from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from app.extensions import db
from .models import Membro
from .forms import MembroForm, CadastrarNaoMembroForm
from app.jornada.models import JornadaEvento, registrar_evento_jornada
from config import Config
from datetime import datetime
from sqlalchemy import func
import os
import uuid
from PIL import Image
from app.decorators import admin_required, group_permission_required

membresia_bp = Blueprint('membresia', __name__, url_prefix='/membresia')
ano=Config.ANO_ATUAL
versao=Config.VERSAO_APP

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
PROFILE_PIC_SIZE = (150, 150)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_profile_picture(file_data):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if file_data and allowed_file(file_data.filename):
        unique_filename = str(uuid.uuid4()) + os.path.splitext(file_data.filename)[1]
        filepath = os.path.join(upload_folder, unique_filename)

        img = Image.open(file_data)
        img.thumbnail(PROFILE_PIC_SIZE, Image.Resampling.LANCZOS)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        img.save(filepath)

        return unique_filename
    return None

@membresia_bp.route('/')
@membresia_bp.route('/index')
@login_required
@admin_required
def index():
    total_membros_ativos = Membro.query.filter_by(ativo=True).count()
    membros_por_status = db.session.query(Membro.status, func.count(Membro.id)).filter_by(ativo=True).group_by(Membro.status).all()
    resumo_membros_por_status = {status: count for status, count in membros_por_status}

    mes_atual = datetime.now().month
    aniversariantes_do_mes = Membro.query.filter(
        Membro.ativo == True,
        func.strftime('%m', Membro.data_nascimento) == str(mes_atual).zfill(2)
    ).order_by(func.strftime('%d', Membro.data_nascimento)).all()

    membros_por_campus_data = db.session.query(Membro.campus, func.count(Membro.id)).filter_by(ativo=True).group_by(Membro.campus).all()
    chart_labels_campus = [campus for campus, _ in membros_por_campus_data]
    chart_data_campus = [count for _, count in membros_por_campus_data]

    membros_por_status_chart_data = db.session.query(Membro.status, func.count(Membro.id)).filter_by(ativo=True).group_by(Membro.status).all()
    chart_labels_status = [status for status, _ in membros_por_status_chart_data]
    chart_data_status = [count for _, count in membros_por_status_chart_data]

    campus_colors = Config.CAMPUS
    status_colors = Config.STATUS

    return render_template(
        'membresia/index.html',
        ano=ano,
        versao=versao,
        total_membros_ativos=total_membros_ativos,
        resumo_membros_por_status=resumo_membros_por_status,
        aniversariantes_do_mes=aniversariantes_do_mes,
        chart_labels_campus=chart_labels_campus,
        chart_data_campus=chart_data_campus,
        chart_labels_status=chart_labels_status,
        chart_data_status=chart_data_status,
        campus_colors=campus_colors,
        status_colors=status_colors
    )

