from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.grupos.models import Area, Setor, PequenoGrupo, AreaMetaVigente
from app.grupos.forms import AreaForm, SetorForm, PequenoGrupoForm, AreaMetasForm, MultiplicacaoForm
from app.membresia.models import Membro
from app.auth.models import User
from app.jornada.models import registrar_evento_jornada, JornadaEvento
from config import Config
from app.decorators import admin_required, group_permission_required, leader_required
from sqlalchemy import or_, and_, func
from app.ctm.models import TurmaCTM, AulaRealizada, Presenca, ConclusaoCTM
from datetime import date, datetime

grupos_bp = Blueprint('grupos', __name__, template_folder='templates')
ano=Config.ANO_ATUAL
versao=Config.VERSAO_APP

def is_supervisor_do_setor(user_membro_id, pg):
    """Verifica se o usuário é supervisor do setor do PG."""
    if not pg.setor:
        return False
    membro = Membro.query.get(user_membro_id)
    if not membro:
        return False
    return pg.setor in membro.setores_supervisionados

def is_supervisor_da_area(user_membro_id, pg):
    """Verifica se o usuário é supervisor da área do PG."""
    if not pg.setor or not pg.setor.area:
        return False
    membro = Membro.query.get(user_membro_id)
    if not membro:
        return False
    return pg.setor.area in membro.areas_supervisionadas

def is_pg_facilitator(user_membro_id, pg):
    """Verifica se o usuário é facilitador do PG."""
    return pg.facilitador_id == user_membro_id

@grupos_bp.route('/')
@grupos_bp.route('/index')
@grupos_bp.route('/listar')
@login_required
@leader_required
def listar_grupos_unificada():
    busca = request.args.get('busca', '')
    setor_filtro = request.args.get('setor_filtro', '')
    area_filtro = request.args.get('area_filtro', '')
    tipo_selecionado = request.args.get('tipo', 'pgs')
    status_pg = request.args.get('status_pg', 'ativos')

    if current_user.has_permission('admin'):
        areas_query = Area.query
        setores_query = Setor.query
        pgs_query = PequenoGrupo.query

    elif current_user.membro:
        membro_logado = current_user.membro

        areas_do_lider = Area.query.filter(Area.supervisores.any(id=membro_logado.id)).all()
        area_ids_lider = [a.id for a in areas_do_lider]
        
        setores_do_lider = Setor.query.filter(
            db.or_(
                Setor.supervisores.any(id=membro_logado.id),
                Setor.area_id.in_(area_ids_lider)
            )
        ).all()
        setor_ids_lider = [s.id for s in setores_do_lider]

        areas_query = Area.query.filter(Area.id.in_(area_ids_lider))
        setores_query = Setor.query.filter(Setor.id.in_(setor_ids_lider))
        pgs_query = PequenoGrupo.query.filter(
            db.or_(
                PequenoGrupo.facilitador_id == membro_logado.id,
                PequenoGrupo.anfitriao_id == membro_logado.id,
                PequenoGrupo.setor_id.in_(setor_ids_lider)
            )
        )
    else:
        flash('Você não tem permissão para visualizar grupos.', 'danger')
        return redirect(url_for('main.index'))

    if tipo_selecionado == 'pgs':
        if status_pg == 'ativos':
            pgs_query = pgs_query.filter_by(ativo=True)
        elif status_pg == 'multiplicados':
            pgs_query = pgs_query.filter(
                db.and_(
                    PequenoGrupo.ativo == False,
                    PequenoGrupo.data_multiplicacao.isnot(None)
                )
            )
        elif status_pg == 'inativos':
            pgs_query = pgs_query.filter(
                db.and_(
                    PequenoGrupo.ativo == False,
                    PequenoGrupo.data_multiplicacao.is_(None)
                )
            )
    
    if busca:
        if tipo_selecionado == 'areas':
            areas_query = areas_query.filter(Area.nome.ilike(f'%{busca}%'))
        elif tipo_selecionado == 'setores':
            setores_query = setores_query.filter(Setor.nome.ilike(f'%{busca}%'))
        elif tipo_selecionado == 'pgs':
            pgs_query = pgs_query.filter(PequenoGrupo.nome.ilike(f'%{busca}%'))

    if area_filtro:
        if tipo_selecionado == 'setores':
            setores_query = setores_query.filter(Setor.area_id == area_filtro)
        elif tipo_selecionado == 'pgs':
            pgs_query = pgs_query.filter(PequenoGrupo.setor.has(Setor.area_id == area_filtro))
    
    if setor_filtro:
        if tipo_selecionado == 'pgs':
            pgs_query = pgs_query.filter(PequenoGrupo.setor_id == setor_filtro)

    areas = areas_query.order_by(Area.nome).all()
    setores = setores_query.order_by(Setor.nome).all()
    pgs = pgs_query.order_by(PequenoGrupo.nome).all()

    todas_areas = Area.query.order_by(Area.nome).all()
    todos_setores = Setor.query.order_by(Setor.nome).all()
    
    return render_template('grupos/listagem_unificada.html',
                           areas=areas,
                           setores=setores,
                           pgs=pgs,
                           tipo_selecionado=tipo_selecionado,
                           status_pg=status_pg,
                           busca=busca,
                           setor_filtro=setor_filtro,
                           area_filtro=area_filtro,
                           todas_areas=todas_areas,
                           todos_setores=todos_setores,
                           ano=ano, versao=versao,
                           config=Config)

@grupos_bp.route('/areas')
@login_required
@admin_required
def listar_areas():
    return redirect(url_for('grupos.listar_grupos_unificada', tipo='areas'))

