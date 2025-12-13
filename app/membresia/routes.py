from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from .models import Membro
from .forms import MembroForm, CadastrarNaoMembroForm, EditarMembroForm
from app.jornada.models import JornadaEvento, registrar_evento_jornada
from app.financeiro.models import Contribuicao
from app.ctm.models import ConclusaoCTM, Presenca
from app.auth.models import User
from app.grupos.models import PequenoGrupo, Setor, Area
from config import Config
from datetime import datetime, timedelta, date
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import joinedload
from werkzeug.datastructures import FileStorage
import os
import uuid
from PIL import Image
from app.decorators import admin_required, group_permission_required, secretaria_or_admin_required
from unidecode import unidecode
import re

membresia_bp = Blueprint('membresia', __name__, url_prefix='/membresia')
ano=Config.ANO_ATUAL
versao=Config.VERSAO_APP

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
PROFILE_PIC_SIZE = (100, 100)
COMPRESSION_QUALITY = 75

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_profile_picture(file_data):
    """
    Salva e otimiza a imagem de perfil.
    - Redimensiona para um tamanho máximo de 100x100 pixels.
    - Converte para RGB para compatibilidade e menor tamanho (remove transparência).
    - Aplica compressão com qualidade 75.
    
    Args:
        file_data (FileStorage): O objeto de arquivo da imagem.
        
    Returns:
        str: O nome único do arquivo salvo, ou None se o arquivo for inválido.
    """
    upload_folder = current_app.config['UPLOAD_FOLDER']
    
    if not isinstance(file_data, FileStorage) or not allowed_file(file_data.filename):
        return None

    try:
        extensao = file_data.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{extensao}"
        filepath = os.path.join(upload_folder, unique_filename)

        img = Image.open(file_data)
        
        img.thumbnail(PROFILE_PIC_SIZE, Image.Resampling.LANCZOS)
        
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        img.save(filepath, quality=COMPRESSION_QUALITY, optimize=True)

        return unique_filename
    except Exception as e:
        current_app.logger.error(f'Erro ao processar e salvar a imagem: {e}')
        return None