@membresia_bp.route('/novo', methods=['GET', 'POST'])
@login_required
@admin_required
def novo_membro():
    form = MembroForm()
    
    if form.validate_on_submit():
        membro = Membro(
            nome_completo=form.nome_completo.data,
            data_nascimento=form.data_nascimento.data,
            data_recepcao=form.data_recepcao.data,
            tipo_recepcao=form.tipo_recepcao.data,
            status='Membro',
            campus=form.campus.data,
            obs_recepcao=form.obs_recepcao.data,
            ativo=True
        )

        if form.foto_perfil.data and form.foto_perfil.data.filename:
            filename = save_profile_picture(form.foto_perfil.data)
            if filename:
                membro.foto_perfil = filename
            else:
                flash('Tipo de arquivo de imagem não permitido ou inválido!', 'danger')
                return render_template('membresia/cadastro.html', form=form, ano=ano, versao=versao)

        db.session.add(membro)
        try:
            db.session.commit()
            flash(f'{membro.nome_completo} registrado com sucesso!', 'success')
            registrar_evento_jornada(
                tipo_acao='CADASTRO_MEMBRO',
                descricao_detalhada='Membro(a) cadastrado(a).',
                usuario_executor=current_user,
                membros=[membro]
            )
            return redirect(url_for('membresia.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar membro: {e}', 'danger')
    
    elif request.method == 'POST':
        print('O formulário falhou na validação.')
        print(f'Erros do formulário: {form.errors}')
        flash('Por favor, verifique os campos em vermelho e corrija os erros de validação.', 'danger')

    return render_template('membresia/cadastro.html', form=form, ano=ano, versao=versao)

@membresia_bp.route('/listagem')
@login_required
@admin_required
def listagem():
    busca = request.args.get('busca', '')
    campus_filtro = request.args.get('campus', '')
    status_filtro = request.args.get('status', '')
    recepcao_filtro = request.args.get('recepcao', '')

    query = Membro.query.filter_by(ativo=True)
    if busca:
        query = query.filter(Membro.nome_completo.ilike(f'%{busca}%'))
    if campus_filtro:
        query = query.filter_by(campus=campus_filtro)
    if status_filtro:
        query = query.filter_by(status=status_filtro)
    if recepcao_filtro:
        query = query.filter_by(recepcao=recepcao_filtro)

    membros = query.order_by(Membro.nome_completo).all()

    return render_template('membresia/lista.html', membros=membros, ano=ano, versao=versao)

@membresia_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_membro(id):
    membro = Membro.query.get_or_404(id)

    if membro.status == 'Membro':
        form = MembroForm(obj=membro)
    else:
        form = CadastrarNaoMembroForm(obj=membro)

    old_status = membro.status
    old_campus = membro.campus
    old_data_recepcao = membro.data_recepcao
    old_tipo_recepcao = membro.tipo_recepcao
    old_obs_recepcao = membro.obs_recepcao
    
    if form.validate_on_submit():
        membro.nome_completo = form.nome_completo.data
        membro.data_nascimento = form.data_nascimento.data

        if membro.status == 'Membro':
            membro.data_recepcao = form.data_recepcao.data
            membro.tipo_recepcao = form.tipo_recepcao.data
            membro.obs_recepcao = form.obs_recepcao.data
        else:
            membro.data_recepcao = None
            membro.tipo_recepcao = None
            membro.obs_recepcao = None

        membro.status = form.status.data if hasattr(form, 'status') else membro.status
        membro.campus = form.campus.data

        if form.foto_perfil.data and form.foto_perfil.data.filename:
            if membro.foto_perfil and membro.foto_perfil != 'default.jpg':
                old_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], membro.foto_perfil)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)

            filename = save_profile_picture(form.foto_perfil.data)
            if filename:
                membro.foto_perfil = filename
            else:
                flash('Tipo de arquivo de imagem não permitido ou inválido!', 'danger')
                return render_template('membresia/cadastro.html', form=form, editar=True, membro=membro, ano=ano, versao=versao)

        try:
            db.session.commit()
            flash(f'Registro de {membro.nome_completo} atualizado com sucesso!', 'success')

            descricao_jornada = 'Dados atualizados.'
            mudancas = []
            if old_status != membro.status:
                mudancas.append(f'Status: {old_status} -> {membro.status}')
            if old_campus != membro.campus:
                mudancas.append(f'Campus: {old_campus} -> {membro.campus}')
            if old_data_recepcao != membro.data_recepcao:
                mudancas.append(f"Recepção: {old_data_recepcao.strftime('%d/%m/%Y') if old_data_recepcao else 'Indefinida'} -> {membro.data_recepcao.strftime('%d/%m/%Y') if membro.data_recepcao else 'Indefinida'}")
            if old_tipo_recepcao != membro.tipo_recepcao:
                mudancas.append(f'Tipo Recepção: {old_tipo_recepcao} -> {membro.tipo_recepcao}')
            if old_obs_recepcao != membro.obs_recepcao:
                mudancas.append('Observações de Recepção alteradas')

            if mudancas:
                descricao_jornada += ' ' + '; '.join(mudancas)
            else:
                descricao_jornada = 'Dados atualizados. Nenhuma mudança nos campos principais detectada.'
            
            registrar_evento_jornada(
                tipo_acao='MEMBRO_ATUALIZADO',
                descricao_detalhada=descricao_jornada,
                usuario_executor=current_user,
                membros=[membro]
            )
            return redirect(url_for('membresia.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar membro: {e}', 'danger')
            
    return render_template('membresia/cadastro.html',
                            form=form, editar=True, membro=membro, ano=ano, versao=versao)

@membresia_bp.route('/<int:id>/desligar', methods=['POST'])
@login_required
@admin_required
def desligar_membro(id):
    membro = Membro.query.get_or_404(id)

    membro.ativo = False
    membro.status = 'Desligado'
    
    if membro.pg_id:
        membro.pg_id = None
        membro.status_treinamento_pg = 'Participante'
        membro.participou_ctm = False
        membro.participou_encontro_deus = False
        membro.batizado_aclamado = False
        db.session.add(membro)

    try:
        db.session.commit()
        flash(f"{membro.nome_completo} foi desligado.", 'warning')

        registrar_evento_jornada(
            tipo_acao='DESLIGAMENTO',
            descricao_detalhada='Membro(a) foi desligado(a).',
            usuario_executor=current_user,
            membros=[membro]
        )

        return redirect(url_for('membresia.index'))
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao desligar membro: {e}', 'danger')
    return redirect(url_for('membresia.index'))


@membresia_bp.route('/cadastro_nao_membro', methods=['GET', 'POST'])
def cadastro_nao_membro():
    form = CadastrarNaoMembroForm()
    next_url = request.args.get('next')

    if form.validate_on_submit():
        novo_membro = Membro(
            nome_completo=form.nome_completo.data,
            campus=form.campus.data,
            status='Não-Membro',
            ativo=True
        )

        if form.foto_perfil.data and form.foto_perfil.data.filename:
            filename = save_profile_picture(form.foto_perfil.data)
            if filename:
                novo_membro.foto_perfil = filename
            else:
                flash('Tipo de arquivo de imagem não permitido ou inválido!', 'danger')
                return render_template('membresia/cadastro_nao_membro.html', form=form, ano=ano, versao=versao)

        db.session.add(novo_membro)
        try:
            db.session.commit()
            flash(f'{novo_membro.nome_completo} cadastrado(a) com sucesso!', 'success')

            registrar_evento_jornada(
                tipo_acao='CADASTRO_NAO_MEMBRO',
                descricao_detalhada='Cadastrado(a) como Não-Membro.',
                usuario_executor=current_user,
                membros=[novo_membro]
            )
            return redirect(next_url or url_for('ctm.registrar_presenca_aluno'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar Não-Membro: {e}', 'danger')

    elif request.method == 'POST':
        current_app.logger.error(f'Erros de validação do formulário de não-membro: {form.errors}')
        flash('Por favor, verifique os campos em vermelho e corrija os erros.', 'danger')

    return render_template('membresia/cadastro_nao_membro.html',
                            form=form, ano=ano, versao=versao)

@membresia_bp.route('/nao_membros')
@login_required
def listar_nao_membros():
    nao_membros = Membro.query.filter_by(status='Não-Membro', ativo=True).order_by(Membro.nome_completo).all()
    return render_template('membresia/lista_nao_membros.html', nao_membros=nao_membros, ano=ano, versao=versao)

@membresia_bp.route('/<int:id>/perfil')
@login_required
def perfil(id):
    membro = Membro.query.get_or_404(id)
    jornada_eventos = membro.jornada_eventos_membro.order_by(JornadaEvento.data_evento.desc()).all()

    return render_template('membresia/perfil.html',
                            membro=membro, jornada_eventos=jornada_eventos, jornada_config=current_app.config.get('JORNADA', {}), ano=ano, versao=versao)

@membresia_bp.route('/membros/<int:membro_id>')
@login_required
def detalhes_membro(membro_id):
    membro = Membro.query.get_or_404(membro_id)
    jornada_eventos = membro.jornada_eventos_membro.order_by(JornadaEvento.data_evento.desc()).all()
    return render_template('membresia/perfil.html', membro=membro, jornada_eventos=jornada_eventos)
