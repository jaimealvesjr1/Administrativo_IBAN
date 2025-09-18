from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import login_required, current_user
from app.decorators import admin_required, group_permission_required
from app.extensions import db
from app.membresia.models import Membro
from app.jornada.models import registrar_evento_jornada
from .models import Presenca, AulaModelo, AulaRealizada, ClasseCTM, TurmaCTM, aluno_turma, ConclusaoCTM
from .forms import PresencaForm, AulaModeloForm, AulaRealizadaForm, ClasseCTMForm, TurmaCTMForm, PresencaManualForm
from datetime import date, datetime
from sqlalchemy import and_, func
from config import Config
import pandas as pd
import io

ctm_bp = Blueprint('ctm', __name__, url_prefix='/ctm')
ano = Config.ANO_ATUAL
versao = Config.VERSAO_APP

@ctm_bp.route('/')
@login_required
@admin_required
def index():
    classes_total = ClasseCTM.query.count()
    turmas_total = TurmaCTM.query.filter_by(ativa=True).count()
    aulas_modelo_total = AulaModelo.query.count()

    turmas_ativas = TurmaCTM.query.filter_by(ativa=True).order_by(TurmaCTM.nome).all()
    campus_por_turma = {}

    for turma in turmas_ativas:
        campus_counts = {}
        for aluno in turma.alunos:
            campus = aluno.campus if aluno.campus else 'Não Informado'
            campus_counts[campus] = campus_counts.get(campus, 0) + 1
        campus_por_turma[turma.nome] = campus_counts

    return render_template(
        'ctm/index.html',
        classes_total=classes_total,
        turmas_total=turmas_total,
        aulas_modelo_total=aulas_modelo_total,
        turmas_ativas=turmas_ativas,
        campus_por_turma=campus_por_turma,
        versao=versao,
        ano=ano
    )

@ctm_bp.route('/listar')
@login_required
@admin_required
def listar_ctm_unificada():
    classes_with_aulas = db.session.query(
        ClasseCTM, 
        func.count(AulaModelo.id).label('num_aulas')
    ).outerjoin(AulaModelo).group_by(ClasseCTM.id).order_by(ClasseCTM.nome).all()

    turmas = TurmaCTM.query.filter_by(ativa=True).order_by(TurmaCTM.nome).all()
    aulas_realizadas = AulaRealizada.query.order_by(AulaRealizada.data.desc()).all()
    
    return render_template(
        'ctm/listagem_unificada.html',
        classes=classes_with_aulas,
        turmas=turmas,
        aulas_realizadas=aulas_realizadas,
        versao=versao,
        ano=ano
    )