@membresia_bp.route('/')
@membresia_bp.route('/index')
@login_required
@secretaria_or_admin_required
def index():
    TIPOS_RECEPCAO_MEMBRO = ['Aclamação', 'Membro', 'Batismo']
    total_pessoas_ativas = Membro.query.filter_by(ativo=True).count()
    total_membros_ativos = Membro.query.filter(
        Membro.ativo == True,
        Membro.status != 'Não-Membro'
    ).count()
    
    total_nao_membros_ativos = Membro.query.filter(
        Membro.ativo == True,
        Membro.status == 'Não-Membro'
    ).count()
    
    membros_por_status = db.session.query(Membro.status, func.count(Membro.id)).filter_by(ativo=True).group_by(Membro.status).all()

    hoje = date.today()
    quinze_dias_depois = hoje + timedelta(days=15)

    if hoje.month == quinze_dias_depois.month:
        aniversariantes_do_mes = Membro.query.filter(
            Membro.ativo == True,
            db.extract('month', Membro.data_nascimento) == hoje.month,
            db.extract('day', Membro.data_nascimento) >= hoje.day,
            db.extract('day', Membro.data_nascimento) <= quinze_dias_depois.day
        ).order_by(db.extract('day', Membro.data_nascimento)).all()
    else:
        aniversariantes_do_mes = Membro.query.filter(
            Membro.ativo == True,
            or_(
                and_(db.extract('month', Membro.data_nascimento) == hoje.month, db.extract('day', Membro.data_nascimento) >= hoje.day),
                and_(db.extract('month', Membro.data_nascimento) == quinze_dias_depois.month, db.extract('day', Membro.data_nascimento) <= quinze_dias_depois.day)
            )
        ).order_by(db.extract('month', Membro.data_nascimento), db.extract('day', Membro.data_nascimento)).all()

    membros_por_campus_data = db.session.query(Membro.campus, func.count(Membro.id)).filter_by(ativo=True).group_by(Membro.campus).all()
    chart_labels_campus = [campus for campus, _ in membros_por_campus_data]
    chart_data_campus = [count for _, count in membros_por_campus_data]

    membros_com_cargos = Membro.query.filter_by(ativo=True).options(
    joinedload(Membro.pgs_facilitados),
    joinedload(Membro.pgs_anfitriados),
    joinedload(Membro.areas_supervisionadas),
    joinedload(Membro.setores_supervisionados)
    ).all()

    contagem_cargos = {
        'Supervisor de Área': 0,
        'Supervisor de Setor': 0,
        'Facilitador de PG': 0,
        'Anfitrião de PG': 0,
        'Facilitador em Treinamento': 0,
        'Anfitrião em Treinamento': 0,
        'Sem Cargo': 0
    }

    for membro in membros_com_cargos:
        if len(membro.areas_supervisionadas) > 0:
            contagem_cargos['Supervisor de Área'] += 1
        elif len(membro.setores_supervisionados) > 0:
            contagem_cargos['Supervisor de Setor'] += 1
        elif len(membro.pgs_facilitados) > 0:
            contagem_cargos['Facilitador de PG'] += 1
        elif len(membro.pgs_anfitriados) > 0:
            contagem_cargos['Anfitrião de PG'] += 1
        else:
            status_treinamento = membro.status_treinamento_pg or 'Participante'
            
            if status_treinamento == 'Facilitador em Treinamento':
                contagem_cargos['Facilitador em Treinamento'] += 1
            
            elif status_treinamento == 'Anfitrião em Treinamento':
                contagem_cargos['Anfitrião em Treinamento'] += 1
                
            else:
                contagem_cargos['Sem Cargo'] += 1
    
    chart_labels_cargos_pg = list(contagem_cargos.keys())
    chart_data_cargos_pg = list(contagem_cargos.values())

    campus_colors = Config.CORES_CAMPUS
    status_colors = Config.CORES_STATUS

    return render_template(
        'membresia/index.html',
        ano=ano,
        versao=versao,
        total_membros_ativos=total_membros_ativos,
        resumo_membros_por_status=contagem_cargos, 
        aniversariantes_do_mes=aniversariantes_do_mes,
        chart_labels_campus=chart_labels_campus,
        chart_data_campus=chart_data_campus,
        chart_labels_cargos=chart_labels_cargos_pg,
        chart_data_cargos=chart_data_cargos_pg,
        campus_colors=campus_colors,
        status_colors=status_colors,
        total_pessoas_ativas=total_pessoas_ativas, 
        total_nao_membros_ativos=total_nao_membros_ativos
    )

