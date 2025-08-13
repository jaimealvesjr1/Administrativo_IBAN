from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.grupos.models import Area, Setor, PequenoGrupo
from app.grupos.forms import AreaForm, SetorForm, PequenoGrupoForm, PequenoGrupoMetasForm, SetorMetasForm
from app.membresia.models import Membro
from app.auth.models import User
from app.jornada.models import registrar_evento_jornada, JornadaEvento
from config import Config
from app.decorators import admin_required, group_permission_required, leader_required

grupos_bp = Blueprint('grupos', __name__, template_folder='templates')

@grupos_bp.route('/')
@grupos_bp.route('/index')
@grupos_bp.route('/listar')
@login_required
@leader_required
def listar_grupos_unificada():
    if current_user.has_permission('admin'):
        areas = Area.query.order_by(Area.nome).all()
        setores = Setor.query.order_by(Setor.nome).all()
        pgs = PequenoGrupo.query.order_by(PequenoGrupo.nome).all()
    elif current_user.membro:
        areas_coordenadas = current_user.membro.areas_coordenadas.all()
        setores_supervisionados = current_user.membro.setores_supervisionados.all()
        pgs_liderados = PequenoGrupo.query.filter(
            (PequenoGrupo.facilitador_id == current_user.membro.id) |
            (PequenoGrupo.anfitriao_id == current_user.membro.id)
        ).all()

        areas = list(areas_coordenadas)
        setores = list(setores_supervisionados)
        pgs = list(pgs_liderados)

        # Lógica para adicionar a hierarquia abaixo do coordenador
        for area in areas_coordenadas:
            for setor in area.setores:
                if setor not in setores:
                    setores.append(setor)
                for pg in setor.pequenos_grupos:
                    if pg not in pgs:
                        pgs.append(pg)

        # Lógica para adicionar a hierarquia abaixo do supervisor
        for setor in setores_supervisionados:
            for pg in setor.pequenos_grupos:
                if pg not in pgs:
                    pgs.append(pg)

        areas = sorted(areas, key=lambda a: a.nome)
        setores = sorted(setores, key=lambda s: s.nome)
        pgs = sorted(pgs, key=lambda p: p.nome)

    else:
        flash('Você não tem permissão para visualizar grupos.', 'danger')
        return redirect(url_for('main.index'))

    tipo_selecionado = request.args.get('tipo', 'pgs')
    return render_template('grupos/listagem_unificada.html', 
                            areas=areas, 
                            setores=setores, 
                            pgs=pgs, 
                            tipo_selecionado=tipo_selecionado, config=Config)

@grupos_bp.route('/areas')
@login_required
def listar_areas():
    return redirect(url_for('grupos.listar_grupos_unificada', tipo='areas'))

