from . import eventos_bp
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.decorators import admin_required
from .models import Evento, InscricaoEvento
from .forms import EventoForm, ConclusaoRecepcaoForm, InscricaoMembrosForm
from app.membresia.models import Membro
from app.grupos.models import Area, Setor, PequenoGrupo
from app.jornada.models import registrar_evento_jornada
from datetime import date

@eventos_bp.route('/')
@eventos_bp.route('/listar')
@login_required
@admin_required
def listar_eventos():
    eventos_ativos = Evento.query.filter_by(concluido=False).order_by(Evento.data_evento.desc()).all()
    eventos_concluidos = Evento.query.filter_by(concluido=True).order_by(Evento.data_evento.desc()).all()
    
    return render_template('eventos/listagem_eventos.html', 
                           eventos_ativos=eventos_ativos, 
                           eventos_concluidos=eventos_concluidos)

@eventos_bp.route('/criar', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_evento():
    form = EventoForm()
    if form.validate_on_submit():
        novo_evento = Evento(
            nome=form.nome.data,
            tipo_evento=form.tipo_evento.data,
            data_evento=form.data_evento.data,
            observacoes=form.observacoes.data
        )
        db.session.add(novo_evento)
        try:
            db.session.commit()
            flash('Evento criado com sucesso!', 'success')
            return redirect(url_for('eventos.gerenciar_evento', evento_id=novo_evento.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar o evento: {e}', 'danger')
            
    return render_template('eventos/form_evento.html', form=form)

@eventos_bp.route('/<int:evento_id>/gerenciar', methods=['GET', 'POST'])
@login_required
@admin_required
def gerenciar_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    form_inscricao_membros = InscricaoMembrosForm()
    
    if form_inscricao_membros.validate_on_submit():
        membros_selecionados = form_inscricao_membros.membros.data
        for membro_id in membros_selecionados:
            membro = Membro.query.get(membro_id)
            if membro and membro not in evento.participantes:
                evento.participantes.append(membro)
        
        try:
            db.session.commit()
            flash(f'Membros inscritos no evento com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao inscrever membros: {e}', 'danger')
            
        return redirect(url_for('eventos.gerenciar_evento', evento_id=evento.id))
    
    membros_inscritos = evento.participantes.all()
    membros_disponiveis = Membro.query.filter(Membro.ativo==True, ~Membro.eventos_inscritos.any(Evento.id == evento.id)).all()
    
    return render_template('eventos/gerenciar_evento.html', 
                           evento=evento, 
                           membros_inscritos=membros_inscritos, 
                           membros_disponiveis=membros_disponiveis,
                           form_inscricao_membros=form_inscricao_membros)

@eventos_bp.route('/<int:evento_id>/concluir', methods=['GET', 'POST'])
@login_required
@admin_required
def concluir_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    form_conclusao = ConclusaoRecepcaoForm()

    if evento.tipo_evento == 'Recepção' and form_conclusao.validate_on_submit():
        tipo_recepcao = form_conclusao.tipo_recepcao.data
        obs_membresia = form_conclusao.obs_membresia.data
        
        for membro in evento.participantes.all():
            membro.status = 'Membro'
            membro.data_recepcao = evento.data_evento
            membro.tipo_recepcao = tipo_recepcao
            membro.obs_recepcao = obs_membresia
            
            if tipo_recepcao == 'Batismo':
                membro.batizado_aclamado = True
                membro.data_batismo = evento.data_evento
            elif tipo_recepcao == 'Aclamação':
                membro.batizado_aclamado = True
                membro.data_aclamacao = evento.data_evento

            db.session.add(membro)
            registrar_evento_jornada(
                tipo_acao='MEMBRO_RECEBIDO',
                descricao_detalhada=f'Recebido como membro por {tipo_recepcao}.',
                usuario_executor=current_user,
                membros=[membro]
            )
        
        evento.concluido = True
        db.session.add(evento)
        
        try:
            db.session.commit()
            flash('Evento concluído e membros atualizados com sucesso!', 'success')
            return redirect(url_for('eventos.listar_eventos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao concluir evento: {e}', 'danger')
            
    elif evento.tipo_evento == 'Encontro com Deus':
        for membro in evento.participantes.all():
            membro.participou_encontro_deus = True
            db.session.add(membro)
            registrar_evento_jornada(
                tipo_acao='EVENTO_CONCLUIDO',
                descricao_detalhada=f'Participou do Encontro com Deus.',
                usuario_executor=current_user,
                membros=[membro]
            )
        
        evento.concluido = True
        db.session.add(evento)
        
        try:
            db.session.commit()
            flash('Evento concluído e participantes atualizados!', 'success')
            return redirect(url_for('eventos.listar_eventos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao concluir evento: {e}', 'danger')
        
    return render_template('eventos/concluir_evento.html', evento=evento, form_conclusao=form_conclusao)

@eventos_bp.route('/<int:evento_id>/remover-participante/<int:membro_id>', methods=['POST'])
@login_required
@admin_required
def remover_participante(evento_id, membro_id):
    evento = Evento.query.get_or_404(evento_id)
    membro = Membro.query.get_or_404(membro_id)
    
    if evento.concluido:
        flash('Não é possível remover participantes de um evento já concluído.', 'danger')
    elif membro in evento.participantes:
        evento.participantes.remove(membro)
        try:
            db.session.commit()
            flash(f'{membro.nome_completo} removido do evento.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao remover participante: {e}', 'danger')
    else:
        flash('Membro não é um participante deste evento.', 'warning')
        
    return redirect(url_for('eventos.gerenciar_evento', evento_id=evento.id))

@eventos_bp.route('/buscar_membros_ativos')
@login_required
def buscar_membros_ativos():
    """Retorna uma lista de membros ativos para uso com Select2."""
    search_term = request.args.get('q', '')
    
    query = Membro.query.filter(
        Membro.nome_completo.ilike(f'%{search_term}%'),
        Membro.ativo == True
    )
    
    membros = query.order_by(Membro.nome_completo).limit(20).all()
    
    results = [{'id': membro.id, 'text': membro.nome_completo} for membro in membros]
    
    return jsonify(results=results)
