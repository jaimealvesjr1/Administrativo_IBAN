from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.grupos.models import Area, Setor, PequenoGrupo, AreaMetaVigente, setor_supervisores
from app.grupos.forms import AreaForm, SetorForm, PequenoGrupoForm, AreaMetasForm, MultiplicacaoForm
from app.eventos.models import Evento, participantes_evento
from app.membresia.models import Membro
from app.financeiro.models import Contribuicao
from app.auth.models import User
from app.jornada.models import registrar_evento_jornada, JornadaEvento
from config import Config
from app.decorators import admin_required, group_permission_required, leader_required
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import joinedload
from app.ctm.models import TurmaCTM, AulaRealizada, Presenca, ConclusaoCTM
from datetime import date, datetime, timedelta

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

    if current_user.has_permission('admin') or current_user.has_permission('secretaria'):
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

    meta_vigente = area.meta_vigente
    data_inicio_meta = meta_vigente.data_inicio if meta_vigente else date.min
    data_fim_meta = meta_vigente.data_fim if meta_vigente else date.max

    setor_ids = [s.id for s in area.setores]
    
    pg_ids_ativos_query = db.session.query(PequenoGrupo.id)\
                              .filter(PequenoGrupo.setor_id.in_(setor_ids), 
                                      PequenoGrupo.ativo == True)
    
    pg_ids_ativos = [id[0] for id in pg_ids_ativos_query.all()]
    num_pgs_ativos = len(pg_ids_ativos)

    membro_ids_supervisores_area = {s.id for s in area.supervisores}
    
    membro_ids_supervisores_setor_query = db.session.query(setor_supervisores.c.supervisor_id)\
                                              .filter(setor_supervisores.c.setor_id.in_(setor_ids))
    membro_ids_supervisores_setor = {id[0] for id in membro_ids_supervisores_setor_query.all()}

    membro_ids_pgs_query = db.session.query(Membro.id)\
                               .filter(Membro.pg_id.in_(pg_ids_ativos))
    membro_ids_pgs = {id[0] for id in membro_ids_pgs_query.all()}

    facilitador_ids_query = db.session.query(PequenoGrupo.facilitador_id).filter(PequenoGrupo.id.in_(pg_ids_ativos))
    anfitriao_ids_query = db.session.query(PequenoGrupo.anfitriao_id).filter(PequenoGrupo.id.in_(pg_ids_ativos))

    membro_ids_lideres_pg = {id[0] for id in facilitador_ids_query.all()}
    membro_ids_lideres_pg.update({id[0] for id in anfitriao_ids_query.all()})

    membro_ids_da_area = (membro_ids_supervisores_area | 
                          membro_ids_supervisores_setor | 
                          membro_ids_pgs | 
                          membro_ids_lideres_pg)
    
    if not membro_ids_da_area:
        membro_ids_da_area = []

    metricas_area = {}
    
    metricas_area['num_pequenos_grupos_ativos'] = num_pgs_ativos

    if meta_vigente:
        metricas_area['meta_facilitadores_treinamento'] = meta_vigente.meta_facilitadores_treinamento_pg * num_pgs_ativos
        metricas_area['meta_anfitrioes_treinamento'] = meta_vigente.meta_anfitrioes_treinamento_pg * num_pgs_ativos
        metricas_area['meta_ctm_participantes'] = meta_vigente.meta_ctm_participantes_pg * num_pgs_ativos
        metricas_area['meta_encontro_deus_participantes'] = meta_vigente.meta_encontro_deus_participantes_pg * num_pgs_ativos
        metricas_area['meta_batizados_aclamados'] = meta_vigente.meta_batizados_aclamados_pg * num_pgs_ativos
        metricas_area['meta_multiplicacoes_pg'] = meta_vigente.meta_multiplicacoes_pg_pg * num_pgs_ativos
    else:
        metricas_area['meta_facilitadores_treinamento'] = 0
        metricas_area['meta_anfitrioes_treinamento'] = 0
        metricas_area['meta_ctm_participantes'] = 0
        metricas_area['meta_encontro_deus_participantes'] = 0
        metricas_area['meta_batizados_aclamados'] = 0
        metricas_area['meta_multiplicacoes_pg'] = 0

    trinta_dias_atras = date.today() - timedelta(days=35)
    
    # Subquery para presenças no CTM nos últimos 30 dias
    subquery_ctm_presentes = db.session.query(Presenca.membro_id)\
        .join(AulaRealizada)\
        .filter(AulaRealizada.data >= trinta_dias_atras)\
        .distinct()

    # Query principal de membros
    query_membros_indicadores = db.session.query(
        Membro.status_treinamento_pg,
        Membro.batizado_aclamado,
        Membro.data_recepcao,
        Membro.status,
        Membro.id.in_(subquery_ctm_presentes).label('presente_ctm_30d')
    ).filter(Membro.id.in_(membro_ids_da_area)).all()

    metricas_area['num_facilitadores_treinamento_atuais_agregado'] = 0
    metricas_area['num_anfitrioes_treinamento_atuais_agregado'] = 0
    metricas_area['num_ctm_participantes_atuais_agregado'] = 0
    metricas_area['num_batizados_aclamados_atuais_agregado'] = 0

    for membro_indicador in query_membros_indicadores:
        if membro_indicador.status_treinamento_pg == 'Facilitador em Treinamento':
            metricas_area['num_facilitadores_treinamento_atuais_agregado'] += 1
        if membro_indicador.status_treinamento_pg == 'Anfitrião em Treinamento':
            metricas_area['num_anfitrioes_treinamento_atuais_agregado'] += 1
        if membro_indicador.presente_ctm_30d:
            metricas_area['num_ctm_participantes_atuais_agregado'] += 1
        
        if membro_indicador.data_recepcao and data_inicio_meta <= membro_indicador.data_recepcao <= data_fim_meta:
            if membro_indicador.status == 'Não-Membro' and membro_indicador.batizado_aclamado:
                metricas_area['num_batizados_aclamados_atuais_agregado'] += 1
            elif membro_indicador.status != 'Não-Membro':
                metricas_area['num_batizados_aclamados_atuais_agregado'] += 1
    
    eventos_encontro_ids = db.session.query(Evento.id).filter(
        Evento.tipo_evento == 'Encontro com Deus',
        Evento.concluido == True,
        Evento.data_evento.between(data_inicio_meta, data_fim_meta)
    ).all()

    if eventos_encontro_ids:
        metricas_area['num_encontro_deus_participantes_atuais_agregado'] = db.session.query(participantes_evento)\
            .filter(participantes_evento.c.evento_id.in_([e_id[0] for e_id in eventos_encontro_ids]),
                    participantes_evento.c.membro_id.in_(membro_ids_da_area))\
            .count()
    else:
        metricas_area['num_encontro_deus_participantes_atuais_agregado'] = 0

    metricas_area['num_multiplicacoes_pg_atuais_agregado'] = PequenoGrupo.query\
        .filter(PequenoGrupo.setor_id.in_(setor_ids),
                PequenoGrupo.data_multiplicacao.isnot(None),
                PequenoGrupo.data_multiplicacao.between(data_inicio_meta, data_fim_meta))\
        .count()

    dizimistas_por_setor_chart = { 'labels': [], 'dizimistas': [], 'nao_dizimistas': [] }
    ctm_por_setor = []
    membros_por_setor = []
    pgs_ativos_por_setor = []

    trinta_dias_atras_contrib = date.today() - timedelta(days=35)

    pgs_ativos_por_setor_query = db.session.query(Setor.id, func.count(PequenoGrupo.id))\
        .join(PequenoGrupo, PequenoGrupo.setor_id == Setor.id)\
        .filter(Setor.area_id == area_id, PequenoGrupo.ativo == True)\
        .group_by(Setor.id).all()
    pgs_ativos_por_setor_dict = dict(pgs_ativos_por_setor_query)

    for setor in area.setores:
        membro_ids_setor_query = db.session.query(Membro.id)\
            .join(PequenoGrupo, Membro.pg_id == PequenoGrupo.id, isouter=True)\
            .filter(PequenoGrupo.setor_id == setor.id, Membro.ativo == True)
        
        membro_ids_setor = {m[0] for m in membro_ids_setor_query.all()}
        
        lideres_pgs_setor_query = db.session.query(PequenoGrupo.facilitador_id, PequenoGrupo.anfitriao_id)\
            .filter(PequenoGrupo.setor_id == setor.id, PequenoGrupo.ativo == True)
        for f_id, a_id in lideres_pgs_setor_query.all():
            membro_ids_setor.add(f_id)
            membro_ids_setor.add(a_id)

        for supervisor in setor.supervisores:
             membro_ids_setor.add(supervisor.id)

        num_membros_setor = len(membro_ids_setor)
        membros_por_setor.append({'setor_nome': setor.nome, 'count': num_membros_setor})

        pgs_ativos_por_setor.append({
            'id': setor.id,
            'nome': setor.nome,
            'pgs_ativos': pgs_ativos_por_setor_dict.get(setor.id, 0)
        })

        if num_membros_setor > 0:
            dizimistas_30d_setor = db.session.query(func.count(Contribuicao.membro_id.distinct()))\
                .filter(Contribuicao.membro_id.in_(membro_ids_setor),
                        Contribuicao.tipo == 'Dízimo',
                        Contribuicao.data_lanc >= trinta_dias_atras_contrib)\
                .scalar() or 0
            
            ctm_frequentes_setor = db.session.query(func.count(Presenca.membro_id.distinct()))\
                .join(AulaRealizada)\
                .filter(Presenca.membro_id.in_(membro_ids_setor),
                        AulaRealizada.data >= trinta_dias_atras)\
                .scalar() or 0
        else:
            dizimistas_30d_setor = 0
            ctm_frequentes_setor = 0

        dizimistas_por_setor_chart['labels'].append(setor.nome)
        dizimistas_por_setor_chart['dizimistas'].append(dizimistas_30d_setor)
        dizimistas_por_setor_chart['nao_dizimistas'].append(num_membros_setor - dizimistas_30d_setor)
        
        ctm_por_setor.append({
            'setor_nome': setor.nome,
            'count': ctm_frequentes_setor
        })
    
    pgs_ativos_por_setor.sort(key=lambda x: x['nome'])

    return render_template('grupos/areas/detalhes.html',
                           area=area,
                           jornada_eventos=jornada_eventos,
                           metricas_area=metricas_area,
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

    meta_vigente = setor.area.meta_vigente
    data_inicio_meta = meta_vigente.data_inicio if meta_vigente else date.min
    data_fim_meta = meta_vigente.data_fim if meta_vigente else date.max

    pgs_ativos_query = setor.pequenos_grupos.filter(
        PequenoGrupo.ativo == True,
        PequenoGrupo.data_multiplicacao.is_(None)
    )
    pgs_ativos = pgs_ativos_query.order_by(PequenoGrupo.nome).all()
    pgs_ativos_ids = [pg.id for pg in pgs_ativos]
    num_pgs_ativos = len(pgs_ativos_ids)

    pgs_multiplicados = setor.pequenos_grupos.filter(
        db.and_(
            PequenoGrupo.ativo == False,
            PequenoGrupo.data_multiplicacao.isnot(None)
        )
    ).order_by(PequenoGrupo.nome).all()

    membro_ids_supervisores_setor = {s.id for s in setor.supervisores}
    
    membro_ids_pgs_query = db.session.query(Membro.id)\
                               .filter(Membro.pg_id.in_(pgs_ativos_ids))
    membro_ids_pgs = {id[0] for id in membro_ids_pgs_query.all()}
    
    facilitador_ids_query = db.session.query(PequenoGrupo.facilitador_id).filter(PequenoGrupo.id.in_(pgs_ativos_ids))
    anfitriao_ids_query = db.session.query(PequenoGrupo.anfitriao_id).filter(PequenoGrupo.id.in_(pgs_ativos_ids))
    
    membro_ids_lideres_pg = {id[0] for id in facilitador_ids_query.all()}
    membro_ids_lideres_pg.update({id[0] for id in anfitriao_ids_query.all()})

    membro_ids_do_setor = (membro_ids_supervisores_setor | 
                           membro_ids_pgs | 
                           membro_ids_lideres_pg)
    
    if not membro_ids_do_setor:
        membro_ids_do_setor = []

    num_participantes_totais = len(membro_ids_do_setor)
    
    metricas_setor = {}
    
    if meta_vigente:
        metricas_setor['meta_facilitadores_treinamento'] = meta_vigente.meta_facilitadores_treinamento_pg * num_pgs_ativos
        metricas_setor['meta_anfitrioes_treinamento'] = meta_vigente.meta_anfitrioes_treinamento_pg * num_pgs_ativos
        metricas_setor['meta_ctm_participantes'] = meta_vigente.meta_ctm_participantes_pg * num_pgs_ativos
        metricas_setor['meta_encontro_deus_participantes'] = meta_vigente.meta_encontro_deus_participantes_pg * num_pgs_ativos
        metricas_setor['meta_batizados_aclamados'] = meta_vigente.meta_batizados_aclamados_pg * num_pgs_ativos
        metricas_setor['meta_multiplicacoes_pg'] = meta_vigente.meta_multiplicacoes_pg_pg * num_pgs_ativos
    else:
        metricas_setor['meta_facilitadores_treinamento'] = 0
        metricas_setor['meta_anfitrioes_treinamento'] = 0
        metricas_setor['meta_ctm_participantes'] = 0
        metricas_setor['meta_encontro_deus_participantes'] = 0
        metricas_setor['meta_batizados_aclamados'] = 0
        metricas_setor['meta_multiplicacoes_pg'] = 0

    trinta_dias_atras = date.today() - timedelta(days=35)
    
    subquery_ctm_presentes = db.session.query(Presenca.membro_id)\
        .join(AulaRealizada)\
        .filter(AulaRealizada.data >= trinta_dias_atras)\
        .distinct()

    query_membros_indicadores = db.session.query(
        Membro.status_treinamento_pg,
        Membro.batizado_aclamado,
        Membro.data_recepcao,
        Membro.status,
        Membro.id.in_(subquery_ctm_presentes).label('presente_ctm_30d')
    ).filter(Membro.id.in_(membro_ids_do_setor)).all()

    metricas_setor['num_facilitadores_treinamento_atuais_agregado'] = 0
    metricas_setor['num_anfitrioes_treinamento_atuais_agregado'] = 0
    metricas_setor['num_ctm_participantes_atuais_agregado'] = 0
    metricas_setor['num_batizados_aclamados_atuais_agregado'] = 0
    
    for membro_indicador in query_membros_indicadores:
        if membro_indicador.status_treinamento_pg == 'Facilitador em Treinamento':
            metricas_setor['num_facilitadores_treinamento_atuais_agregado'] += 1
        if membro_indicador.status_treinamento_pg == 'Anfitrião em Treinamento':
            metricas_setor['num_anfitrioes_treinamento_atuais_agregado'] += 1
        if membro_indicador.presente_ctm_30d:
            metricas_setor['num_ctm_participantes_atuais_agregado'] += 1
        
        if membro_indicador.data_recepcao and data_inicio_meta <= membro_indicador.data_recepcao <= data_fim_meta:
            if membro_indicador.status == 'Não-Membro' and membro_indicador.batizado_aclamado:
                metricas_setor['num_batizados_aclamados_atuais_agregado'] += 1
            elif membro_indicador.status != 'Não-Membro':
                metricas_setor['num_batizados_aclamados_atuais_agregado'] += 1

    eventos_encontro_ids = db.session.query(Evento.id).filter(
        Evento.tipo_evento == 'Encontro com Deus',
        Evento.concluido == True,
        Evento.data_evento.between(data_inicio_meta, data_fim_meta)
    ).all()
    
    if eventos_encontro_ids:
        metricas_setor['num_encontro_deus_participantes_atuais_agregado'] = db.session.query(participantes_evento)\
            .filter(participantes_evento.c.evento_id.in_([e_id[0] for e_id in eventos_encontro_ids]),
                    participantes_evento.c.membro_id.in_(membro_ids_do_setor))\
            .count()
    else:
        metricas_setor['num_encontro_deus_participantes_atuais_agregado'] = 0

    metricas_setor['num_multiplicacoes_pg_atuais_agregado'] = pgs_multiplicados_count = PequenoGrupo.query\
        .filter(PequenoGrupo.setor_id == setor_id,
                PequenoGrupo.data_multiplicacao.isnot(None),
                PequenoGrupo.data_multiplicacao.between(data_inicio_meta, data_fim_meta))\
        .count()

    trinta_dias_atras_contrib = datetime.now() - timedelta(days=35)
    
    membros_do_setor = Membro.query.filter(Membro.id.in_(membro_ids_do_setor)).all()
    
    ids_dizimistas_30d_setor = {r[0] for r in db.session.query(Contribuicao.membro_id.distinct())\
        .filter(Contribuicao.membro_id.in_(membro_ids_do_setor),
                Contribuicao.tipo == 'Dízimo',
                Contribuicao.data_lanc >= trinta_dias_atras_contrib)\
        .all()}

    ids_ctm_frequentes_setor = {r[0] for r in db.session.query(Presenca.membro_id.distinct())\
        .join(AulaRealizada)\
        .filter(Presenca.membro_id.in_(membro_ids_do_setor),
                AulaRealizada.data >= trinta_dias_atras)\
        .all()}

    lista_dizimistas = []
    lista_nao_dizimistas = []
    lista_ctm_frequentes = []
    lista_nao_ctm_frequentes = []
    
    for membro in membros_do_setor:
        if membro.id in ids_dizimistas_30d_setor:
            lista_dizimistas.append(membro)
        else:
            lista_nao_dizimistas.append(membro)
            
        if membro.id in ids_ctm_frequentes_setor:
            lista_ctm_frequentes.append(membro)
        else:
            lista_nao_ctm_frequentes.append(membro)

    lista_dizimistas.sort(key=lambda m: m.nome_completo)
    lista_nao_dizimistas.sort(key=lambda m: m.nome_completo)
    lista_ctm_frequentes.sort(key=lambda m: m.nome_completo)
    lista_nao_ctm_frequentes.sort(key=lambda m: m.nome_completo)

    distribuicao_dizimistas_30d = {
        'dizimistas': len(lista_dizimistas),
        'nao_dizimistas': len(lista_nao_dizimistas)
    }
    distribuicao_frequencia_ctm = {
        'frequentes_ctm': len(lista_ctm_frequentes),
        'nao_frequentes_ctm': len(lista_nao_ctm_frequentes)
    }

    return render_template('grupos/setores/detalhes.html',  
                           setor=setor,
                           pgs_ativos=pgs_ativos,
                           pgs_multiplicados=pgs_multiplicados,
                           jornada_eventos=jornada_eventos,
                           metricas_setor=metricas_setor,
                           num_participantes_totais=num_participantes_totais,
                           lista_dizimistas=lista_dizimistas,
                           lista_ctm_frequentes=lista_ctm_frequentes,
                           lista_nao_dizimistas=lista_nao_dizimistas,
                           lista_nao_ctm_frequentes=lista_nao_ctm_frequentes,
                           distribuicao_dizimistas_30d=distribuicao_dizimistas_30d,
                           distribuicao_frequencia_ctm=distribuicao_frequencia_ctm,
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
    pg = PequenoGrupo.query.options(
        joinedload(PequenoGrupo.setor).joinedload(Setor.area),
        joinedload(PequenoGrupo.facilitador),
        joinedload(PequenoGrupo.anfitriao)
    ).get_or_404(pg_id)

    if not pg.ativo:
        jornada_eventos = pg.jornada_eventos_pg.order_by(JornadaEvento.data_evento.desc()).all()
        return render_template('grupos/pgs/detalhes_inativo.html', 
                               pg=pg, 
                               jornada_eventos=jornada_eventos, 
                               ano=ano, 
                               versao=versao)
    
    meta_vigente = pg.setor.area.meta_vigente
    data_inicio_meta = meta_vigente.data_inicio if meta_vigente else date.min
    data_fim_meta = meta_vigente.data_fim if meta_vigente else date.max
    
    membro_ids_pgs_query = db.session.query(Membro.id)\
                               .filter(Membro.pg_id == pg_id, Membro.ativo == True)
    
    membro_ids_pgs = {id[0] for id in membro_ids_pgs_query.all()}
    
    if pg.facilitador_id:
        membro_ids_pgs.add(pg.facilitador_id)
    if pg.anfitriao_id:
        membro_ids_pgs.add(pg.anfitriao_id)
        
    if not membro_ids_pgs:
        membro_ids_pgs = []

    metricas_pg = {}
    
    if meta_vigente:
        metricas_pg['meta_facilitadores_treinamento'] = meta_vigente.meta_facilitadores_treinamento_pg
        metricas_pg['meta_anfitrioes_treinamento'] = meta_vigente.meta_anfitrioes_treinamento_pg
        metricas_pg['meta_ctm_participantes'] = meta_vigente.meta_ctm_participantes_pg
        metricas_pg['meta_encontro_deus_participantes'] = meta_vigente.meta_encontro_deus_participantes_pg
        metricas_pg['meta_batizados_aclamados'] = meta_vigente.meta_batizados_aclamados_pg
    else:
        metricas_pg['meta_facilitadores_treinamento'] = 0
        metricas_pg['meta_anfitrioes_treinamento'] = 0
        metricas_pg['meta_ctm_participantes'] = 0
        metricas_pg['meta_encontro_deus_participantes'] = 0
        metricas_pg['meta_batizados_aclamados'] = 0
    
    trinta_dias_atras = date.today() - timedelta(days=35)

    subquery_ctm_presentes = db.session.query(Presenca.membro_id)\
        .join(AulaRealizada)\
        .filter(AulaRealizada.data >= trinta_dias_atras)\
        .distinct()

    query_membros_indicadores = db.session.query(
        Membro.status_treinamento_pg,
        Membro.batizado_aclamado,
        Membro.data_recepcao,
        Membro.status,
        Membro.id.in_(subquery_ctm_presentes).label('presente_ctm_30d')
    ).filter(Membro.id.in_(membro_ids_pgs)).all()
    
    metricas_pg['num_facilitadores_treinamento_atuais'] = 0
    metricas_pg['num_anfitrioes_treinamento_atuais'] = 0
    metricas_pg['num_ctm_participantes_atuais'] = 0
    metricas_pg['num_batizados_aclamados_atuais'] = 0

    for membro_indicador in query_membros_indicadores:
        if membro_indicador.status_treinamento_pg == 'Facilitador em Treinamento':
            metricas_pg['num_facilitadores_treinamento_atuais'] += 1
        if membro_indicador.status_treinamento_pg == 'Anfitrião em Treinamento':
            metricas_pg['num_anfitrioes_treinamento_atuais'] += 1
        if membro_indicador.presente_ctm_30d:
            metricas_pg['num_ctm_participantes_atuais'] += 1
        
        if membro_indicador.data_recepcao and data_inicio_meta <= membro_indicador.data_recepcao <= data_fim_meta:
            if (membro_indicador.status == 'Não-Membro' and membro_indicador.batizado_aclamado) or \
               (membro_indicador.status != 'Não-Membro'):
                metricas_pg['num_batizados_aclamados_atuais'] += 1

    eventos_encontro_ids = db.session.query(Evento.id).filter(
        Evento.tipo_evento == 'Encontro com Deus',
        Evento.concluido == True,
        Evento.data_evento.between(data_inicio_meta, data_fim_meta)
    ).all()
    
    if eventos_encontro_ids:
        metricas_pg['num_encontro_deus_participantes_atuais'] = db.session.query(participantes_evento)\
            .filter(participantes_evento.c.evento_id.in_([e_id[0] for e_id in eventos_encontro_ids]),
                    participantes_evento.c.membro_id.in_(membro_ids_pgs))\
            .count()
    else:
        metricas_pg['num_encontro_deus_participantes_atuais'] = 0

    ctm_dados_alunos = db.session.query(
        Membro,
        TurmaCTM,
        TurmaCTM.classe,
        func.count(Presenca.id).label('total_presencas'),
        ConclusaoCTM.status_conclusao
    )\
    .select_from(Membro)\
    .join(Membro.turmas_ctm)\
    .join(TurmaCTM.classe)\
    .outerjoin(Presenca, and_(
        Presenca.membro_id == Membro.id,
        Presenca.aula_realizada.has(AulaRealizada.turma_id == TurmaCTM.id)
    ))\
    .outerjoin(ConclusaoCTM, and_(
        ConclusaoCTM.membro_id == Membro.id,
        ConclusaoCTM.turma_id == TurmaCTM.id
    ))\
    .filter(Membro.id.in_(membro_ids_pgs))\
    .group_by(Membro.id, TurmaCTM.id, ConclusaoCTM.id)\
    .all()

    aulas_por_turma = dict(db.session.query(
        AulaRealizada.turma_id, 
        func.count(AulaRealizada.id)
    ).group_by(AulaRealizada.turma_id).all())

    ctm_dados_formatados = []
    for membro, turma, classe, total_presencas, status_conclusao in ctm_dados_alunos:
        ctm_dados_formatados.append({
            'membro': membro,
            'turma': turma,
            'classe': classe,
            'total_presencas': total_presencas,
            'total_aulas': aulas_por_turma.get(turma.id, 0),
            'status_conclusao': status_conclusao or 'Em Andamento'
        })
    
    jornada_eventos = pg.jornada_eventos_pg.order_by(JornadaEvento.data_evento.desc()).all()
    membros_disponiveis = Membro.query.filter(
        Membro.id.notin_(membro_ids_pgs), 
        Membro.pg_id == None,
        Membro.ativo == True
    ).order_by(Membro.nome_completo).all()

    return render_template('grupos/pgs/detalhes.html',
                           pg=pg,
                           metricas_pg=metricas_pg,
                           ctm_dados_alunos=ctm_dados_formatados,
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