@grupos_bp.route('/areas/criar', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_area():
    form = AreaForm()
    if form.validate_on_submit():
        nova_area = Area(
            nome=form.nome.data,
            coordenador_id=form.coordenador.data,
            meta_facilitadores_treinamento=form.meta_facilitadores_treinamento.data,
            meta_anfitrioes_treinamento=form.meta_anfitrioes_treinamento.data,
            meta_ctm_participantes=form.meta_ctm_participantes.data,
            meta_encontro_deus_participantes=form.meta_encontro_deus_participantes.data,
            meta_batizados_aclamados=form.meta_batizados_aclamados.data,
            meta_multiplicacoes_pg=form.meta_multiplicacoes_pg.data
        )
        db.session.add(nova_area)
        try:
            db.session.commit()
            flash('Área criada com sucesso!', 'success')
            registrar_evento_jornada(
                tipo_acao='AREA_CRIADA',
                descricao_detalhada=f'Se tornou coordenador(a) da área "{nova_area.nome}".',
                usuario_executor=current_user,
                membros=[nova_area.coordenador]
            )
            return redirect(url_for('grupos.detalhes_area', area_id=nova_area.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar Área: {e}', 'danger')
    return render_template('grupos/areas/form.html', form=form)

@grupos_bp.route('/areas/<int:area_id>')
@login_required
@group_permission_required(Area, 'view')
def detalhes_area(area_id):
    area = Area.query.get_or_404(area_id)    
    jornada_eventos = area.jornada_eventos_area.order_by(JornadaEvento.data_evento.desc()).all()
    return render_template('grupos/areas/detalhes.html', area=area, jornada_eventos=jornada_eventos, config=Config)

@grupos_bp.route('/areas/editar/<int:area_id>', methods=['GET', 'POST'])
@login_required
@group_permission_required(Area, 'edit')
def editar_area(area_id):
    area = Area.query.get_or_404(area_id)    
    form = AreaForm(obj=area)
    form.area = area
    coordenador_antigo = area.coordenador
    if form.validate_on_submit():
        area.nome = form.nome.data
        area.coordenador_id = form.coordenador.data
        area.meta_facilitadores_treinamento = form.meta_facilitadores_treinamento.data
        area.meta_anfitrioes_treinamento = form.meta_anfitrioes_treinamento.data
        area.meta_ctm_participantes = form.meta_ctm_participantes.data
        area.meta_encontro_deus_participantes = form.meta_encontro_deus_participantes.data
        area.meta_batizados_aclamados = form.meta_batizados_aclamados.data
        area.meta_multiplicacoes_pg = form.meta_multiplicacoes_pg.data
        try:
            db.session.commit()
            flash('Área atualizada com sucesso!', 'success')
            if coordenador_antigo and coordenador_antigo.id != area.coordenador_id: 
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Deixou de ser coordenador(a) da área "{area.nome}".', usuario_executor=current_user, membros=[coordenador_antigo])
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Se tornou coordenador(a) da área "{area.nome}".', usuario_executor=current_user, membros=[area.coordenador])
            return redirect(url_for('grupos.detalhes_area', area_id=area.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar Área: {e}', 'danger')
    elif request.method == 'GET':
        form.coordenador.data = area.coordenador_id
    return render_template('grupos/areas/form.html', form=form, area=area)

@grupos_bp.route('/areas/deletar/<int:area_id>', methods=['POST'])
@login_required
@admin_required
def deletar_area(area_id):
    area = Area.query.get_or_404(area_id)
    if area.setores.count() > 0:
        flash(f'Não é possível deletar a Área "{area.nome}" pois ela possui Setores vinculados.', 'danger')
        return redirect(url_for('grupos.listar_areas'))
    nome_area = area.nome
    coordenador_obj = area.coordenador
    try:
        db.session.delete(area)
        db.session.commit()
        flash('Área deletada com sucesso!', 'success')
        if coordenador_obj:
            registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Deixou de ser coordenador(a) da área "{nome_area}", pois a entidade foi deletada.', usuario_executor=current_user, membros=[coordenador_obj])
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
    if form.validate_on_submit():
        novo_setor = Setor(
            nome=form.nome.data,
            supervisor_id=form.supervisor.data,
            area_id=form.area.data,
            )
        db.session.add(novo_setor)
        try:
            db.session.commit()
            flash('Setor criado com sucesso!', 'success')
            registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Se tornou supervisor(a) do setor "{novo_setor.nome}".', usuario_executor=current_user, membros=[novo_setor.supervisor])
            return redirect(url_for('grupos.detalhes_setor', setor_id=novo_setor.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar Setor: {e}', 'danger')
    return render_template('grupos/setores/form.html', form=form)

@grupos_bp.route('/setores/<int:setor_id>')
@login_required
@group_permission_required(Setor, 'view')
def detalhes_setor(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    jornada_eventos = setor.jornada_eventos_setor.order_by(JornadaEvento.data_evento.desc()).all()
    return render_template('grupos/setores/detalhes.html', setor=setor, jornada_eventos=jornada_eventos, config=Config)

@grupos_bp.route('/setores/editar/<int:setor_id>', methods=['GET', 'POST'])
@login_required
@group_permission_required(Setor, 'edit')
def editar_setor(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    form = SetorForm(obj=setor)
    form.setor = setor
    supervisor_antigo = setor.supervisor
    area_antiga = setor.area
    if form.validate_on_submit():
        setor.nome = form.nome.data
        setor.supervisor_id = form.supervisor.data
        setor.area_id = form.area.data
        setor.meta_facilitadores_treinamento = form.meta_facilitadores_treinamento.data
        setor.meta_anfitrioes_treinamento = form.meta_anfitrioes_treinamento.data
        setor.meta_ctm_participantes = form.meta_ctm_participantes.data
        setor.meta_encontro_deus_participantes = form.meta_encontro_deus_participantes.data
        setor.meta_batizados_aclamados = form.meta_batizados_aclamados.data
        setor.meta_multiplicacoes_pg = form.meta_multiplicacoes_pg.data
        try:
            db.session.commit()
            flash('Setor atualizado com sucesso!', 'success')
            if supervisor_antigo and supervisor_antigo.id != setor.supervisor_id:
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Deixou de ser supervisor(a) do setor "{setor.nome}".', usuario_executor=current_user, membros=[supervisor_antigo])
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Se tornou supervisor(a) do setor "{setor.nome}".', usuario_executor=current_user, membros=[setor.supervisor])
            return redirect(url_for('grupos.detalhes_setor', setor_id=setor.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar Setor: {e}', 'danger')
    elif request.method == 'GET':
        form.supervisor.data = setor.supervisor_id
        form.area.data = setor.area_id
    return render_template('grupos/setores/form.html', form=form, setor=setor)

@grupos_bp.route('/setores/deletar/<int:setor_id>', methods=['POST'])
@login_required
@admin_required
def deletar_setor(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    if setor.pequenos_grupos.count() > 0:
        flash(f'Não é possível deletar o Setor "{setor.nome}" pois ele possui Pequenos Grupos vinculados.', 'danger')
        return redirect(url_for('grupos.listar_setores'))
    nome_setor = setor.nome
    supervisor_obj = setor.supervisor
    try:
        db.session.delete(setor)
        db.session.commit()
        flash('Setor deletado com sucesso!', 'success')
        if supervisor_obj:
            registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Deixou de ser supervisor(a) do setor "{nome_setor}", pois a entidade foi deletada.', usuario_executor=current_user, membros=[supervisor_obj])
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar Setor: {e}', 'danger')
    return redirect(url_for('grupos.listar_setores'))

@grupos_bp.route('/pgs')
@login_required
def listar_pgs():
    return redirect(url_for('grupos.listar_grupos_unificada', tipo='pgs'))

@grupos_bp.route('/pgs/criar', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_pg():
    form = PequenoGrupoForm()
    if form.validate_on_submit():
        novo_pg = PequenoGrupo(nome=form.nome.data, facilitador_id=form.facilitador.data, anfitriao_id=form.anfitriao.data, setor_id=form.setor.data, dia_reuniao=form.dia_reuniao.data, horario_reuniao=form.horario_reuniao.data)
        db.session.add(novo_pg)
        try:
            db.session.commit()
            flash('Pequeno Grupo criado com sucesso!', 'success')
            registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Se tornou facilitador(a) do PG "{novo_pg.nome}".', usuario_executor=current_user, membros=[novo_pg.facilitador])
            registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Se tornou anfitrião(a) do PG "{novo_pg.nome}".', usuario_executor=current_user, membros=[novo_pg.anfitriao])
            return redirect(url_for('grupos.detalhes_pg', pg_id=novo_pg.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar Pequeno Grupo: {e}', 'danger')
    return render_template('grupos/pgs/form.html', form=form)

@grupos_bp.route('/pgs/<int:pg_id>')
@login_required
@group_permission_required(PequenoGrupo, 'view')
def detalhes_pg(pg_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)
    membros_disponiveis = Membro.query.filter(Membro.id != pg.facilitador_id, Membro.id != pg.anfitriao_id, Membro.pg_id == None).order_by(Membro.nome_completo).all()
    jornada_eventos = pg.jornada_eventos_pg.order_by(JornadaEvento.data_evento.desc()).all()
    return render_template('grupos/pgs/detalhes.html', pg=pg, membros_disponiveis=membros_disponiveis, jornada_eventos=jornada_eventos, config=Config)

@grupos_bp.route('/pgs/editar/<int:pg_id>', methods=['GET', 'POST'])
@login_required
@group_permission_required(PequenoGrupo, 'edit')
def editar_pg(pg_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)
    form = PequenoGrupoForm(obj=pg)
    form.pg = pg
    facilitador_antigo = pg.facilitador
    anfitriao_antigo = pg.anfitriao
    setor_antigo = pg.setor
    if form.validate_on_submit():
        pg.nome = form.nome.data
        pg.facilitador_id = form.facilitador.data
        pg.anfitriao_id = form.anfitriao.data
        pg.setor_id = form.setor.data
        pg.dia_reuniao = form.dia_reuniao.data
        pg.horario_reuniao = form.horario_reuniao.data
        try:
            db.session.commit()
            flash('Pequeno Grupo atualizado com sucesso!', 'success')
            if facilitador_antigo and facilitador_antigo.id != pg.facilitador_id:
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Deixou de ser facilitador(a) do PG "{pg.nome}".', usuario_executor=current_user, membros=[facilitador_antigo])
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Se tornou facilitador(a) do PG "{pg.nome}".', usuario_executor=current_user, membros=[pg.facilitador])
            if anfitriao_antigo and anfitriao_antigo.id != pg.anfitriao_id:
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Deixou de ser anfitrião(a) do PG "{pg.nome}".', usuario_executor=current_user, membros=[anfitriao_antigo])
                registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Se tornou anfitrião(a) do PG "{pg.nome}".', usuario_executor=current_user, membros=[pg.anfitriao])
            return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar Pequeno Grupo: {e}', 'danger')
    elif request.method == 'GET':
        form.facilitador.data = pg.facilitador_id
        form.anfitriao.data = pg.anfitriao_id
        form.setor.data = pg.setor_id
        form.dia_reuniao.data = pg.dia_reuniao
        form.horario_reuniao.data = pg.horario_reuniao
    return render_template('grupos/pgs/form.html', form=form, pg=pg)

@grupos_bp.route('/pgs/deletar/<int:pg_id>', methods=['POST'])
@login_required
@admin_required
def deletar_pg(pg_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)
    nome_pg = pg.nome
    facilitador_obj = pg.facilitador
    anfitriao_obj = pg.anfitriao
    membros_no_pg_antes_deletar = list(pg.participantes)
    for membro in pg.participantes:
        membro.pg_id = None
        membro.status_treinamento_pg = 'Nenhum'
        membro.participou_ctm = False
        membro.participou_encontro_deus = False
        membro.batizado_aclamado = False
        db.session.add(membro)
    try:
        db.session.delete(pg)
        db.session.commit()
        flash('Pequeno Grupo deletado com sucesso!', 'success')
        if facilitador_obj:
            registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Deixou de ser facilitador(a) do PG "{nome_pg}", pois a entidade foi deletada.', usuario_executor=current_user, membros=[facilitador_obj])
        if anfitriao_obj:
            registrar_evento_jornada(tipo_acao='LIDERANCA_ALTERADA', descricao_detalhada=f'Deixou de ser anfitrião(a) do PG "{nome_pg}", pois a entidade foi deletada.', usuario_executor=current_user, membros=[anfitriao_obj])
        for membro in membros_no_pg_antes_deletar:
            registrar_evento_jornada(tipo_acao='PARTICIPANTE_REMOVIDO_PG', descricao_detalhada=f'Deixou de ser participante do PG "{nome_pg}", pois o PG foi deletado.', usuario_executor=current_user, membros=[membro])
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar Pequeno Grupo: {e}', 'danger')
    return redirect(url_for('grupos.listar_pgs'))

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
            flash(f'{membro.nome_completo} adicionado(a) ao {pg.nome} como participante!', 'success')
            registrar_evento_jornada(tipo_acao='PARTICIPANTE_ADICIONADO_PG', descricao_detalhada=f'Se tornou participante do PG "{pg_nome}".', usuario_executor=current_user, membros=[membro])
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar participante: {e}', 'danger')
    else:
        flash('Membro não pertence a este Pequeno Grupo.', 'danger')
    return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))

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
            registrar_evento_jornada(tipo_acao='PARTICIPANTE_REMOVIDO_PG', descricao_detalhada=f'Deixou de ser participante do PG "{pg_nome}".', usuario_executor=current_user, membros=[membro])
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao remover participante: {e}', 'danger')
    else:
        flash('Membro não pertence a este Pequeno Grupo.', 'danger')
    return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))

@grupos_bp.route('/pgs/<int:pg_id>/atualizar/<int:membro_id>', methods=['POST'])
@login_required
@group_permission_required(PequenoGrupo, 'manage_participants')
def atualizar_indicadores(pg_id, membro_id):
    pg = PequenoGrupo.query.get_or_404(pg_id)
    membro = Membro.query.get_or_404(membro_id)
    if membro.pg_id != pg.id:
        flash('Membro não pertence a este Pequeno Grupo.', 'danger')
        return redirect(url_for('grupos.detalhes_pg', pg_id=pg.id))
    status_treinamento_antigo = membro.status_treinamento_pg
    participou_ctm_antigo = membro.participou_ctm
    participou_encontro_deus_antigo = membro.participou_encontro_deus
    batizado_aclamado_antigo = membro.batizado_aclamado
    status_treinamento = request.form.get(f'status_treinamento_pg_{membro.id}')
    if status_treinamento in ['Facilitador em Treinamento', 'Anfitrião em Treinamento', 'Participante']:
        membro.status_treinamento_pg = status_treinamento
    membro.participou_ctm = 'participou_ctm' in request.form
    membro.participou_encontro_deus = 'participou_encontro_deus' in request.form
    membro.batizado_aclamado = 'batizado_aclamado' in request.form
    try:
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

@grupos_bp.route('/setores/<int:setor_id>/gerenciar_metas_pgs', methods=['GET', 'POST'])
@login_required
@group_permission_required(Setor, 'edit')
def gerenciar_metas_pgs_do_setor(setor_id):
    if not (current_user.has_permission('admin') or (current_user.membro and Setor.query.filter_by(supervisor_id=current_user.membro.id, id=setor_id).first())):
        flash('Você não tem permissão para gerenciar metas deste Setor.', 'danger')
        return redirect(url_for('grupos.detalhes_setor', setor_id=setor_id))
    setor = Setor.query.get_or_404(setor_id)
    pgs = setor.pequenos_grupos.all()
    forms = {pg.id: PequenoGrupoMetasForm(prefix=str(pg.id), obj=pg) for pg in pgs}
    if request.method == 'POST':
        todos_validos = True
        for pg_id, form in forms.items():
            if not form.validate():
                todos_validos = False
                break
        if todos_validos:
            try:
                for pg_id, form in forms.items():
                    pg = PequenoGrupo.query.get(pg_id)
                    pg.meta_facilitadores_treinamento = form.meta_facilitadores_treinamento.data
                    pg.meta_anfitrioes_treinamento = form.meta_anfitrioes_treinamento.data
                    pg.meta_ctm_participantes = form.meta_ctm_participantes.data
                    pg.meta_encontro_deus_participantes = form.meta_encontro_deus_participantes.data
                    pg.meta_batizados_aclamados = form.meta_batizados_aclamados.data
                    pg.meta_multiplicacoes_pg = form.meta_multiplicacoes_pg.data
                    db.session.add(pg)
                db.session.commit()
                flash('Metas dos Pequenos Grupos atualizadas com sucesso!', 'success')
                return redirect(url_for('grupos.detalhes_setor', setor_id=setor.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao atualizar metas: {e}', 'danger')
    return render_template('grupos/setores/gerenciar_metas_pgs.html', setor=setor, pgs=pgs, forms=forms, config=Config)

@grupos_bp.route('/areas/<int:area_id>/gerenciar_metas_setores', methods=['GET', 'POST'])
@login_required
@group_permission_required(Area, 'edit')
def gerenciar_metas_setores_da_area(area_id):
    area = Area.query.get_or_404(area_id)
    setores = area.setores.all()
    forms = {setor.id: SetorMetasForm(prefix=str(setor.id), obj=setor) for setor in setores}
    if request.method == 'POST':
        todos_validos = True
        for setor_id, form in forms.items():
            if not form.validate():
                todos_validos = False
                break
        if todos_validos:
            try:
                for setor_id, form in forms.items():
                    setor = Setor.query.get(setor_id)
                    setor.meta_facilitadores_treinamento = form.meta_facilitadores_treinamento.data
                    setor.meta_anfitrioes_treinamento = form.meta_anfitrioes_treinamento.data
                    setor.meta_ctm_participantes = form.meta_ctm_participantes.data
                    setor.meta_encontro_deus_participantes = form.meta_encontro_deus_participantes.data
                    setor.meta_batizados_aclamados = form.meta_batizados_aclamados.data
                    setor.meta_multiplicacoes_pg = form.meta_multiplicacoes_pg.data
                    db.session.add(setor)
                db.session.commit()
                flash('Metas dos Setores atualizadas com sucesso!', 'success')
                return redirect(url_for('grupos.detalhes_area', area_id=area.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao atualizar metas: {e}', 'danger')
    return render_template('grupos/areas/gerenciar_metas_setores.html', area=area, setores=setores, forms=forms, config=Config)