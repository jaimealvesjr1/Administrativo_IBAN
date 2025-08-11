from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import login_required, current_user
from app.decorators import admin_required
from app.extensions import db
from app.membresia.models import Membro
from .models import Presenca, Aula
from .forms import PresencaForm, AulaForm, PresencaManualForm
from datetime import date, datetime
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
    aulas = Aula.query.order_by(Aula.data.desc()).all()

    ultimas_aulas = Aula.query.order_by(Aula.data.desc()).limit(4).all()
    media_presentes_ultimas_4_aulas = 0

    if ultimas_aulas:
        total_presentes_nas_ultimas_4 = 0
        total_membros_ativos_para_calculo = Membro.query.filter_by(ativo=True).count()
        if total_membros_ativos_para_calculo == 0:
            media_presentes_ultimas_4_aulas = 0
        else:
            for aula_obj in ultimas_aulas:
                presencas_na_aula = Presenca.query.filter_by(aula_id=aula_obj.id).count()
                total_presentes_nas_ultimas_4 += presencas_na_aula
            
            media_presentes_ultimas_4_aulas = (total_presentes_nas_ultimas_4 / len(ultimas_aulas)) / total_membros_ativos_para_calculo * 100
            media_presentes_ultimas_4_aulas = round(media_presentes_ultimas_4_aulas, 1)

    total_alunos_com_presenca = db.session.query(Presenca.membro_id).distinct().count()

    dados_por_campus = {}
    campus_list_for_chart_filter = ['Todos'] + sorted(Config.CAMPUS.keys()) 
    
    all_aulas_for_charts = Aula.query.order_by(Aula.data).all()
    
    for campus in campus_list_for_chart_filter:
        membros_do_campus = Membro.query.filter_by(ativo=True)
        if campus != 'Todos':
            membros_do_campus = membros_do_campus.filter_by(campus=campus)
        membros_do_campus_list = membros_do_campus.all()
        total_lideres_ativos_no_campus = len(membros_do_campus_list)

        dados_campus_atual = []
        for aula_obj in all_aulas_for_charts:
            presentes_na_aula_no_campus = db.session.query(Presenca).filter(
                Presenca.aula_id == aula_obj.id,
                Presenca.membro_id.in_([m.id for m in membros_do_campus_list])
            ).count()
            
            faltas_na_aula_no_campus = max(0, total_lideres_ativos_no_campus - presentes_na_aula_no_campus)

            dados_campus_atual.append({
                'data': aula_obj.data.strftime('%d/%m'),
                'presentes': presentes_na_aula_no_campus,
                'faltas': faltas_na_aula_no_campus
            })
        dados_por_campus[campus] = dados_campus_atual

    media_por_campus_query = db.session.query(
        Membro.campus,
        db.func.avg(Presenca.avaliacao)
    ).join(Presenca).filter(Presenca.avaliacao.isnot(None)).group_by(Membro.campus).all()
    media_por_campus_dict = {campus: round(media, 2) for campus, media in media_por_campus_query}

    media_por_tema_query = db.session.query(
        Aula.tema,
        db.func.avg(Presenca.avaliacao)
    ).join(Presenca).filter(Presenca.avaliacao.isnot(None)).group_by(Aula.tema).all()
    media_por_tema_dict = {tema: round(media, 2) for tema, media in media_por_tema_query}
    
    if not media_por_campus_dict:
        media_por_campus_dict = {'Sem Dados': 0}
    if not media_por_tema_dict:
        media_por_tema_dict = {'Sem Dados': 0}

    todos_membros_ativos = Membro.query.filter_by(ativo=True).order_by(Membro.nome_completo).all()
    
    presenca_manual_form = PresencaManualForm()
    presenca_manual_form.membro_id.choices = [('', 'Selecione um membro')] + \
                                            [(m.id, m.nome_completo) for m in todos_membros_ativos]

    aula_form = AulaForm()
    if not aula_form.data.data:
        aula_form.data.data = date.today()

    return render_template('ctm/admin_dashboard.html',
                           total_alunos_com_presenca=total_alunos_com_presenca,
                           media_presentes_ultimas_4_aulas=media_presentes_ultimas_4_aulas,
                           dados_grafico=dados_por_campus,
                           campus_list_for_chart_filter=campus_list_for_chart_filter,
                           media_por_campus=media_por_campus_dict,
                           media_por_tema=media_por_tema_dict,
                           aulas=aulas,
                           nomes=todos_membros_ativos,
                           versao=versao, ano=ano,
                           today=date.today(),
                           presenca_manual_form=presenca_manual_form,
                           aula_form=aula_form)

