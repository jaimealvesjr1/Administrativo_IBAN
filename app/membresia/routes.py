from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required
from app.extensions import db
from .models import Membro, JornadaEvento
from .forms import MembroForm, CadastrarNaoMembroForm
from config import Config
from datetime import datetime
from sqlalchemy import func
import os
import uuid
from PIL import Image

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
def novo_membro():
    form = MembroForm()
    
    if form.validate_on_submit():
        membro = Membro(
            nome_completo=form.nome_completo.data,
            data_nascimento=form.data_nascimento.data,
            data_recepcao=form.data_recepcao.data,
            status=form.status.data,
            campus=form.campus.data,
            ativo=True
        )

        if form.foto_perfil.data:
            filename = save_profile_picture(form.foto_perfil.data)
            if filename:
                membro.foto_perfil = filename
            else:
                flash('Tipo de arquivo de imagem não permitido ou inválido!', 'danger')
                return render_template('membresia/cadastro.html', form=form, ano=ano, versao=versao)

        db.session.add(membro)
        db.session.commit()

        descricao_cadastro = f'Chegou à IBAN no Campus {membro.campus}.'
        membro.registrar_evento_jornada(descricao_cadastro, 'Cadastro')

        flash(f'{membro.nome_completo} registrado com sucesso!', 'success')
        return redirect(url_for('membresia.index'))
    return render_template('membresia/cadastro.html',
                           form=form, ano=ano, versao=versao)

@membresia_bp.route('/listagem')
@login_required
def listagem():
    busca = request.args.get('busca', '')
    campus_filtro = request.args.get('campus', '')
    status_filtro = request.args.get('status', '')

    query = Membro.query.filter_by(ativo=True)
    if busca:
        query = query.filter(Membro.nome_completo.ilike(f'%{busca}%'))
    if campus_filtro:
        query = query.filter_by(campus=campus_filtro)
    if status_filtro:
        query = query.filter_by(status=status_filtro)

    membros = query.order_by(Membro.nome_completo).all()

    return render_template('membresia/lista.html', membros=membros, ano=ano, versao=versao)

@membresia_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_membro(id):
    membro = Membro.query.get_or_404(id)
    old_status = membro.status
    old_campus = membro.campus
    old_data_recepcao = membro.data_recepcao

    form = MembroForm()

    if request.method == 'GET':
        form.nome_completo.data = membro.nome_completo
        form.data_nascimento.data = membro.data_nascimento
        form.data_recepcao.data = membro.data_recepcao
        form.status.data = membro.status
        form.campus.data = membro.campus

    if form.validate_on_submit():
        membro.nome_completo = form.nome_completo.data
        membro.data_nascimento = form.data_nascimento.data
        membro.data_recepcao = form.data_recepcao.data
        membro.status = form.status.data
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

        new_status = form.status.data
        new_campus = form.campus.data
        new_data_recepcao = form.data_recepcao.data

        if old_status != new_status:
            descricao_status = f'Status alterado de {old_status} para {new_status}'
            membro.registrar_evento_jornada(descricao_status, 'Status_Mudanca')
        
        if old_campus != new_campus:
            descricao_campus = f'Passou a frequentar o Campus {new_campus}.'
            membro.registrar_evento_jornada(descricao_campus, 'Campus_Mudanca')
        
        if old_data_recepcao != new_data_recepcao:
            descricao_data_recepcao = f"Data de Recepção alterada de {old_data_recepcao.strftime('%d/%m/%Y') if old_data_recepcao else 'Indefinida'} para {new_data_recepcao.strftime('%d/%m/%Y') if new_data_recepcao else 'Indefinida'}."
            membro.registrar_evento_jornada(descricao_data_recepcao, 'Data_Recepcao_Mudanca')
        
        db.session.commit()
        flash(f'Registro de {membro.nome_completo} atualizado com sucesso!', 'success')
        return redirect(url_for('membresia.index'))
        
    return render_template('membresia/cadastro.html',
                           form=form, editar=True, membro=membro, ano=ano, versao=versao)

@membresia_bp.route('/<int:id>/desligar', methods=['POST'])
@login_required
def desligar_membro(id):
    membro = Membro.query.get_or_404(id)
    current_status = membro.status
    membro.ativo = False
    membro.status = 'Desligado'
    db.session.commit()

    descricao_desligamento = f'Foi desligado(a) da IBAN enquanto era {current_status}.'
    membro.registrar_evento_jornada(descricao_desligamento, 'Desligamento')

    flash(f"{membro.nome_completo} foi desligado.", 'warning')
    return redirect(url_for('membresia.index'))

@membresia_bp.route('/cadastro_nao_membro_ctm', methods=['GET', 'POST'])
def cadastro_nao_membro_ctm():
    form = CadastrarNaoMembroForm()

    if form.validate_on_submit():
        membro_existente = Membro.query.filter_by(nome_completo=form.nome_completo.data).first()
        if membro_existente:
            flash(f'Já existe uma pessoa com o nome "{form.nome_completo.data}". Por favor, verifique ou selecione o nome na tela anterior.', 'warning')
            return render_template('membresia/cadastro_nao_membro.html', form=form, ano=ano, versao=versao)

        novo_membro = Membro(
            nome_completo=form.nome_completo.data,
            data_nascimento=form.data_nascimento.data,
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
        db.session.commit()

        descricao_cadastro_nao_membro = f'Chegou à IBAN através do CTM no Campus {novo_membro.campus}'
        novo_membro.registrar_evento_jornada(descricao_cadastro_nao_membro, 'Cadastro_Nao_Membro_CTM')

        flash(f'{novo_membro.nome_completo} cadastrado(a) com sucesso!', 'success')
        return redirect(url_for('ctm.registrar_presenca_aluno'))

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
    jornada = JornadaEvento.query.filter_by(membro_id=membro.id).order_by(JornadaEvento.data_evento.desc()).all()

    return render_template('membresia/perfil.html',
                           membro=membro, jornada=jornada, jornada_config=current_app.config.get('JORNADA', {}), ano=ano, versao=versao)