@membresia_bp.route('/perfil/editar', methods=['GET', 'POST'])
@login_required
def editar_proprio_perfil():
    membro = current_user.membro
    if not membro:
        flash('Você não tem um perfil de membro para editar.', 'danger')
        return redirect(url_for('main.index'))
    
    form = EditarMembroForm(obj=membro)
    
    if form.validate_on_submit():
        old_foto_perfil = membro.foto_perfil

        membro.nome_completo = form.nome_completo.data
        membro.data_nascimento = form.data_nascimento.data
        membro.campus = form.campus.data

        if isinstance(form.foto_perfil.data, FileStorage) and form.foto_perfil.data.filename:
            if old_foto_perfil and old_foto_perfil != 'default.jpg':
                old_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], old_foto_perfil)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            
            filename = save_profile_picture(form.foto_perfil.data)
            if filename:
                membro.foto_perfil = filename
            else:
                flash('Tipo de arquivo de imagem não permitido ou inválido!', 'danger')
                return render_template('membresia/editar_proprio_perfil.html', form=form, membro=membro, ano=ano, versao=versao)
        
        try:
            db.session.commit()
            flash('Seu perfil foi atualizado com sucesso!', 'success')
            registrar_evento_jornada(
                tipo_acao='MEMBRO_ATUALIZADO_SELF',
                descricao_detalhada='O próprio membro atualizou seu perfil.',
                usuario_executor=current_user,
                membros=[membro]
            )
            return redirect(url_for('membresia.perfil', id=membro.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar o perfil: {e}', 'danger')
    
    return render_template('membresia/editar_proprio_perfil.html', form=form, membro=membro, ano=ano, versao=versao)

@membresia_bp.route('/novo', methods=['GET', 'POST'])
@login_required
@secretaria_or_admin_required
def novo_membro():
    form = MembroForm(membro=None)
    next_url = request.args.get('next')
    
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
            return redirect(next_url or url_for('membresia.index'))
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
@secretaria_or_admin_required
def listagem():
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 30

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
        query = query.filter_by(tipo_recepcao=recepcao_filtro) 

    pagination = query.order_by(Membro.nome_completo).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    membros = pagination.items

    return render_template(
        'membresia/lista.html', 
        membros=membros,
        pagination=pagination,
        ano=ano, 
        versao=versao,
        busca=busca,
        campus=campus_filtro,
        status=status_filtro,
        recepcao_filtro=recepcao_filtro
    )

@membresia_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@secretaria_or_admin_required
def editar_membro(id):
    membro = Membro.query.get_or_404(id)

    if membro.status != 'Não-Membro':
        form = MembroForm(obj=membro, membro=membro)
    else:
        form = CadastrarNaoMembroForm(obj=membro, membro=membro)

    old_status = membro.status
    old_campus = membro.campus
    old_data_recepcao = membro.data_recepcao
    old_tipo_recepcao = membro.tipo_recepcao
    old_obs_recepcao = membro.obs_recepcao
    old_foto_perfil = membro.foto_perfil

    if form.validate_on_submit():
        if membro.status != 'Não-Membro':
            if not form.data_recepcao.data or not form.tipo_recepcao.data:
                flash('Data e tipo de recepção são obrigatórios para Membros.', 'danger')
                return render_template('membresia/cadastro.html', form=form, editar=True, membro=membro, ano=ano, versao=versao)
            
            form.populate_obj(membro)
            membro.status = form.status.data if hasattr(form, 'status') else membro.status
            membro.ativo = True
        else:
            form.populate_obj(membro)
            membro.data_recepcao = None
            membro.tipo_recepcao = None
            membro.obs_recepcao = None
            membro.status = 'Não-Membro'
            membro.ativo = True

        if isinstance(form.foto_perfil.data, FileStorage) and form.foto_perfil.data.filename:
            if old_foto_perfil and old_foto_perfil != 'default.jpg':
                old_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], old_foto_perfil)
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

@membresia_bp.route('/buscar_membros_ctm')
@login_required
def buscar_membros_ctm():
    search_term = request.args.get('term', '')
    turma_id = request.args.get('turma_id', '')
    busca_normalizada = unidecode(search_term).lower()
    busca_db = f'%{busca_normalizada}%'
    
    query = Membro.query.filter(
        func.lower(func.unidecode(Membro.nome_completo)).like(busca_db),
        Membro.ativo == True
    )

    if turma_id:
        query = query.filter(~Membro.turmas_ctm.any(id=turma_id))

    membros = query.order_by(Membro.nome_completo).limit(20).all()
    
    results = []
    for membro in membros:
        results.append({
            'id': membro.id,
            'text': membro.nome_completo
        })
    
    return jsonify(items=results)

@membresia_bp.route('/<int:id>/desligar', methods=['POST'])
@login_required
@secretaria_or_admin_required
def desligar_membro(id):
    membro = Membro.query.get_or_404(id)

    if len(membro.pgs_facilitados) > 0 or len(membro.pgs_anfitriados) > 0:
        flash(f'Não é possível desligar {membro.nome_completo} pois ele(a) é líder de um PG.', 'danger')
        return redirect(url_for('membresia.perfil', id=membro.id))

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
            descricao_detalhada=f'Membro(a) {membro.nome_completo} foi desligado(a).',
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
    form = CadastrarNaoMembroForm(membro=None)
    next_url = request.args.get('next') or request.form.get('next')

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

    return render_template('membresia/cadastro.html',
                           form=form,
                           editar=False,
                           ano=ano,
                           versao=versao,
                           next_url=next_url)

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
    
    historico_ctm = ConclusaoCTM.query.filter_by(membro_id=membro.id).all()

    return render_template('membresia/perfil.html',
                           membro=membro, 
                           jornada_eventos=jornada_eventos,
                           historico_ctm=historico_ctm,
                           jornada_config=current_app.config.get('JORNADA', {}), 
                           ano=ano, 
                           versao=versao)