@ctm_bp.route('/presenca', methods=['GET', 'POST'])
def registrar_presenca_aluno():
    form = PresencaForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():            
            membro_id_selecionado = form.membro_id.data
            palavra_chave_digitada = form.palavra_chave_aula.data.strip().lower()
            avaliacao = form.avaliacao.data

            membro_obj = Membro.query.get(membro_id_selecionado)

            if not membro_obj:
                flash("Membro selecionado não encontrado. Por favor, selecione um nome da lista ou cadastre-se.", 'error')
                return render_template('ctm/presenca.html', form=form)
            
            data_hoje = date.today()
            aula_hoje = Aula.query.filter_by(data=data_hoje).first()

            if not aula_hoje:
                flash("Sua presença não foi registrada, pois não há aula cadastrada para hoje.", 'error')
                return render_template('ctm/presenca.html', form=form)
            
            if palavra_chave_digitada != aula_hoje.chave.lower():
                flash("Sua presença não foi registrada, pois a palavra-chave está incorreta. 😕", 'error')
                return render_template('ctm/presenca.html', form=form)

            ja_registrado = Presenca.query.filter_by(
                membro_id=membro_obj.id,
                aula_id=aula_hoje.id
            ).first()

            if ja_registrado:
                flash("Você já registrou presença hoje.", 'warning')
                db.session.rollback()
                return render_template('ctm/presenca.html', form=form)
            
            nova_presenca = Presenca(
                membro_id=membro_obj.id,
                aula_id=aula_hoje.id,
                avaliacao=avaliacao
            )

            try:
                db.session.add(nova_presenca)
                db.session.commit()

                nova_presenca.registrar_evento_jornada()
                db.session.commit()

                flash(f'Presença de {membro_obj.nome_completo} para a aula de {aula_hoje.tema} registrada com sucesso!', 'success')
                return render_template('ctm/confirmacao.html',
                                       nome=membro_obj.nome_completo, sucesso=True, versao=versao, ano=ano)
            
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao registrar presença: {str(e)}', 'error')
                return render_template('ctm/presenca.html', form=form)

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Erro no campo '{getattr(form, field).label.text if hasattr(form, field) else field}': {error}", 'danger')
            
            return render_template('ctm/presenca.html', form=form)

    return render_template('ctm/presenca.html',
                           form=form,
                           versao=versao,
                           ano=ano)

@ctm_bp.route('/confirmacao')
def confirmacao():
    return render_template('ctm/confirmacao.html',
                           nome="Visitante",
                           sucesso=False,
                           mensagem="Acesso inválido ou direto à página de confirmação.",
                           versao=versao,
                           ano=ano)