@grupos_bp.route('/areas/criar', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_area():
    form = AreaForm()

    supervisores_possiveis = Membro.query.filter(Membro.ativo == True).order_by(Membro.nome_completo).all()
    form.supervisores.choices = [(m.id, m.nome_completo) for m in supervisores_possiveis]

    if form.validate_on_submit():
        nova_area = Area(
            nome=form.nome.data,
        )
        for supervisor_id in form.supervisores.data:
            supervisor = Membro.query.get(supervisor_id)
            if supervisor:
                nova_area.supervisores.append(supervisor)

        db.session.add(nova_area)
        try:
            db.session.commit()
            flash('Área criada com sucesso!', 'success')
            for supervisor in nova_area.supervisores:
                registrar_evento_jornada(
                    tipo_acao='LIDERANCA_ALTERADA',
                    descricao_detalhada=f'Se tornou supervisor(a) da área "{nova_area.nome}".',
                    usuario_executor=current_user,
                    membros=[supervisor]
                )
            return redirect(url_for('grupos.detalhes_area', area_id=nova_area.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar Área: {e}', 'danger')
    return render_template('grupos/areas/form.html', form=form, ano=ano, versao=versao)

@grupos_bp.route('/areas/<int:area_id>')
@login_required
@group_permission_required(Area, 'view', 'supervisores')
def detalhes_area(area_id):
    area = Area.query.get_or_404(area_id)
    jornada_eventos = area.jornada_eventos_area.order_by(JornadaEvento.data_evento.desc()).all()

    dizimistas_por_setor_chart = { 'labels': [], 'dizimistas': [], 'nao_dizimistas': [] }
    ctm_por_setor = []
    membros_por_setor = []
    pgs_ativos_por_setor = []

    for setor in area.setores:
        dizimistas_data = setor.distribuicao_dizimistas_30d
        dizimistas_por_setor_chart['labels'].append(setor.nome)
        dizimistas_por_setor_chart['dizimistas'].append(dizimistas_data.get('dizimistas', 0))
        dizimistas_por_setor_chart['nao_dizimistas'].append(dizimistas_data.get('nao_dizimistas', 0))

        ctm_data = setor.distribuicao_frequencia_ctm
        ctm_por_setor.append({
            'setor_nome': setor.nome,
            'count': ctm_data.get('frequentes_ctm', 0)
        })

        membros_por_setor.append({
            'setor_nome': setor.nome,
            'count': len(setor.membros_do_setor_completos)
        })

        pgs_ativos_por_setor.append({
            'id': setor.id,
            'nome': setor.nome,
            'pgs_ativos': setor.pequenos_grupos.filter_by(ativo=True).count()
        })
    
    pgs_ativos_por_setor.sort(key=lambda x: x['nome'])

    return render_template('grupos/areas/detalhes.html',
                           area=area,
                           jornada_eventos=jornada_eventos,
                           dizimistas_por_setor=dizimistas_por_setor_chart,
                           ctm_por_setor=ctm_por_setor,
                           membros_por_setor=membros_por_setor,
                           pgs_ativos_por_setor=pgs_ativos_por_setor,
                           config=Config, ano=ano, versao=versao)

@grupos_bp.route('/areas/editar/<int:area_id>', methods=['GET', 'POST'])
@login_required
@group_permission_required(Area, 'edit', 'supervisores')
def editar_area(area_id):
    area = Area.query.get_or_404(area_id)
    form = AreaForm(obj=area)

    if form.validate_on_submit():
        area.nome = form.nome.data
        
        supervisores_antigos_ids = {s.id for s in area.supervisores}
        supervisores_novos_ids = set(form.supervisores.data)

        area.supervisores = []
        for supervisor_id in supervisores_novos_ids:
            supervisor = Membro.query.get(supervisor_id)
            if supervisor:
                area.supervisores.append(supervisor)
        
        try:
            db.session.commit()

            novos_supervisores_adicionados = supervisores_novos_ids.difference(supervisores_antigos_ids)
            supervisores_removidos = supervisores_antigos_ids.difference(supervisores_novos_ids)

            for supervisor_id in novos_supervisores_adicionados:
                supervisor = Membro.query.get(supervisor_id)
                if supervisor:
                    registrar_evento_jornada(
                        tipo_acao='LIDERANCA_ALTERADA', 
                        descricao_detalhada=f'Se tornou supervisor(a) da área "{area.nome}".', 
                        usuario_executor=current_user, 
                        membros=[supervisor]
                    )
            
            for supervisor_id in supervisores_removidos:
                supervisor = Membro.query.get(supervisor_id)
                if supervisor:
                    registrar_evento_jornada(
                        tipo_acao='LIDERANCA_ALTERADA', 
                        descricao_detalhada=f'Deixou de ser supervisor(a) da área "{area.nome}".', 
                        usuario_executor=current_user, 
                        membros=[supervisor]
                    )

            flash('Área atualizada com sucesso!', 'success')
            return redirect(url_for('grupos.detalhes_area', area_id=area.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar Área: {e}', 'danger')
    elif request.method == 'GET':
        form.supervisores.data = [s.id for s in area.supervisores]
    return render_template('grupos/areas/form.html', form=form, area=area, ano=ano, versao=versao)

@grupos_bp.route('/areas/deletar/<int:area_id>', methods=['POST'])
@login_required
@admin_required
def deletar_area(area_id):
    area = Area.query.get_or_404(area_id)
    if area.setores.count() > 0:
        flash(f'Não é possível deletar a Área "{area.nome}" pois ela possui Setores vinculados.', 'danger')
        return redirect(url_for('grupos.listar_areas'))
    
    nome_area = area.nome
    supervisores_antigos = list(area.supervisores)
    
    try:
        db.session.delete(area)
        db.session.commit()
        flash('Área deletada com sucesso!', 'success')
        for supervisor in supervisores_antigos:
            registrar_evento_jornada(
                tipo_acao='LIDERANCA_ALTERADA', 
                descricao_detalhada=f'Deixou de ser supervisor(a) da área "{nome_area}".', 
                usuario_executor=current_user, 
                membros=[supervisor]
            )
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar Área: {e}', 'danger')
    return redirect(url_for('grupos.listar_areas'))

@grupos_bp.route('/setores')
@login_required
def listar_setores():
    return redirect(url_for('grupos.listar_grupos_unificada', tipo='setores'))

@grupos_bp.route('/setores/criar', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_setor():
    form = SetorForm()

    supervisores_possiveis = Membro.query.filter(Membro.ativo == True).order_by(Membro.nome_completo).all()
    form.supervisores.choices = [(m.id, m.nome_completo) for m in supervisores_possiveis]
    
    if form.validate_on_submit():
        novo_setor = Setor(
            nome=form.nome.data,
            area_id=form.area.data,
        )
        
        for supervisor_id in form.supervisores.data:
            supervisor = Membro.query.get(supervisor_id)
            if supervisor:
                novo_setor.supervisores.append(supervisor)

        db.session.add(novo_setor)
        try:
            db.session.commit()
            flash('Setor criado com sucesso!', 'success')
            for supervisor in novo_setor.supervisores:
                registrar_evento_jornada(
                    tipo_acao='LIDERANCA_ALTERADA', 
                    descricao_detalhada=f'Se tornou supervisor(a) do setor "{novo_setor.nome}".', 
                    usuario_executor=current_user, 
                    membros=[supervisor]
                )
            return redirect(url_for('grupos.detalhes_setor', setor_id=novo_setor.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar Setor: {e}', 'danger')
    return render_template('grupos/setores/form.html', form=form, ano=ano, versao=versao)

@grupos_bp.route('/setores/<int:setor_id>')
@login_required
@group_permission_required(Setor, 'view', 'supervisores')
def detalhes_setor(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    jornada_eventos = setor.jornada_eventos_setor.order_by(JornadaEvento.data_evento.desc()).all()

    pgs_ativos = setor.pequenos_grupos.filter(
        db.and_(
            PequenoGrupo.ativo == True,
            PequenoGrupo.data_multiplicacao.is_(None)
        )
    ).order_by(PequenoGrupo.nome).all()
    
    pgs_multiplicados = setor.pequenos_grupos.filter(
        db.and_(
            PequenoGrupo.ativo == False,
            PequenoGrupo.data_multiplicacao.isnot(None)
        )
    ).order_by(PequenoGrupo.nome).all()

    membros_do_setor = set(setor.membros_do_setor_completos)
    
    lista_dizimistas = sorted(
        [m for m in membros_do_setor if m.contribuiu_dizimo_ultimos_30d],
        key=lambda m: m.nome_completo
    )

    lista_ctm_frequentes = sorted(
        [m for m in membros_do_setor if m.presente_ctm_ultimos_30d],
        key=lambda m: m.nome_completo
    )

    lista_nao_dizimistas = sorted(
        [m for m in membros_do_setor if not m.contribuiu_dizimo_ultimos_30d],
        key=lambda m: m.nome_completo
    )

    lista_nao_ctm_frequentes = sorted(
        [m for m in membros_do_setor if not m.presente_ctm_ultimos_30d],
        key=lambda m: m.nome_completo
    )

    return render_template('grupos/setores/detalhes.html',  
                           setor=setor,
                           pgs_ativos=pgs_ativos,
                           pgs_multiplicados=pgs_multiplicados,
                           lista_dizimistas=lista_dizimistas,
                           lista_ctm_frequentes=lista_ctm_frequentes,
                           lista_nao_dizimistas=lista_nao_dizimistas,
                           lista_nao_ctm_frequentes=lista_nao_ctm_frequentes,
                           jornada_eventos=jornada_eventos,
                           config=Config, ano=ano, versao=versao)

@grupos_bp.route('/setores/<int:setor_id>/multiplicar_pgs', methods=['GET'])
@login_required
@group_permission_required(Setor, 'edit', 'supervisores')
def tela_multiplicacao_pgs(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    pgs_do_setor = setor.pequenos_grupos.all()

    form_multiplicacao = MultiplicacaoForm()

    pg_antigo_id = request.args.get('pg_id', type=int)
    pg_antigo = PequenoGrupo.query.get(pg_antigo_id) if pg_antigo_id else None

    if pg_antigo:
        membros_treinamento = [m for m in pg_antigo.membros_para_indicadores 
                               if m.status_treinamento_pg in ['Facilitador em Treinamento', 'Anfitrião em Treinamento']]
        lideres_atuais = []
        if pg_antigo.facilitador:
            lideres_atuais.append(pg_antigo.facilitador)
        if pg_antigo.anfitriao and pg_antigo.anfitriao.id != pg_antigo.facilitador.id:
            lideres_atuais.append(pg_antigo.anfitriao)

        membros_candidatos = list(set(membros_treinamento + lideres_atuais))
        membros_choices = [(m.id, f"{m.nome_completo} ({m.status_treinamento_pg or 'Líder Atual'})") for m in membros_candidatos]
        membros_choices.sort(key=lambda x: x[1])
        membros_choices.insert(0, (0, 'Selecione um membro'))

        form_multiplicacao.pg1.facilitador.choices = membros_choices
        form_multiplicacao.pg1.anfitriao.choices = membros_choices
        form_multiplicacao.pg2.facilitador.choices = membros_choices
        form_multiplicacao.pg2.anfitriao.choices = membros_choices
    
    setor_choices = [(setor.id, setor.nome)]
    form_multiplicacao.pg1.setor.choices = setor_choices
    form_multiplicacao.pg2.setor.choices = setor_choices

    hoje = date.today().strftime('%Y-%m-%d')

    return render_template('grupos/setores/multiplicar_pg.html',
                           setor=setor,
                           pgs=pgs_do_setor,
                           form_multiplicacao=form_multiplicacao,
                           hoje=hoje,
                           ano=ano,
                           versao=versao)

@grupos_bp.route('/pgs/<int:pg_id>/autorizar_multiplicacao', methods=['POST'])
@login_required
@group_permission_required(PequenoGrupo, 'supervisores')
def autorizar_multiplicacao(pg_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)
    autorizacao_status = request.form.get('autorizacao') == '1'
    
    pg.autorizacao_multiplicacao = autorizacao_status
    
    try:
        db.session.commit()
        if autorizacao_status:
            flash(f'A multiplicação do PG {pg.nome} foi autorizada!', 'success')
        else:
            flash(f'A autorização para multiplicação do PG {pg.nome} foi removida.', 'warning')
        return redirect(url_for('grupos.tela_multiplicacao_pgs', setor_id=pg.setor_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar a autorização: {e}', 'danger')
        return redirect(url_for('grupos.tela_multiplicacao_pgs', setor_id=pg.setor_id))

@grupos_bp.route('/pgs/<int:pg_id>/processar_multiplicacao', methods=['POST'])
@login_required
@group_permission_required(PequenoGrupo, 'supervisores')
def processar_multiplicacao(pg_id):
    pg_antigo = PequenoGrupo.query.get_or_404(pg_id)
    setor = pg_antigo.setor

    form = MultiplicacaoForm(pg_antigo_id=pg_antigo.id)

    membros_treinamento = [m for m in pg_antigo.membros_para_indicadores 
                           if m.status_treinamento_pg in ['Facilitador em Treinamento', 'Anfitrião em Treinamento']]
    lideres_atuais = []
    if pg_antigo.facilitador:
        lideres_atuais.append(pg_antigo.facilitador)
    if pg_antigo.anfitriao and pg_antigo.anfitriao.id != pg_antigo.facilitador.id:
        lideres_atuais.append(pg_antigo.anfitriao)
    membros_candidatos = list(set(membros_treinamento + lideres_atuais))

    membros_choices = [(m.id, f"{m.nome_completo} ({m.status_treinamento_pg or 'Líder Atual'})") for m in membros_candidatos]
    membros_choices.sort(key=lambda x: x[1])
    membros_choices.insert(0, (0, 'Selecione um membro'))

    form.pg1.facilitador.choices = membros_choices
    form.pg1.anfitriao.choices = membros_choices
    form.pg2.facilitador.choices = membros_choices
    form.pg2.anfitriao.choices = membros_choices

    setor_choices = [(pg_antigo.setor.id, pg_antigo.setor.nome)]
    form.pg1.setor.choices = setor_choices
    form.pg2.setor.choices = setor_choices

    if form.validate_on_submit():
        nome_antigo_original = pg_antigo.nome
        data_multiplicacao = form.data_multiplicacao.data
        data_formatada = data_multiplicacao.strftime('%d/%m/%Y')
        pg_antigo.nome = f"{nome_antigo_original} - {data_formatada}"
        pg_antigo.data_multiplicacao = data_multiplicacao
        pg_antigo.ativo = False        

        novo_pg1 = PequenoGrupo(
            nome=form.pg1.nome.data,
            facilitador_id=form.pg1.facilitador.data,
            anfitriao_id=form.pg1.anfitriao.data,
            setor_id=form.pg1.setor.data,
            dia_reuniao=form.pg1.dia_reuniao.data,
            horario_reuniao=form.pg1.horario_reuniao.data,
            autorizacao_multiplicacao=False
        )
        novo_pg2 = PequenoGrupo(
            nome=form.pg2.nome.data,
            facilitador_id=form.pg2.facilitador.data,
            anfitriao_id=form.pg2.anfitriao.data,
            setor_id=form.pg2.setor.data,
            dia_reuniao=form.pg2.dia_reuniao.data,
            horario_reuniao=form.pg2.horario_reuniao.data,
            autorizacao_multiplicacao=False
        )

        db.session.add_all([novo_pg1, novo_pg2])
        db.session.add(pg_antigo)
        
        try:
            db.session.commit()
            
            registrar_evento_jornada(
                tipo_acao='PG_MULTIPLICADO',
                descricao_detalhada=f'PG {nome_antigo_original} foi multiplicado, originando os PGs "{novo_pg1.nome}" e "{novo_pg2.nome}".',
                usuario_executor=current_user,
                pgs=[pg_antigo]
            )
            
            registrar_evento_jornada(
                tipo_acao='PG_MULTIPLICADO',
                descricao_detalhada=f'Nasceu da multiplicação do PG "{pg_antigo.nome}".',
                usuario_executor=current_user,
                pgs=[novo_pg1, novo_pg2]
            )
                        
            registrar_evento_jornada(
                tipo_acao='PG_MULTIPLICADO',
                descricao_detalhada=f'O PG "{pg_antigo.nome}" foi multiplicado, gerando os novos PGs: "{novo_pg1.nome}" e "{novo_pg2.nome}".',
                usuario_executor=current_user,
                setores=[pg_antigo.setor]
            )
            
            flash(f'PG {pg_antigo.nome} multiplicado com sucesso! Os novos PGs foram criados e os membros devem ser adicionados manualmente.', 'success')
            return redirect(url_for('grupos.detalhes_setor', setor_id=pg_antigo.setor_id))
        except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao processar a multiplicação: {e}', 'danger')
                    return redirect(url_for('grupos.tela_multiplicacao_pgs', setor_id=setor.id))

    for field, errors in form.errors.items():
        for error in errors:
            flash(f"Erro no campo {field}: {error}", 'danger')

    pgs_do_setor = setor.pequenos_grupos.all()
    hoje = date.today().strftime('%Y-%m-%d')
    return render_template('grupos/setores/multiplicar_pg.html',
                        setor=setor,
                        pgs=pgs_do_setor,
                        form_multiplicacao=form,
                        hoje=hoje,
                        ano=ano,
                        versao=versao)    

@grupos_bp.route('/setores/editar/<int:setor_id>', methods=['GET', 'POST'])
@login_required
@group_permission_required(Setor, 'edit', 'supervisores')
def editar_setor(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    form = SetorForm(obj=setor)
    
    if form.validate_on_submit():
        setor.nome = form.nome.data
        setor.area_id = form.area.data
        
        supervisores_antigos_ids = {s.id for s in setor.supervisores}
        supervisores_novos_ids = set(form.supervisores.data)

        setor.supervisores = []
        for supervisor_id in supervisores_novos_ids:
            supervisor = Membro.query.get(supervisor_id)
            if supervisor:
                setor.supervisores.append(supervisor)
        
        try:
            db.session.commit()

            novos_supervisores_adicionados = supervisores_novos_ids.difference(supervisores_antigos_ids)
            supervisores_removidos = supervisores_antigos_ids.difference(supervisores_novos_ids)

            for supervisor_id in novos_supervisores_adicionados:
                supervisor = Membro.query.get(supervisor_id)
                if supervisor:
                    registrar_evento_jornada(
                        tipo_acao='LIDERANCA_ALTERADA', 
                        descricao_detalhada=f'Se tornou supervisor(a) do setor "{setor.nome}".', 
                        usuario_executor=current_user, 
                        membros=[supervisor]
                    )
            
            for supervisor_id in supervisores_removidos:
                supervisor = Membro.query.get(supervisor_id)
                if supervisor:
                    registrar_evento_jornada(
                        tipo_acao='LIDERANCA_ALTERADA', 
                        descricao_detalhada=f'Deixou de ser supervisor(a) do setor "{setor.nome}".', 
                        usuario_executor=current_user, 
                        membros=[supervisor]
                    )

            flash('Setor atualizado com sucesso!', 'success')
            return redirect(url_for('grupos.detalhes_setor', setor_id=setor.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar Setor: {e}', 'danger')
    elif request.method == 'GET':
        form.supervisores.data = [s.id for s in setor.supervisores]
        form.area.data = setor.area_id
        
    return render_template('grupos/setores/form.html', form=form, setor=setor, ano=ano, versao=versao)

@grupos_bp.route('/setores/<int:setor_id>/multiplicar_pgs', methods=['GET', 'POST'])
@login_required
@group_permission_required(Setor, 'edit', 'supervisores')
def multiplicar_pgs_setor(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    
    if request.method == 'GET':
        pgs_do_setor = setor.pequenos_grupos.all()
        return render_template('grupos/setores/multiplicar_pg.html', setor=setor, pgs=pgs_do_setor, ano=ano, versao=versao)
    
    if request.method == 'POST':
        pass

@grupos_bp.route('/setores/deletar/<int:setor_id>', methods=['POST'])
@login_required
@admin_required
def deletar_setor(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    if setor.pequenos_grupos.count() > 0:
        flash(f'Não é possível deletar o Setor "{setor.nome}" pois ele possui Pequenos Grupos vinculados.', 'danger')
        return redirect(url_for('grupos.listar_setores'))

    nome_setor = setor.nome
    supervisores_antigos = list(setor.supervisores)

    try:
        db.session.delete(setor)
        db.session.commit()
        flash('Setor deletado com sucesso!', 'success')
        for supervisor in supervisores_antigos:
            registrar_evento_jornada(
                tipo_acao='LIDERANCA_ALTERADA', 
                descricao_detalhada=f'Deixou de ser supervisor(a) do setor "{nome_setor}".', 
                usuario_executor=current_user, 
                membros=[supervisor]
            )
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar Setor: {e}', 'danger')
    return redirect(url_for('grupos.listar_setores'))

@grupos_bp.route('/pgs')
@login_required
def listar_pgs():
    return redirect(url_for('grupos.listar_grupos_unificada', tipo='pgs'))

def get_nome(membro_id):
    """Obtém o nome do facilitador para sugerir o nome do PG."""
    membro = Membro.query.get(membro_id)
    if membro:
        return membro.nome_completo
    return ""

def verificar_e_sugerir_nome_pg(nome_base, sufixo):
    """Verifica a unicidade e constrói o nome final."""
    nome_final = nome_base
    if sufixo:
        nome_final = f"{nome_base} - {sufixo}"

    pg_existente = PequenoGrupo.query.filter_by(nome=nome_final).first()
    
    if pg_existente:
        return None, True, nome_final
    
    return nome_final, False, None

@grupos_bp.route('/pgs/criar', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_pg():
    form = PequenoGrupoForm()
    nome_sugerido_base = None

    facilitador_id_url = request.args.get('facilitador', type=int)

    if request.method == 'GET' and facilitador_id_url and facilitador_id_url != 0:
        form.facilitador.data = facilitador_id_url 
        nome_sugerido_base = get_nome(facilitador_id_url)
        if nome_sugerido_base:
            form.nome.data = nome_sugerido_base
    
    if form.validate_on_submit():
        nome_final = form.nome.data 

        novo_pg = PequenoGrupo(
            nome=nome_final,
            facilitador_id=form.facilitador.data,
            anfitriao_id=form.anfitriao.data,
            setor_id=form.setor.data,
            dia_reuniao=form.dia_reuniao.data,
            horario_reuniao=form.horario_reuniao.data
        )
        db.session.add(novo_pg)

        try:
            db.session.commit()
            flash('Pequeno Grupo criado com sucesso!', 'success')
            registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Se tornou facilitador(a) do PG {novo_pg.nome}.', usuario_executor=current_user, membros=[novo_pg.facilitador])
            registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Se tornou anfitrião do PG {novo_pg.nome}.', usuario_executor=current_user, membros=[novo_pg.anfitriao])
            return redirect(url_for('grupos.detalhes_pg', pg_id=novo_pg.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar Pequeno Grupo: {e}', 'danger')

    elif request.method == 'POST':
        nome_sugerido_base = get_nome(form.facilitador.data)
        
    return render_template('grupos/pgs/form.html', form=form, nome_sugerido_base=nome_sugerido_base, ano=ano, versao=versao)

@grupos_bp.route('/pgs/<int:pg_id>')
@login_required
@group_permission_required(PequenoGrupo, 'view')
def detalhes_pg(pg_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)

    if not pg.ativo:
        return render_template('grupos/pgs/detalhes_inativo.html', pg=pg, ano=ano, versao=versao)
    
    participantes_pg_ids = [m.id for m in pg.membros_completos]
    ctm_dados_alunos = []

    for membro in pg.membros_completos:
        if membro.turmas_ctm:
            for turma_ctm in membro.turmas_ctm:
                total_aulas = AulaRealizada.query.filter_by(turma_id=turma_ctm.id).count()
                
                total_presencas = Presenca.query.filter(
                    and_(
                        Presenca.membro_id == membro.id,
                        Presenca.aula_realizada.has(AulaRealizada.turma_id == turma_ctm.id)
                    )
                ).count()
                
                conclusao = ConclusaoCTM.query.filter_by(membro_id=membro.id, turma_id=turma_ctm.id).first()
                status_conclusao = conclusao.status_conclusao if conclusao else 'Em andamento'
                
                ctm_dados_alunos.append({
                    'membro': membro,
                    'turma': turma_ctm,
                    'classe': turma_ctm.classe,
                    'total_aulas': total_aulas,
                    'total_presencas': total_presencas,
                    'status_conclusao': status_conclusao
                })

    jornada_eventos = pg.jornada_eventos_pg.order_by(JornadaEvento.data_evento.desc()).all()
    membros_disponiveis = Membro.query.filter(Membro.id.notin_(participantes_pg_ids), Membro.pg_id == None).order_by(Membro.nome_completo).all()

    return render_template('grupos/pgs/detalhes.html',
                           pg=pg,
                           ctm_dados_alunos=ctm_dados_alunos,
                           membros_disponiveis=membros_disponiveis,
                           jornada_eventos=jornada_eventos,
                           config=Config, ano=ano, versao=versao)

@grupos_bp.route('/pgs/editar/<int:pg_id>', methods=['GET', 'POST'])
@login_required
@group_permission_required(PequenoGrupo, 'edit')
def editar_pg(pg_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)
    membro_atual_id = current_user.membro.id if current_user.membro else None

    is_admin = current_user.has_permission('admin')
    is_area_supervisor = is_supervisor_da_area(membro_atual_id, pg)
    is_sector_supervisor = is_supervisor_do_setor(membro_atual_id, pg)
    is_facilitator = is_pg_facilitator(membro_atual_id, pg)

    can_access_inactive = is_admin or is_area_supervisor or is_sector_supervisor
    if not pg.ativo and not can_access_inactive:
        flash('Não é possível editar um Pequeno Grupo inativo.', 'danger')
        return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))
    
    form = PequenoGrupoForm(
        obj=pg,
        pg=pg,
        is_admin=is_admin,
        is_area_supervisor=is_area_supervisor,
        is_sector_supervisor=is_sector_supervisor,
        is_facilitator=is_facilitator,
        formdata=request.form if request.method == 'POST' else None
    )

    facilitador_antigo = pg.facilitador
    anfitriao_antigo = pg.anfitriao
    
    if form.validate_on_submit():        
        novo_facilitador_id_str = request.form.get('facilitador')
        if novo_facilitador_id_str is not None:
            pg.facilitador_id = int(novo_facilitador_id_str)
        
        novo_anfitriao_id_str = request.form.get('anfitriao')
        if novo_anfitriao_id_str is not None:
            pg.anfitriao_id = int(novo_anfitriao_id_str)

        novo_setor_id_str = request.form.get('setor')
        if novo_setor_id_str is not None:
            pg.setor_id = int(novo_setor_id_str)
            
        pg.nome = form.nome.data
        pg.dia_reuniao = form.dia_reuniao.data
        pg.horario_reuniao = form.horario_reuniao.data

        try:
            db.session.commit()
            flash('Pequeno Grupo atualizado com sucesso!', 'success')
            
            if facilitador_antigo and facilitador_antigo.id != pg.facilitador_id:
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Deixou de ser facilitador(a) do PG {pg.nome}.', usuario_executor=current_user, membros=[facilitador_antigo])
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Se tornou facilitador(a) do PG {pg.nome}.', usuario_executor=current_user, membros=[pg.facilitador])
            if anfitriao_antigo and anfitriao_antigo.id != pg.anfitriao_id:
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Deixou de ser anfitrião do PG {pg.nome}.', usuario_executor=current_user, membros=[anfitriao_antigo])
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Se tornou anfitrião do PG {pg.nome}.', usuario_executor=current_user, membros=[pg.anfitriao])
                
            return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar Pequeno Grupo: {e}', 'danger')
    
    elif request.method == 'POST':
        current_app.logger.error(f"Falha de validação no editar_pg. Erros: {form.errors}")
        
        if form.errors:
            flash('Falha na validação do formulário. Por favor, verifique os campos em vermelho.', 'danger')
        else:
            flash('As alterações não puderam ser salvas. Tente novamente.', 'danger')

    elif request.method == 'GET':
        form.facilitador.data = pg.facilitador_id
        form.anfitriao.data = pg.anfitriao_id
        form.setor.data = pg.setor_id

    return render_template('grupos/pgs/form.html', 
                           form=form, 
                           pg=pg, 
                           is_area_supervisor=is_area_supervisor,
                           is_sector_supervisor=is_sector_supervisor,
                           ano=ano, 
                           versao=versao)

@grupos_bp.route('/pgs/fechar/<int:pg_id>', methods=['POST'])
@login_required
def fechar_pg(pg_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)
    membro_atual_id = current_user.membro.id if current_user.membro else None
    
    form = PequenoGrupoForm(pg=pg) 

    is_admin = current_user.has_permission('admin')
    is_area_supervisor = is_supervisor_da_area(membro_atual_id, pg)
    is_sector_supervisor = is_supervisor_do_setor(membro_atual_id, pg)

    can_close = is_admin or is_area_supervisor or is_sector_supervisor
    
    if not can_close:
        flash('Você não tem permissão para fechar este Pequeno Grupo.', 'danger')
        return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))

    if pg.ativo:
        pg.ativo = False
        
        try:
            db.session.commit()
            flash(f'Pequeno Grupo "{pg.nome}" foi fechado com sucesso.', 'success')
            
            registrar_evento_jornada(tipo_acao='PG_FECHADO', 
                                     descricao_detalhada=f'O PG "{pg.nome}" foi fechado.', 
                                     usuario_executor=current_user)

            return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao fechar Pequeno Grupo: {e}', 'danger')
            
    return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))

@grupos_bp.route('/pgs/deletar/<int:pg_id>', methods=['POST'])
@login_required
@admin_required
def deletar_pg(pg_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)
    
    for membro in pg.membros_completos:
        membro.pg_id = None
        db.session.add(membro)

    db.session.delete(pg)
    
    try:
        db.session.commit()
        flash(f'Pequeno Grupo "{pg.nome}" foi deletado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar Pequeno Grupo: {e}', 'danger')
        
    return redirect(url_for('grupos.listar_grupos_unificada'))

@grupos_bp.route('/pgs/<int:pg_id>/adicionar', methods=['POST'])
@login_required
@group_permission_required(PequenoGrupo, 'manage_participants')
def adicionar_participante(pg_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)
    membro_id = request.form.get('membro_id')
    membro = Membro.query.get(membro_id)
    if membro and membro.pg_id is None:
        pg_nome = pg.nome
        membro.pg_id = pg.id
        try:
            db.session.commit()
            flash(f'{membro.nome_completo} adicionado(a) ao PG {pg.nome} como participante!', 'success')
            registrar_evento_jornada(tipo_acao='PARTICIPANTE_ADICIONADO_PG', descricao_detalhada=f'Se tornou participante do PG {pg_nome}.', usuario_executor=current_user, membros=[membro])
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar participante: {e}', 'danger')
    else:
        flash('Membro não pertence a este Pequeno Grupo.', 'danger')
    return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))

@grupos_bp.route('/buscar_membros_pgs')
@login_required
def buscar_membros_pgs():
    term = request.args.get('term', '')
    
    membros = Membro.query.filter(
        or_(
            Membro.nome_completo.ilike(f'%{term}%'),
        ),
        Membro.ativo == True,
        Membro.pg_id == None,
        Membro.id != current_user.membro.id
    ).order_by(Membro.nome_completo).limit(20).all()
    
    results = []
    for membro in membros:
        results.append({
            'id': membro.id,
            'text': membro.nome_completo
        })
    
    return jsonify(items=results)

@grupos_bp.route('/pgs/<int:pg_id>/remover/<int:membro_id>', methods=['POST'])
@login_required
@group_permission_required(PequenoGrupo, 'manage_participants')
def remover_participante(pg_id, membro_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)
    membro = Membro.query.get_or_404(membro_id)
    if membro.pg_id == pg.id:
        pg_nome = pg.nome
        membro.pg_id = None
        membro.status_treinamento_pg = 'Nenhum'
        membro.participou_ctm = False
        membro.participou_encontro_deus = False
        membro.batizado_aclamado = False
        try:
            db.session.commit()
            flash(f'{membro.nome_completo} removido(a) do {pg.nome}!', 'success')
            registrar_evento_jornada(tipo_acao='PARTICIPANTE_REMOVIDO_PG', descricao_detalhada=f'Deixou de ser participante do PG {pg_nome}.', usuario_executor=current_user, membros=[membro])
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao remover participante: {e}', 'danger')
    else:
        flash('Membro não pertence a este Pequeno Grupo.', 'danger')
    return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))

@grupos_bp.route('/pgs/<int:pg_id>/atualizar-indicadores/<int:membro_id>', methods=['POST'])
@login_required
@group_permission_required(PequenoGrupo, 'manage_participants')
def atualizar_indicadores(pg_id, membro_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)
    membro = Membro.query.get_or_404(membro_id)
    
    if membro.id not in [m.id for m in pg.membros_para_indicadores]:
        flash('Este membro não pode ter seus indicadores atualizados neste Pequeno Grupo.', 'danger')
        return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))
    
    status_treinamento = request.form.get(f'status_treinamento_pg_{membro.id}')

    membro.participou_ctm = 'participou_ctm' in request.form
    membro.participou_encontro_deus = 'participou_encontro_deus' in request.form

    if membro.status == 'Não-Membro':
        membro.batizado_aclamado = 'batizado_aclamado' in request.form
    else:
        membro.batizado_aclamado = False

    membro.status_treinamento_pg = status_treinamento

    try:
        db.session.add(membro)
        db.session.commit()
        flash(f'Indicadores de {membro.nome_completo} atualizados com sucesso!', 'success')
        descricao_membro = f'Indicadores atualizados no PG {pg.nome}.'
        descricao_setor = f'Indicadores do PG {pg.nome} atualizados. (Membro: {membro.nome_completo})'
        registrar_evento_jornada(tipo_acao='INDICADORES_PG_ATUALIZADOS', descricao_detalhada=descricao_membro, usuario_executor=current_user, membros=[membro])
        if pg.setor:
            registrar_evento_jornada(tipo_acao='INDICADORES_PG_ATUALIZADOS', descricao_detalhada=descricao_setor, usuario_executor=current_user, setores=[pg.setor])
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar indicadores: {e}', 'danger')
    return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))

@grupos_bp.route('/areas/<int:area_id>/gerenciar_metas', methods=['GET', 'POST'])
@login_required
@group_permission_required(Area, 'edit', 'supervisores')
def gerenciar_metas_da_area(area_id):
    area = Area.query.get_or_404(area_id)
    meta_vigente = area.meta_vigente
    
    pode_editar = True
    if meta_vigente and meta_vigente.data_fim >= date.today():
        pode_editar = False
        flash(f'As metas atuais são válidas até {meta_vigente.data_fim.strftime("%d/%m/%Y")}. Não é possível editar antes desta data.', 'warning')

    form = AreaMetasForm()

    if form.validate_on_submit() and pode_editar:
        if meta_vigente:
            meta_vigente.ativa = False
            db.session.add(meta_vigente)

        nova_meta = AreaMetaVigente(
            meta_facilitadores_treinamento_pg=form.meta_facilitadores_treinamento_pg.data,
            meta_anfitrioes_treinamento_pg=form.meta_anfitrioes_treinamento_pg.data,
            meta_ctm_participantes_pg=form.meta_ctm_participantes_pg.data,
            meta_encontro_deus_participantes_pg=form.meta_encontro_deus_participantes_pg.data,
            meta_batizados_aclamados_pg=form.meta_batizados_aclamados_pg.data,
            meta_multiplicacoes_pg_pg=form.meta_multiplicacoes_pg_pg.data,
            data_fim=form.data_fim.data,
            area_id=area.id
        )
        db.session.add(nova_meta)

        try:
            db.session.commit()
            flash('Metas da área atualizadas e propagadas para os grupos abaixo!', 'success')
            return redirect(url_for('grupos.detalhes_area', area_id=area.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar as metas: {e}', 'danger')

    elif request.method == 'GET':
        if meta_vigente:
            form.meta_facilitadores_treinamento_pg.data = meta_vigente.meta_facilitadores_treinamento_pg
            form.meta_anfitrioes_treinamento_pg.data = meta_vigente.meta_anfitrioes_treinamento_pg
            form.meta_ctm_participantes_pg.data = meta_vigente.meta_ctm_participantes_pg
            form.meta_encontro_deus_participantes_pg.data = meta_vigente.meta_encontro_deus_participantes_pg
            form.meta_batizados_aclamados_pg.data = meta_vigente.meta_batizados_aclamados_pg
            form.meta_multiplicacoes_pg_pg.data = meta_vigente.meta_multiplicacoes_pg_pg
            form.data_fim.data = meta_vigente.data_fim

    return render_template(
        'grupos/areas/form_metas_area.html',
        form=form,
        area=area,
        pode_editar=pode_editar,
        meta_vigente=meta_vigente,
        ano=ano,
        versao=versao
    )

@grupos_bp.route('/areas/<int:area_id>/admin_gerenciar_metas', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_gerenciar_metas_da_area(area_id):
    area = Area.query.get_or_404(area_id)
    form = AreaMetasForm()

    if form.validate_on_submit():
        try:
            AreaMetaVigente.query.filter_by(area_id=area.id).delete()
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao limpar metas antigas: {e}', 'danger')
            return redirect(url_for('grupos.detalhes_area', area_id=area.id))

        nova_meta = AreaMetaVigente(
                meta_facilitadores_treinamento_pg=form.meta_facilitadores_treinamento_pg.data,
                meta_anfitrioes_treinamento_pg=form.meta_anfitrioes_treinamento_pg.data,
                meta_ctm_participantes_pg=form.meta_ctm_participantes_pg.data,
                meta_encontro_deus_participantes_pg=form.meta_encontro_deus_participantes_pg.data,
                meta_batizados_aclamados_pg=form.meta_batizados_aclamados_pg.data,
                meta_multiplicacoes_pg_pg=form.meta_multiplicacoes_pg_pg.data,
                data_inicio=form.data_inicio.data,
                data_fim=form.data_fim.data,
                area_id=area.id
            )

        db.session.add(nova_meta)

        try:
            db.session.commit()
            flash('Metas da área (Admin) redefinidas com sucesso! Um novo ciclo foi iniciado.', 'success')
            return redirect(url_for('grupos.detalhes_area', area_id=area.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar a nova meta (Admin): {e}', 'danger')

    elif request.method == 'GET':
        # Buscamos a meta mais recente para carregar o formulário
        meta_vigente_recente = AreaMetaVigente.query.filter_by(area_id=area.id).order_by(AreaMetaVigente.data_inicio.desc()).first()
        
        if meta_vigente_recente:
            form.meta_facilitadores_treinamento_pg.data = meta_vigente_recente.meta_facilitadores_treinamento_pg
            form.meta_anfitrioes_treinamento_pg.data = meta_vigente_recente.meta_anfitrioes_treinamento_pg
            form.meta_ctm_participantes_pg.data = meta_vigente_recente.meta_ctm_participantes_pg
            form.meta_encontro_deus_participantes_pg.data = meta_vigente_recente.meta_encontro_deus_participantes_pg
            form.meta_batizados_aclamados_pg.data = meta_vigente_recente.meta_batizados_aclamados_pg
            form.meta_multiplicacoes_pg_pg.data = meta_vigente_recente.meta_multiplicacoes_pg_pg
            form.data_inicio.data = meta_vigente_recente.data_inicio
            form.data_fim.data = meta_vigente_recente.data_fim

    if request.method == 'POST' and not form.validate():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo {field}: {error}", 'danger')

    return render_template(
        'grupos/areas/form_metas_area.html',
        form=form,
        area=area,
        pode_editar=True,
        meta_vigente=AreaMetaVigente.query.filter_by(area_id=area.id).order_by(AreaMetaVigente.data_inicio.desc()).first(),
        versao=versao
    )

@grupos_bp.route('/buscar_membros_ativos')
@login_required
def buscar_membros_ativos():
    search_term = request.args.get('q', '')
    
    query = Membro.query.filter(
        Membro.nome_completo.ilike(f'%{search_term}%'),
        Membro.ativo == True
    )
    
    membros = query.order_by(Membro.nome_completo).limit(20).all()
    
    results = []
    for membro in membros:
        results.append({'id': membro.id, 'text': membro.nome_completo})
        
    return jsonify(results=results)