@membresia_bp.route('/membros/<int:membro_id>')
@login_required
def detalhes_membro(membro_id):
    membro = Membro.query.get_or_404(membro_id)
    jornada_eventos = membro.jornada_eventos_membro.order_by(JornadaEvento.data_evento.desc()).all()
    return render_template('membresia/perfil.html', membro=membro, jornada_eventos=jornada_eventos)

@membresia_bp.route('/unificar', methods=['GET'])
@login_required
@secretaria_or_admin_required
def unificar_membros():
    busca = request.args.get('busca', '').strip()
    membros_sugeridos = []

    if busca:
        busca_normalizada = busca.lower()
        busca_db = f"%{busca_normalizada}%"

        membros_sugeridos = Membro.query.filter(
            func.lower(func.unidecode(Membro.nome_completo)).like(busca_db)
        ).order_by(Membro.nome_completo).limit(20).all()

    return render_template('membresia/unificar_membros.html', 
                           busca=busca, 
                           membros_sugeridos=membros_sugeridos,
                           ano=Config.ANO_ATUAL, 
                           versao=Config.VERSAO_APP)

@membresia_bp.route('/unificar/revisar', methods=['POST'])
@login_required
@secretaria_or_admin_required
def unificar_revisar():
    data = request.get_json()
    membros_ids = data.get('membros_ids', [])

    if not isinstance(membros_ids, list) or len(membros_ids) < 2:
        return jsonify({'success': False, 'message': 'Selecione pelo menos dois membros para unificar.'}), 400

    membros_a_unificar = Membro.query.options(joinedload(Membro.user)).filter(Membro.id.in_(membros_ids)).all()
    
    if len(membros_a_unificar) != len(membros_ids):
        return jsonify({'success': False, 'message': 'Um ou mais membros não foram encontrados.'}), 404

    dados_membros = []
    for membro in membros_a_unificar:
        dados_membros.append({
            'id': membro.id,
            'nome_completo': membro.nome_completo,
            'data_nascimento': membro.data_nascimento.strftime('%Y-%m-%d') if membro.data_nascimento else None,
            'status': membro.status,
            'campus': membro.campus,
            'email': membro.user.email if membro.user else None,
            'permissoes': membro.user.permissions if membro.user else None
        })

    return render_template('membresia/unificar_revisar.html', dados_membros=dados_membros, ano=Config.ANO_ATUAL, versao=Config.VERSAO_APP)