@ctm_bp.route('/admin/cadastrar-aula', methods=['POST'])
@login_required
@admin_required
def cadastrar_aula():
    form = AulaForm()
    if form.validate_on_submit():
        data = form.data.data
        tema = form.tema.data
        chave = form.chave.data.strip().lower()

        aula_existente = Aula.query.filter_by(data=data).first()
        if aula_existente:
            flash(f"Já existe uma aula cadastrada para a data {data.strftime('%d/%m/%Y')}. Edite a existente se necessário.", 'warning')
            return redirect(url_for('ctm.index'))
        
        nova_aula = Aula(data=data, tema=tema, chave=chave)
        try:
            db.session.add(nova_aula)
            db.session.commit()
            flash('Aula cadastrada com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar aula: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo {getattr(form, field).label.text}: {error}", 'error')

    return redirect(url_for('ctm.index'))

@ctm_bp.route('/admin/adicionar-presenca-manual', methods=['POST'])
@login_required
@admin_required
def adicionar_presenca_manual():
    presenca_manual_form = PresencaManualForm()

    if presenca_manual_form.validate_on_submit():
        aula_id = presenca_manual_form.aula_id.data
        membro_id = presenca_manual_form.membro_id.data
        
        membro = Membro.query.get(membro_id)
        if not membro:
            flash(f"Membro selecionado não encontrado.", 'error')
            return redirect(url_for('ctm.index'))
        
        aula = Aula.query.get(aula_id)
        if not aula:
            flash("Aula selecionada não encontrada.", 'error')
            return redirect(url_for('ctm.index'))

        ja_registrado = Presenca.query.filter_by(
            membro_id=membro.id,
            aula_id=aula.id
        ).first()

        if ja_registrado:
            flash(f"{membro.nome_completo} já possui presença registrada para a aula de {aula.data.strftime('%d/%m/%Y')}.", 'warning')
            db.session.rollback()
            return redirect(url_for('ctm.index'))

        nova_presenca = Presenca(
            membro_id=membro.id,
            aula_id=aula.id,
        )
        try:
            db.session.add(nova_presenca)
            db.session.commit()

            nova_presenca.registrar_evento_jornada()
            db.session.commit

            flash(f'Presença manual de {membro.nome_completo} para a aula de {aula.data.strftime("%d/%m/%Y")} registrada com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar presença manual: {str(e)}', 'error')
    else:
        for field, errors in presenca_manual_form.errors.items():
            for error in errors:
                flash(f"Erro no campo {getattr(presenca_manual_form, field).label.text}: {error}", 'error')

    return redirect(url_for('ctm.index'))

@ctm_bp.route('/relatorio')
@login_required
@admin_required
def relatorio_ctm():
    campus_filtro = request.args.get('campus', '')
    status_filtro = request.args.get('status', '')

    query_membros = Membro.query.filter_by(ativo=True)
    
    if campus_filtro:
        query_membros = query_membros.filter_by(campus=campus_filtro)
    if status_filtro:
        query_membros = query_membros.filter_by(status=status_filtro)
    
    membros_para_relatorio = query_membros.order_by(Membro.nome_completo).all()

    todas_aulas = Aula.query.order_by(Aula.data).all()
    datas_unicas_str = [aula.data.strftime('%Y-%m-%d') for aula in todas_aulas]
    datas_formatadas = [aula.data.strftime('%d-%m') for aula in todas_aulas]
    mapa_datas = {aula.data.strftime('%d-%m'): aula.data.strftime('%Y-%m-%d') for aula in todas_aulas}

    relatorio_dados = []
    if todas_aulas:
        for membro in membros_para_relatorio:
            linha = {'Nome': membro.nome_completo}
            total_presencas_membro = 0
            
            presencas_membro_dict = {p.aula.data: p for p in membro.presencas if p.aula in todas_aulas}

            for aula_obj in todas_aulas:
                presente = aula_obj.data in presencas_membro_dict
                linha[aula_obj.data.strftime('%Y-%m-%d')] = '✔️' if presente else '❌'
                if presente:
                    total_presencas_membro += 1
            
            total_aulas_contadas = len(todas_aulas)
            faltas = total_aulas_contadas - total_presencas_membro
            linha['Faltas'] = faltas
            linha['% Presença'] = f'{(total_presencas_membro / total_aulas_contadas) * 100:.0f}%' if total_aulas_contadas > 0 else '0%'
            relatorio_dados.append(linha)
    
    relatorio_dados.sort(key=lambda x: (-int(x['% Presença'].replace('%', '')), x['Faltas']))

    lista_campus_disponiveis = sorted(Config.CAMPUS.keys())
    lista_funcoes_disponiveis = sorted(Config.STATUS.keys())

    return render_template(
        'ctm/relatorio.html',
        relatorio=relatorio_dados,
        datas_formatadas=datas_formatadas,
        mapa_datas=mapa_datas,
        campus_filtro=campus_filtro,
        status_filtro=status_filtro,
        lista_campus=lista_campus_disponiveis,
        lista_funcoes=lista_funcoes_disponiveis,
        versao=versao,
        ano=ano
    )

@ctm_bp.route('/download_relatorio')
@login_required
@admin_required
def download_excel_relatorio():
    campus_filtro = request.args.get('campus', '')
    status_filtro = request.args.get('status', '')

    query_membros = Membro.query.filter_by(ativo=True)
    if campus_filtro:
        query_membros = query_membros.filter_by(campus=campus_filtro)
    if status_filtro:
        query_membros = query_membros.filter_by(status=status_filtro)
    
    membros_para_relatorio = query_membros.order_by(Membro.nome_completo).all()


    todas_aulas = Aula.query.order_by(Aula.data).all()

    relatorio_dados = []
    if todas_aulas:
        for membro in membros_para_relatorio:
            linha = {'Nome': membro.nome_completo}
            total_presencas_membro = 0
            presencas_datas_membro = {p.aula.data for p in membro.presencas if p.aula in todas_aulas}

            for aula_obj in todas_aulas:
                presente = aula_obj.data in presencas_datas_membro
                linha[aula_obj.data.strftime('%Y-%m-%d')] = '✔️' if presente else '❌'
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

    filename = f"relatorio_presencas_{campus_filtro if campus_filtro else 'geral'}{'_'+status_filtro if status_filtro else ''}.xlsx"
    return send_file(output,
                     download_name=filename,
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@ctm_bp.route('/buscar_membros')
@login_required
def buscar_membros():
    search_term = request.args.get('term', '')

    membros = Membro.query.filter(Membro.nome_completo.ilike(f'%{search_term}%')).limit(50).all()

    results = []
    for membro in membros:
        results.append({'id': membro.id, 'text': membro.nome_completo})

    return jsonify(items=results)