@ctm_bp.route('/classes/criar', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_classe():
    form = ClasseCTMForm()
    if form.validate_on_submit():
        nova_classe = ClasseCTM(nome=form.nome.data, supervisor_id=form.supervisor_id.data)
        db.session.add(nova_classe)
        
        try:
            db.session.flush()
            
            for i in range(1, form.num_aulas_ciclo.data + 1):
                nova_aula = AulaModelo(tema=f'Tema da Aula {i}', ordem=i, classe_id=nova_classe.id)
                db.session.add(nova_aula)

            db.session.commit()
            flash('Classe e aulas modelo criadas com sucesso!', 'success')
            return redirect(url_for('ctm.listar_ctm_unificada', tipo='classes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar Classe: {e}', 'danger')
    
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Erro no campo "{form[field].label.text}": {error}', 'danger')
            
    return render_template('ctm/form_classe.html', form=form, versao=versao, ano=ano)

@ctm_bp.route('/classes/editar/<int:classe_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_classe(classe_id):
    classe = ClasseCTM.query.get_or_404(classe_id)
    form = ClasseCTMForm(obj=classe)
    
    if form.validate_on_submit():
        classe.nome = form.nome.data
        classe.supervisor_id = form.supervisor_id.data
        
        num_aulas_novas = form.num_aulas_ciclo.data
        num_aulas_atuais = AulaModelo.query.filter_by(classe_id=classe.id).count()
        
        if num_aulas_novas > num_aulas_atuais:
            for i in range(num_aulas_atuais + 1, num_aulas_novas + 1):
                nova_aula = AulaModelo(tema=f'Tema da Aula {i}', ordem=i, classe_id=classe.id)
                db.session.add(nova_aula)
        elif num_aulas_novas < num_aulas_atuais:
            aulas_a_remover = AulaModelo.query.filter_by(classe_id=classe.id)\
                                                .order_by(AulaModelo.ordem.desc())\
                                                .limit(num_aulas_atuais - num_aulas_novas).all()
            for aula in aulas_a_remover:
                if aula.realizadas:
                    flash(f'Não é possível reduzir o número de aulas. A aula "{aula.tema}" já possui aulas realizadas vinculadas.', 'danger')
                    db.session.rollback()
                    return render_template('ctm/form_classe.html', form=form, classe=classe, versao=versao, ano=ano)
                db.session.delete(aula)
        try:
            db.session.commit()
            flash('Classe atualizada com sucesso!', 'success')
            return redirect(url_for('ctm.listar_ctm_unificada'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar classe: {e}', 'danger')
            
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Erro no campo "{form[field].label.text}": {error}', 'danger')
            
    return render_template('ctm/form_classe.html', form=form, classe=classe, versao=versao, ano=ano)

@ctm_bp.route('/classes/deletar/<int:classe_id>', methods=['POST'])
@login_required
@admin_required
def deletar_classe(classe_id):
    classe = ClasseCTM.query.get_or_404(classe_id)
    if classe.turmas.count() > 0:
        flash(f'Não é possível deletar a Classe "{classe.nome}" pois ela possui Turmas vinculadas.', 'danger')
        return redirect(url_for('ctm.listar_ctm_unificada'))
    
    try:
        db.session.delete(classe)
        db.session.commit()
        flash('Classe deletada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar Classe: {e}', 'danger')
        
    return redirect(url_for('ctm.listar_ctm_unificada'))

@ctm_bp.route('/turmas/criar', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_turma():
    form = TurmaCTMForm()
    if form.validate_on_submit():
        nova_turma = TurmaCTM(nome=form.nome.data, classe_id=form.classe_id.data, facilitador_id=form.facilitador_id.data)
        db.session.add(nova_turma)
        try:
            db.session.commit()
            flash('Turma criada com sucesso!', 'success')
            return redirect(url_for('ctm.listar_ctm_unificada'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar Turma: {e}', 'danger')
            
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Erro no campo "{form[field].label.text}": {error}', 'danger')
    
    return render_template('ctm/form_turma.html', form=form, versao=versao, ano=ano)

@ctm_bp.route('/turmas/editar/<int:turma_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_turma(turma_id):
    turma = TurmaCTM.query.get_or_404(turma_id)
    
    if not turma.ativa:
        flash(f'Não é possível editar a turma "{turma.nome}", pois ela está arquivada.', 'danger')
        return redirect(url_for('ctm.listar_ctm_unificada', tipo='turmas'))
    
    form = TurmaCTMForm(obj=turma)
    
    if form.validate_on_submit():
        turma.nome = form.nome.data
        turma.classe_id = form.classe_id.data
        turma.facilitador_id = form.facilitador_id.data
        
        try:
            db.session.commit()
            flash('Turma atualizada com sucesso!', 'success')
            return redirect(url_for('ctm.listar_ctm_unificada', tipo='turmas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar turma: {e}', 'danger')
            
    if request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Erro no campo "{form[field].label.text}": {error}', 'danger')
            
    return render_template('ctm/form_turma.html', form=form, turma=turma, versao=versao, ano=ano)

@ctm_bp.route('/turmas/deletar/<int:turma_id>', methods=['POST'])
@login_required
@admin_required
def deletar_turma(turma_id):
    turma = TurmaCTM.query.get_or_404(turma_id)
    
    if not turma.ativa:
        flash(f'Não é possível deletar a turma "{turma.nome}", pois ela está arquivada.', 'danger')
        return redirect(url_for('ctm.listar_ctm_unificada', tipo='turmas'))
    
    if len(turma.alunos) > 0 or turma.aulas_realizadas.count() > 0:
        flash(f'Não é possível deletar a Turma "{turma.nome}" pois ela possui Alunos ou Aulas Realizadas vinculados.', 'danger')
        return redirect(url_for('ctm.listar_ctm_unificada', tipo='turmas'))

    try:
        db.session.delete(turma)
        db.session.commit()
        flash('Turma deletada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar Turma: {e}', 'danger')
        
    return redirect(url_for('ctm.listar_ctm_unificada', tipo='turmas'))

@ctm_bp.route('/turmas/arquivar/<int:turma_id>', methods=['GET', 'POST'])
@login_required
@group_permission_required(TurmaCTM, 'edit', 'facilitador')
def arquivar_turma(turma_id):
    turma = TurmaCTM.query.get_or_404(turma_id)

    if request.method == 'POST':
        for aluno in turma.alunos:
            status = request.form.get(f'status_{aluno.id}')
            if status:
                conclusao = ConclusaoCTM.query.filter_by(membro_id=aluno.id, turma_id=turma.id).first()
                if not conclusao:
                    conclusao = ConclusaoCTM(membro_id=aluno.id, turma_id=turma.id, status_conclusao=status)
                    db.session.add(conclusao)
                else:
                    conclusao.status_conclusao = status
                
                if status == 'Aprovado':
                    registrar_evento_jornada(
                        tipo_acao='CONCLUSAO_CTM',
                        descricao_detalhada=f'Concluiu com aprovação a Classe {turma.classe.nome}.',
                        usuario_executor=current_user,
                        membros=[aluno],
                        turmas_ctm=[turma]
                    )
                    aluno.participou_ctm = True
                else:
                    registrar_evento_jornada(
                        tipo_acao='REPROVACAO_CTM',
                        descricao_detalhada=f'Foi reprovado na Classe {turma.classe.nome}.',
                        usuario_executor=current_user,
                        membros=[aluno],
                        turmas_ctm=[turma]
                    )
                    aluno.participou_ctm = False
        
        turma.ativa = False
        db.session.add(turma)

        try:
            db.session.commit()
            flash(f'Turma "{turma.nome}" arquivada e alunos avaliados com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao arquivar turma: {e}', 'danger')
            
        return redirect(url_for('ctm.listar_ctm_unificada'))

    return render_template('ctm/form_arquivar_turma.html', turma=turma, versao=versao, ano=ano)

@ctm_bp.route('/aulas-modelo/criar', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_aula_modelo():
    form = AulaModeloForm()
    if form.validate_on_submit():
        nova_aula = AulaModelo(tema=form.tema.data, ordem=form.ordem.data, classe_id=form.classe_id.data)
        db.session.add(nova_aula)
        try:
            db.session.commit()
            flash('Aula Modelo cadastrada com sucesso!', 'success')
            return redirect(url_for('ctm.listar_ctm_unificada'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar aula modelo: {e}', 'danger')
            
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Erro no campo "{form[field].label.text}": {error}', 'danger')
    
    return render_template('ctm/form_aula_modelo.html', form=form, versao=versao, ano=ano)

@ctm_bp.route('/aulas-realizadas/criar', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_aula_realizada():
    form = AulaRealizadaForm()
    if form.validate_on_submit():
        chave_formatada = form.chave.data.strip().lower().replace(" ", "")
        aula_realizada = AulaRealizada(
            data=form.data.data, 
            turma_id=form.turma_id.data, 
            chave=chave_formatada,
            aula_modelo_id=form.aula_modelo_id.data
        )
        db.session.add(aula_realizada)
        try:
            db.session.commit()
            flash('Aula realizada criada com sucesso!', 'success')
            return redirect(url_for('ctm.listar_ctm_unificada'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar aula realizada: {e}', 'danger')
    
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Erro no campo "{form[field].label.text}": {error}', 'danger')
    
    return render_template('ctm/form_aula_realizada.html', form=form, versao=versao, ano=ano)

@ctm_bp.route('/aulas-modelo/editar/<int:aula_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_aula_modelo(aula_id):
    aula = AulaModelo.query.get_or_404(aula_id)
    form = AulaModeloForm(obj=aula)

    if form.validate_on_submit():
        aula.tema = form.tema.data
        aula.ordem = form.ordem.data
        aula.classe_id = form.classe_id.data
        
        try:
            db.session.commit()
            flash('Aula Modelo atualizada com sucesso!', 'success')
            return redirect(url_for('ctm.listar_ctm_unificada'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar aula modelo: {e}', 'danger')
            
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Erro no campo "{form[field].label.text}": {error}', 'danger')
    
    return render_template('ctm/form_aula_modelo.html', form=form, aula=aula, versao=versao, ano=ano)

@ctm_bp.route('/aulas-realizadas/editar/<int:aula_realizada_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_aula_realizada(aula_realizada_id):
    aula_realizada = AulaRealizada.query.get_or_404(aula_realizada_id)
    form = AulaRealizadaForm(obj=aula_realizada)

    if form.validate_on_submit():
        aula_realizada.data = form.data.data
        aula_realizada.turma_id = form.turma_id.data
        aula_realizada.aula_modelo_id = form.aula_modelo_id.data
        aula_realizada.chave = form.chave.data.strip().lower().replace(" ", "")
        
        try:
            db.session.commit()
            flash('Aula Realizada atualizada com sucesso!', 'success')
            return redirect(url_for('ctm.listar_ctm_unificada'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar aula realizada: {e}', 'danger')
            
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Erro no campo "{form[field].label.text}": {error}', 'danger')
            
    return render_template('ctm/form_aula_realizada.html', form=form, aula_realizada=aula_realizada, versao=versao, ano=ano)

@ctm_bp.route('/aulas-modelo/deletar/<int:aula_id>', methods=['POST'])
@login_required
@admin_required
def deletar_aula_modelo(aula_id):
    aula = AulaModelo.query.get_or_404(aula_id)
    if aula.realizadas:
        flash(f'Não é possível deletar a Aula Modelo "{aula.tema}" pois ela possui Aulas Realizadas vinculadas.', 'danger')
        return redirect(url_for('ctm.listar_ctm_unificada'))
        
    try:
        db.session.delete(aula)
        db.session.commit()
        flash('Aula Modelo deletada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar Aula Modelo: {e}', 'danger')
        
    return redirect(url_for('ctm.listar_ctm_unificada'))

@ctm_bp.route('/aulas-realizadas/deletar/<int:aula_realizada_id>', methods=['POST'])
@login_required
@admin_required
def deletar_aula_realizada(aula_realizada_id):
    aula = AulaRealizada.query.get_or_404(aula_realizada_id)
    
    try:
        db.session.delete(aula)
        db.session.commit()
        flash('Aula Realizada deletada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar Aula Realizada: {e}', 'danger')
        
    return redirect(url_for('ctm.listar_ctm_unificada'))

@ctm_bp.route('/classes/<int:classe_id>/painel')
@login_required
@group_permission_required(ClasseCTM, 'view', 'supervisor')
def painel_supervisor_classe(classe_id):
    classe = ClasseCTM.query.get_or_404(classe_id)
    
    dados_turmas = {}
    for turma in classe.turmas:
        aulas_realizadas = AulaRealizada.query.filter_by(turma_id=turma.id).order_by(AulaRealizada.data).all()
        alunos = turma.alunos
        
        dados_turmas[turma.id] = {
            'nome': turma.nome,
            'facilitador': turma.facilitador.nome_completo if turma.facilitador else 'N/A',
            'alunos': [],
            'aulas': aulas_realizadas,
        }
        
        for aluno in alunos:
            presencas_aluno = {p.aula_realizada_id for p in aluno.presencas if p.aula_realizada.turma_id == turma.id}
            dados_turmas[turma.id]['alunos'].append({
                'id': aluno.id,
                'nome': aluno.nome_completo,
                'presencas': presencas_aluno,
            })

    return render_template(
        'ctm/painel_supervisor.html',
        classe=classe,
        dados_turmas=dados_turmas,
        versao=versao,
        ano=ano
    )

@ctm_bp.route('/turmas/<int:turma_id>/painel')
@login_required
@group_permission_required(TurmaCTM, 'view', 'facilitador')
def painel_facilitador_turma(turma_id):
    turma = TurmaCTM.query.get_or_404(turma_id)
    aulas_realizadas = AulaRealizada.query.filter_by(turma_id=turma.id).order_by(AulaRealizada.data).all()
    
    dados_alunos = []
    for aluno in turma.alunos:
        presencas_aluno = {p.aula_realizada_id for p in aluno.presencas if p.aula_realizada.turma_id == turma.id}
        dados_alunos.append({
            'id': aluno.id,
            'nome': aluno.nome_completo,
            'presencas': presencas_aluno,
        })
    
    membros_fora_da_turma = Membro.query.filter(
        Membro.ativo == True,
        ~Membro.turmas_ctm.any(TurmaCTM.id == turma.id)
    ).order_by(Membro.nome_completo).all()

    aulas_modelo = AulaModelo.query.filter_by(classe_id=turma.classe_id).order_by(AulaModelo.ordem).all()

    form_aula_realizada = AulaRealizadaForm(turma_id=turma.id)

    return render_template(
        'ctm/painel_facilitador.html',
        turma=turma,
        aulas_realizadas=aulas_realizadas,
        dados_alunos=dados_alunos,
        membros_fora_da_turma=membros_fora_da_turma,
        aulas_modelo=aulas_modelo,
        form=form_aula_realizada,
        versao=versao,
        ano=ano
    )

@ctm_bp.route('/turmas/<int:turma_id>/adicionar-aluno', methods=['POST'])
@login_required
@group_permission_required(TurmaCTM, 'edit', 'facilitador')
def adicionar_aluno(turma_id):
    turma = TurmaCTM.query.get_or_404(turma_id)
    
    if not turma.ativa:
        flash(f'Não é possível adicionar alunos à turma "{turma.nome}", pois ela está arquivada.', 'danger')
        return redirect(url_for('ctm.painel_facilitador_turma', turma_id=turma.id))
    
    membro_id = request.form.get('membro_id')
    membro = Membro.query.get_or_404(membro_id)
    
    if membro in turma.alunos:
        flash(f'{membro.nome_completo} já é aluno(a) desta turma.', 'warning')
    else:
        turma.alunos.append(membro)
        try:
            db.session.commit()
            flash(f'{membro.nome_completo} foi adicionado(a) à turma "{turma.nome}".', 'success')
            registrar_evento_jornada(
                tipo_acao='PARTICIPANTE_ADICIONADO_CTM',
                descricao_detalhada=f'Adicionado(a) à turma {turma.nome} como aluno(a).',
                usuario_executor=current_user,
                membros=[membro],
                turmas_ctm=[turma]
            )
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar aluno: {e}', 'danger')
            
    return redirect(url_for('ctm.painel_facilitador_turma', turma_id=turma.id))


@ctm_bp.route('/turmas/<int:turma_id>/remover-aluno/<int:membro_id>', methods=['POST'])
@login_required
@group_permission_required(TurmaCTM, 'edit', 'facilitador')
def remover_aluno(turma_id, membro_id):
    turma = TurmaCTM.query.get_or_404(turma_id)
    
    if not turma.ativa:
        flash(f'Não é possível remover alunos da turma "{turma.nome}", pois ela está arquivada.', 'danger')
        return redirect(url_for('ctm.painel_facilitador_turma', turma_id=turma.id))
        
    membro = Membro.query.get_or_404(membro_id)
    
    if membro not in turma.alunos:
        flash(f'{membro.nome_completo} não é aluno(a) desta turma.', 'warning')
    else:
        turma.alunos.remove(membro)
        try:
            db.session.commit()
            flash(f'{membro.nome_completo} foi removido(a) da turma "{turma.nome}".', 'success')
            registrar_evento_jornada(
                tipo_acao='PARTICIPANTE_REMOVIDO_CTM',
                descricao_detalhada=f'Removido(a) da turma {turma.nome}.',
                usuario_executor=current_user,
                membros=[membro],
                turmas_ctm=[turma]
            )
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao remover aluno: {e}', 'danger')
            
    return redirect(url_for('ctm.painel_facilitador_turma', turma_id=turma.id))

@ctm_bp.route('/buscar_membros')
def buscar_membros():
    search_term = request.args.get('term', '')
    query = Membro.query.filter(
        Membro.nome_completo.ilike(f'%{search_term}%'),
        Membro.ativo == True
    )
    membros = query.order_by(Membro.nome_completo).limit(20).all()
    
    results = []
    for membro in membros:
        results.append({
            'id': membro.id,
            'text': membro.nome_completo
        })
    
    return jsonify(items=results)

@ctm_bp.route('/turmas/<int:turma_id>/lancar-presenca', methods=['POST'])
@login_required
@group_permission_required(TurmaCTM, 'edit', 'facilitador')
def lancar_presenca_manual(turma_id):
    turma = TurmaCTM.query.get_or_404(turma_id)
    
    if not turma.ativa:
        flash(f'Não é possível lançar presença para a turma "{turma.nome}", pois ela está arquivada.', 'danger')
        return redirect(url_for('ctm.painel_facilitador_turma', turma_id=turma.id))

    membro_id = request.form.get('membro_id')
    aula_id = request.form.get('aula_id')

    membro = Membro.query.get_or_404(membro_id)
    aula = AulaRealizada.query.get_or_404(aula_id)
    
    presenca_existente = Presenca.query.filter_by(membro_id=membro.id, aula_realizada_id=aula.id).first()
    
    if presenca_existente:
        db.session.delete(presenca_existente)
        flash(f'Presença de {membro.nome_completo} para a aula de {aula.aula_modelo.tema} desmarcada.', 'info')
        registrar_evento_jornada(
            tipo_acao='PRESENCA_CTM_REMOVIDA',
            descricao_detalhada=f'Presença desmarcada na aula {aula.aula_modelo.tema} da Turma {turma.nome}.',
            usuario_executor=current_user,
            membros=[membro],
            turmas_ctm=[turma])
    else:
        nova_presenca = Presenca(membro_id=membro.id, aula_realizada_id=aula.id)
        db.session.add(nova_presenca)
        flash(f'Presença de {membro.nome_completo} para a aula de {aula.aula_modelo.tema} marcada.', 'success')
        registrar_evento_jornada(
            tipo_acao='PRESENCA_CTM',
            descricao_detalhada=f'Presença registrada na aula {aula.aula_modelo.tema} da Turma {turma.nome}.',
            usuario_executor=current_user,
            membros=[membro],
            turmas_ctm=[turma])

    try:
        db.session.commit()
        presencas_na_turma = Presenca.query.join(AulaRealizada).filter(
            and_(
                Presenca.membro_id == membro.id,
                AulaRealizada.turma_id == turma.id
            )
        ).count()
        
        numero_aulas_da_classe = AulaModelo.query.filter_by(classe_id=turma.classe_id).count()
        
        if presencas_na_turma >= numero_aulas_da_classe:
            if not membro.participou_ctm:
                membro.participou_ctm = True
                registrar_evento_jornada(
                    tipo_acao='CONCLUSAO_CTM',
                    descricao_detalhada=f'Concluiu o ciclo de {numero_aulas_da_classe} aulas da Classe {turma.classe.nome}.',
                    usuario_executor=current_user,
                    membros=[membro]
                )
        else:
            membro.participou_ctm = False
            
        db.session.add(membro)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar presença: {e}', 'danger')

    return redirect(url_for('ctm.painel_facilitador_turma', turma_id=turma.id))

@ctm_bp.route('/presenca', methods=['GET', 'POST'])
def registrar_presenca_aluno():
    form = PresencaForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():            
            membro_id_selecionado = form.membro_id.data
            palavra_chave_digitada = form.palavra_chave_aula.data.strip().lower().replace(" ", "")
            avaliacao = form.avaliacao.data

            membro_obj = Membro.query.get(membro_id_selecionado)
            
            if not membro_obj:
                flash("Membro selecionado não encontrado. Por favor, selecione um nome da lista ou cadastre-se.", 'danger')
                return render_template('ctm/presenca.html', form=form, versao=versao, ano=ano)
            
            data_hoje = date.today()
            
            aula_realizada_hoje = AulaRealizada.query.filter_by(
                data=data_hoje,
                chave=palavra_chave_digitada
            ).first()

            if not aula_realizada_hoje:
                flash("Sua presença não foi registrada, pois não há aula cadastrada para hoje com essa palavra-chave.", 'danger')
                return render_template('ctm/presenca.html', form=form, versao=versao, ano=ano)

            turma_da_aula = aula_realizada_hoje.turma
            if membro_obj not in turma_da_aula.alunos:
                turma_da_aula.alunos.append(membro_obj)
                db.session.add(turma_da_aula)
                flash(f'{membro_obj.nome_completo} foi matriculado(a) na turma "{turma_da_aula.nome}".', 'info')

            ja_registrado = Presenca.query.filter_by(
                membro_id=membro_obj.id,
                aula_realizada_id=aula_realizada_hoje.id
            ).first()

            if ja_registrado:
                flash("Você já registrou presença para a aula de hoje.", 'warning')
                return render_template('ctm/presenca.html', form=form, versao=versao, ano=ano)
            
            nova_presenca = Presenca(
                membro_id=membro_obj.id,
                aula_realizada_id=aula_realizada_hoje.id,
                avaliacao=avaliacao
            )

            try:
                db.session.add(nova_presenca)
                db.session.commit()
                
                registrar_evento_jornada(
                    tipo_acao='PRESENCA_CTM',
                    descricao_detalhada=f'Presença registrada na aula {aula_realizada_hoje.aula_modelo.tema} da Turma {turma_da_aula.nome}.',
                    usuario_executor=membro_obj,
                    membros=[membro_obj],
                    turmas_ctm=[turma_da_aula]
                )
                
                flash(f'Presença de {membro_obj.nome_completo} para a aula de {aula_realizada_hoje.aula_modelo.tema} registrada com sucesso!', 'success')
                return render_template('ctm/confirmacao.html', nome=membro_obj.nome_completo, sucesso=True, versao=versao, ano=ano)
            
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao registrar presença: {str(e)}', 'danger')
                return render_template('ctm/presenca.html', form=form, versao=versao, ano=ano)

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Erro no campo '{getattr(form, field).label.text if hasattr(form, field) else field}': {error}", 'danger')
        return render_template('ctm/presenca.html', form=form, versao=versao, ano=ano)

    return render_template('ctm/presenca.html', form=form, versao=versao, ano=ano)

@ctm_bp.route('/confirmacao')
def confirmacao():
    return render_template('ctm/confirmacao.html',
                           nome="Visitante",
                           sucesso=False,
                           mensagem="Acesso inválido ou direto à página de confirmação.",
                           versao=versao,
                           ano=ano)

@ctm_bp.route('/relatorio')
@login_required
@admin_required
def relatorio_ctm():
    turma_id = request.args.get('turma_id', '')

    query_membros = Membro.query.join(aluno_turma).join(TurmaCTM).order_by(Membro.nome_completo)
    
    turma_selecionada = None
    if turma_id:
        turma_selecionada = TurmaCTM.query.get_or_404(turma_id)
        query_membros = query_membros.filter(TurmaCTM.id == turma_id)

    membros_para_relatorio = query_membros.all()
    
    todas_aulas = []
    if turma_selecionada:
        todas_aulas = AulaRealizada.query.filter_by(turma_id=turma_selecionada.id).order_by(AulaRealizada.data).all()
        
    datas_unicas_str = [aula.data.strftime('%Y-%m-%d') for aula in todas_aulas]
    datas_formatadas = [f"{aula.data.strftime('%d-%m')} ({aula.aula_modelo.ordem})" for aula in todas_aulas]
    mapa_datas = {f"{aula.data.strftime('%d-%m')} ({aula.aula_modelo.ordem})": aula.data.strftime('%Y-%m-%d') for aula in todas_aulas}

    relatorio_dados = []
    if todas_aulas:
        for membro in membros_para_relatorio:
            linha = {'Nome': membro.nome_completo}
            total_presencas_membro = 0
            
            presencas_membro_dict = {p.aula_realizada.data: p for p in membro.presencas}
            
            for aula_realizada_obj in todas_aulas:
                presente = aula_realizada_obj.data in presencas_membro_dict
                linha[aula_realizada_obj.data.strftime('%Y-%m-%d')] = '✔️' if presente else '❌'
                if presente:
                    total_presencas_membro += 1
            
            total_aulas_contadas = len(todas_aulas)
            faltas = total_aulas_contadas - total_presencas_membro
            linha['Faltas'] = faltas
            linha['% Presença'] = f'{(total_presencas_membro / total_aulas_contadas) * 100:.0f}%' if total_aulas_contadas > 0 else '0%'
            relatorio_dados.append(linha)
    
    relatorio_dados.sort(key=lambda x: (-int(x['% Presença'].replace('%', '')), x['Faltas']))

    lista_turmas = TurmaCTM.query.filter_by(ativa=True).order_by(TurmaCTM.nome).all()

    return render_template(
        'ctm/relatorio.html',
        relatorio=relatorio_dados,
        datas_formatadas=datas_formatadas,
        mapa_datas=mapa_datas,
        turma_id_selecionada=turma_id,
        turma_selecionada=turma_selecionada,
        lista_turmas=lista_turmas,
        versao=versao,
        ano=ano
    )

@ctm_bp.route('/download_relatorio')
@login_required
@admin_required
def download_excel_relatorio():
    turma_id = request.args.get('turma_id', '')

    query_membros = Membro.query.join(aluno_turma).join(TurmaCTM).order_by(Membro.nome_completo)
    
    turma_selecionada = None
    if turma_id:
        turma_selecionada = TurmaCTM.query.get_or_404(turma_id)
        query_membros = query_membros.filter(TurmaCTM.id == turma_id)

    membros_para_relatorio = query_membros.all()
    
    todas_aulas = []
    if turma_selecionada:
        todas_aulas = AulaRealizada.query.filter_by(turma_id=turma_selecionada.id).order_by(AulaRealizada.data).all()

    relatorio_dados = []
    if todas_aulas:
        for membro in membros_para_relatorio:
            linha = {'Nome': membro.nome_completo}
            total_presencas_membro = 0
            presencas_datas_membro = {p.aula_realizada.data for p in membro.presencas}

            for aula_realizada_obj in todas_aulas:
                presente = aula_realizada_obj.data in presencas_datas_membro
                linha[f"{aula_realizada_obj.data.strftime('%d/%m/%Y')} - {aula_realizada_obj.aula_modelo.tema}"] = '✔️' if presente else '❌'
                if presente:
                    total_presencas_membro += 1
            
            total_aulas_contadas = len(todas_aulas)
            faltas = total_aulas_contadas - total_presencas_membro
            linha['Faltas'] = faltas
            linha['% Presença'] = f'{(total_presencas_membro / total_aulas_contadas) * 100:.0f}%' if total_aulas_contadas > 0 else '0%'
            relatorio_dados.append(linha)
    
    relatorio_dados.sort(key=lambda x: (-int(x['% Presença'].replace('%', '')), x['Faltas']))

    df_final = pd.DataFrame(relatorio_dados)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Relatório de Presenças')
        workbook = writer.book
        worksheet = writer.sheets['Relatório de Presenças']
        for i, col in enumerate(df_final.columns):
            width = max(df_final[col].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.set_column(i, i, width)
    output.seek(0)
    
    turma_nome = turma_selecionada.nome if turma_selecionada else "geral"
    filename = f"relatorio_presencas_{turma_nome}.xlsx"
    return send_file(output,
                     download_name=filename,
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@ctm_bp.route('/classes')
@login_required
def listar_classes():
    return redirect(url_for('ctm.listar_ctm_unificada', tipo='classes'))

@ctm_bp.route('/turmas')
@login_required
def listar_turmas():
    return redirect(url_for('ctm.listar_ctm_unificada', tipo='turmas'))

@ctm_bp.route('/aulas-modelo')
@login_required
def listar_aulas_modelo():
    return redirect(url_for('ctm.listar_ctm_unificada', tipo='aulas_modelo'))