@membresia_bp.route('/unificar/processar', methods=['POST'])
@login_required
@secretaria_or_admin_required
def unificar_processar():
    try:
        dados_revisao = request.form

        membro_principal_id = dados_revisao.get('membro_principal_id')
        if not membro_principal_id:
            return jsonify({'success': False, 'message': 'Membro principal não selecionado.'}), 400
        
        membro_principal = Membro.query.get(membro_principal_id)
        if not membro_principal:
            return jsonify({'success': False, 'message': 'Membro principal não encontrado.'}), 404

        membros_ids_a_excluir = [int(id) for id in dados_revisao.getlist('membros_a_excluir[]') if int(id) != int(membro_principal_id)]
        membros_secundarios = Membro.query.filter(Membro.id.in_(membros_ids_a_excluir)).all()

        membro_principal.nome_completo = dados_revisao.get('nome_completo')
        
        data_nasc_str = dados_revisao.get('data_nascimento')
        if data_nasc_str and data_nasc_str != 'None':
            membro_principal.data_nascimento = datetime.strptime(data_nasc_str, '%Y-%m-%d').date()
        else:
            membro_principal.data_nascimento = None

        membro_principal.status = dados_revisao.get('status')
        membro_principal.campus = dados_revisao.get('campus')
        
        usuario_principal = User.query.filter_by(membro_id=membro_principal.id).first()
        if not usuario_principal:
            for membro_secundario in membros_secundarios:
                usuario_secundario = User.query.filter_by(membro_id=membro_secundario.id).first()
                if usuario_secundario:
                    usuario_secundario.membro_id = membro_principal.id
                    usuario_principal = usuario_secundario
                    break
        
        if usuario_principal:
            usuario_principal.email = dados_revisao.get('email')
            usuario_principal.permissions = dados_revisao.get('permissoes')

        db.session.add(membro_principal)

        for membro_secundario in membros_secundarios:
            
            pgs_facilitados_secundario = PequenoGrupo.query.filter_by(facilitador_id=membro_secundario.id).all()
            PequenoGrupo.query.filter_by(facilitador_id=membro_secundario.id).update(
                {PequenoGrupo.facilitador_id: membro_principal.id}, synchronize_session=False
            )
            for pg in pgs_facilitados_secundario:
                 flash(f'O PG {pg.nome} teve o facilitador reatribuído para {membro_principal.nome_completo}.', 'warning')
                
            pgs_anfitriados_secundario = PequenoGrupo.query.filter_by(anfitriao_id=membro_secundario.id).all()
            PequenoGrupo.query.filter_by(anfitriao_id=membro_secundario.id).update(
                {PequenoGrupo.anfitriao_id: membro_principal.id}, synchronize_session=False
            )
            for pg in pgs_anfitriados_secundario:
                 flash(f'O PG {pg.nome} teve o anfitrião reatribuído para {membro_principal.nome_completo}.', 'warning')

            for setor in list(membro_secundario.setores_supervisionados):
                setor.supervisores.remove(membro_secundario)
                setor.supervisores.append(membro_principal)
                db.session.add(setor)
            
            for area in list(membro_secundario.areas_supervisionadas):
                area.supervisores.remove(membro_secundario)
                area.supervisores.append(membro_principal)
                db.session.add(area)
            
            db.session.flush() 

            conclusoes_secundarias = ConclusaoCTM.query.filter_by(membro_id=membro_secundario.id).all()
            turmas_concluidas_principal = {c.turma_id for c in ConclusaoCTM.query.filter_by(membro_id=membro_principal.id).all()}
            for conclusao in conclusoes_secundarias:
                if conclusao.turma_id in turmas_concluidas_principal:
                    db.session.delete(conclusao)
                else:
                    conclusao.membro_id = membro_principal.id
            
            presencas_secundarias = Presenca.query.filter_by(membro_id=membro_secundario.id).all()
            aulas_com_presenca_principal = {p.aula_realizada_id for p in Presenca.query.filter_by(membro_id=membro_principal.id).all()}
            for presenca in presencas_secundarias:
                if presenca.aula_realizada_id in aulas_com_presenca_principal:
                    db.session.delete(presenca)
                else:
                    presenca.membro_id = membro_principal.id

            Contribuicao.query.filter_by(membro_id=membro_secundario.id).update({Contribuicao.membro_id: membro_principal.id}, synchronize_session=False)

            for evento in membro_secundario.jornada_eventos_membro:
                evento.membros_afetados.append(membro_principal)
                evento.membros_afetados.remove(membro_secundario)

            usuario_secundario = User.query.filter_by(membro_id=membro_secundario.id).first()
            if usuario_secundario and usuario_secundario.id != usuario_principal.id:
                db.session.delete(usuario_secundario)

            db.session.delete(membro_secundario)

        db.session.commit()
        flash('Unificação de membros concluída com sucesso!', 'success')
        return redirect(url_for('membresia.perfil', id=membro_principal.id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Erro ao unificar membros: {e}')
        flash(f'Ocorreu um erro ao processar a unificação: {e}', 'danger')
        return redirect(url_for('membresia.unificar_membros'))

@membresia_bp.route('/sugerir_membros', methods=['GET'])
@login_required
def sugerir_membros():
    busca = request.args.get('q', '').strip()
    membros_encontrados = []

    if busca:
        busca_normalizada = unidecode(busca).lower()
        busca_db = f"%{busca_normalizada}%"
        
        membros_encontrados = Membro.query.filter(
            func.lower(func.unidecode(Membro.nome_completo)).like(busca_db),
            Membro.ativo == True
        ).order_by(Membro.nome_completo).limit(5).all()

    resultados_json = []
    for membro in membros_encontrados:
        resultados_json.append({
            'nome_completo': membro.nome_completo,
            'status': membro.status,
            'campus': membro.campus,
            'perfil_url': url_for('membresia.perfil', id=membro.id)
        })
        
    return jsonify({'sugestoes': resultados_json})
