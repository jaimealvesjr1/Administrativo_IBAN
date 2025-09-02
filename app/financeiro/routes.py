from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import login_required, current_user
from app.extensions import db
from datetime import datetime
from app.membresia.models import Membro
from app.grupos.models import PequenoGrupo, Setor, Area
from .models import Contribuicao
from .forms import ContribuicaoForm, ContribuicaoFilterForm
from config import Config
from sqlalchemy import func, extract, and_, or_
from app.jornada.models import registrar_evento_jornada, JornadaEvento
from app.filters import format_currency
import pandas as pd
import io
from app.decorators import admin_required, financeiro_required, group_permission_required

financeiro_bp = Blueprint('financeiro', __name__, url_prefix='/financeiro')
ano=Config.ANO_ATUAL
versao=Config.VERSAO_APP

@financeiro_bp.route('/')
@financeiro_bp.route('/index')
@login_required
@financeiro_required
def index():
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year

    total_mes_atual_query = db.session.query(func.sum(Contribuicao.valor)).filter(
        and_(
            extract('month', Contribuicao.data_lanc) == mes_atual,
            extract('year', Contribuicao.data_lanc) == ano_atual
        )
    ).scalar()
    total_mes_atual = round(float(total_mes_atual_query), 2) if total_mes_atual_query else 0.0

    num_contribuicoes_mes = db.session.query(Contribuicao).filter(
        and_(
            extract('month', Contribuicao.data_lanc) == mes_atual,
            extract('year', Contribuicao.data_lanc) == ano_atual
        )
    ).count()

    total_membros_cadastrados = Membro.query.count()

    chart_labels_meses_nomes = []
    chart_datasets_campus_mes = []
    chart_datasets_status_mes = []

    meses_presentes = set()

    contribuicoes_por_campus_mes_query = db.session.query(
        Membro.campus,
        extract('month', Contribuicao.data_lanc).label('mes'),
        func.sum(Contribuicao.valor).label('total_valor')
    ).join(Membro).filter(
        extract('year', Contribuicao.data_lanc) == ano_atual
    ).group_by(
        Membro.campus,
        extract('month', Contribuicao.data_lanc)
    ).order_by(
        Membro.campus,
        extract('month', Contribuicao.data_lanc)
    ).all()

    dados_grafico_campus_mes = {}

    for campus, mes, total_valor in contribuicoes_por_campus_mes_query:
        if campus not in dados_grafico_campus_mes:
            dados_grafico_campus_mes[campus] = {}
        dados_grafico_campus_mes[campus][int(mes)] = round(float(total_valor), 2)
        meses_presentes.add(int(mes))

    meses_ordenados_nomes_map = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    chart_labels_meses_numeros = sorted(list(meses_presentes))
    chart_labels_meses_nomes = [meses_ordenados_nomes_map[m] for m in chart_labels_meses_numeros]

    cores_campus = Config.CAMPUS
    for campus in sorted(dados_grafico_campus_mes.keys()):
        data_para_campus = []
        for mes_num in chart_labels_meses_numeros:
            data_para_campus.append(dados_grafico_campus_mes[campus].get(mes_num, 0))

        chart_datasets_campus_mes.append({
            'label': campus,
            'data': data_para_campus,
            'backgroundColor': cores_campus.get(campus, '#6c757d'),
            'borderColor': cores_campus.get(campus, '#6c757d'),
            'borderWidth': 1
        })


    contribuicoes_por_membro_e_mes = db.session.query(
        Contribuicao.membro_id,
        extract('month', Contribuicao.data_lanc).label('mes'),
        func.sum(Contribuicao.valor).label('total_valor')
    ).join(Membro).filter(
        extract('year', Contribuicao.data_lanc) == ano_atual
    ).group_by(
        Contribuicao.membro_id,
        extract('month', Contribuicao.data_lanc)
    ).all()

    dados_grafico_categorias = {}

    for membro_id, mes, total_valor in contribuicoes_por_membro_e_mes:
        membro = Membro.query.get(membro_id)
        if not membro:
            continue

        categoria = None

        if PequenoGrupo.query.filter_by(facilitador_id=membro.id).first():
            categoria = 'Facilitador'
        elif PequenoGrupo.query.filter_by(anfitriao_id=membro.id).first():
            categoria = 'Anfitrião'
        elif membro in membro.areas_supervisionadas or membro in membro.setores_supervisionados:
            categoria = 'Supervisor'
        elif membro.status == 'Não Membro':
            categoria = 'Não Membro'
        
        if categoria:
            if categoria not in dados_grafico_categorias:
                dados_grafico_categorias[categoria] = {}
            
            dados_grafico_categorias[categoria][int(mes)] = dados_grafico_categorias[categoria].get(int(mes), 0) + float(total_valor)
            meses_presentes.add(int(mes))

    cores_categorias = Config.STATUS

    categorias_ordenadas = ['Facilitador', 'Supervisor', 'Anfitrião', 'Não-Membro']

    for categoria in categorias_ordenadas:
        if categoria in dados_grafico_categorias:
            data_para_categoria = []
            for mes_num in chart_labels_meses_numeros:
                data_para_categoria.append(dados_grafico_categorias[categoria].get(mes_num, 0))

            chart_datasets_status_mes.append({
                'label': categoria,
                'data': data_para_categoria,
                'backgroundColor': cores_categorias.get(categoria, '#6c757d'),
                'borderColor': cores_categorias.get(categoria, '#6c757d'),
                'borderWidth': 1
            })

    return render_template(
        'financeiro/index.html',
        ano=ano,
        versao=versao,
        now=datetime.now(),
        total_mes_atual=total_mes_atual,
        num_contribuicoes_mes=num_contribuicoes_mes,
        total_membros_cadastrados=total_membros_cadastrados,
        chart_labels_meses=chart_labels_meses_nomes,
        chart_datasets_campus_mes=chart_datasets_campus_mes,
        chart_datasets_status_mes=chart_datasets_status_mes
    )

@financeiro_bp.route('/novo', methods=['GET', 'POST'])
@login_required
@financeiro_required
def nova_contribuicao():
    form = ContribuicaoForm(contribuicao=None)
    form.membro_id.choices = [('', 'Selecione um membro')] + \
                             [(m.id, m.nome_completo) for m in Membro.query.order_by(Membro.nome_completo).all()]

    if form.validate_on_submit():
        query = Contribuicao.query.filter(
            Contribuicao.membro_id == form.membro_id.data,
            Contribuicao.valor == form.valor.data,
            Contribuicao.data_lanc == form.data_lanc.data
        )
        if query.first():
            flash('Já existe uma contribuição com o mesmo valor e data para este membro.', 'danger')
            return redirect(url_for('financeiro.nova_contribuicao'))

        contrib = Contribuicao(
            membro_id=form.membro_id.data,
            tipo=form.tipo.data,
            valor=form.valor.data,
            data_lanc=form.data_lanc.data,
            forma=form.forma.data,
            observacoes=form.observacoes.data
        )

        try:
            db.session.add(contrib)
            db.session.commit()

            membro_associado = Membro.query.get(contrib.membro_id)
            if membro_associado:
                descricao_membro = f"Contribuiu com {contrib.tipo}."
                registrar_evento_jornada(
                    tipo_acao='CONTRIBUICAO',
                    descricao_detalhada=descricao_membro,
                    usuario_executor=current_user,
                    membros=[membro_associado]
                )
                
                if contrib.tipo == 'Dízimo' and membro_associado.pg_participante:
                    pg_associado = membro_associado.pg_participante
                    descricao_pg = f"Participante {membro_associado.nome_completo} contribuiu com dízimo."
                    registrar_evento_jornada(
                        tipo_acao='CONTRIBUICAO',
                        descricao_detalhada=descricao_pg,
                        usuario_executor=current_user,
                        pgs=[pg_associado]
                    )

            flash('Contribuição lançada com sucesso!', 'success')
            return redirect(url_for('financeiro.lancamentos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao lançar contribuição: {str(e)}', 'error')

    return render_template('financeiro/registro.html',
                            form=form, ano=ano, versao=versao)

@financeiro_bp.route('/lancamentos')
@login_required
@financeiro_required
def lancamentos():
    filter_form = ContribuicaoFilterForm(request.args, meta={'csrf': False})

    query = Contribuicao.query.join(Membro)

    if filter_form.validate():
        busca_nome = filter_form.busca_nome.data
        tipo_filtro = filter_form.tipo_filtro.data
        campus_filtro = filter_form.campus_filtro.data
        status_filtro = filter_form.status_filtro.data
        data_inicial = filter_form.data_inicial.data
        data_final = filter_form.data_final.data

        if busca_nome:
            query = query.filter(Membro.nome_completo.ilike(f'%{busca_nome}%'))
        if tipo_filtro:
            query = query.filter(Contribuicao.tipo == tipo_filtro)
        if campus_filtro:
            query = query.filter(Membro.campus == campus_filtro)
        if status_filtro:
            if status_filtro == 'Facilitador':
                query = query.filter(Membro.pgs_facilitados.any())
            elif status_filtro == 'Supervisor':
                query = query.filter(or_(Membro.setores_supervisionados.any(), Membro.areas_supervisionadas.any()))
            else:
                query = query.filter(Membro.status == status_filtro)
        if data_inicial:
            query = query.filter(Contribuicao.data_lanc >= data_inicial)
        if data_final:
            query = query.filter(Contribuicao.data_lanc <= data_final)
    else:
        for field_name, errors in filter_form.errors.items():
            for error in errors:
                if field_name != 'csrf_token':
                    field_obj = getattr(filter_form, field_name, None)
                    field_label = field_obj.label.text if field_obj and hasattr(field_obj, 'label') else field_name
                    flash(f"Erro no filtro '{field_label}': {error}", 'danger')

    soma_valores_query = query.with_entities(func.sum(Contribuicao.valor)).scalar()

    if soma_valores_query is None:
        soma_valores_query = 0.0
    else:
        soma_valores_query = round(float(soma_valores_query), 2)

    contribuicoes = query.order_by(Contribuicao.data_lanc.desc(), Membro.nome_completo).all()

    return render_template(
        'financeiro/lancamentos.html',
        contribuicoes=contribuicoes,
        soma_valores=soma_valores_query,
        filter_form=filter_form,
        versao=versao,
        ano=ano
    )

@financeiro_bp.route('download_lancamentos_excel')
@login_required
@financeiro_required
def download_lancamentos_excel():
    busca_nome = request.args.get('busca_nome', '')
    tipo_filtro = request.args.get('tipo_filtro', '')
    campus_filtro = request.args.get('campus_filtro', '')
    status_filtro = request.args.get('status_filtro', '')
    data_inicial_str = request.args.get('data_inicial', '')
    data_final_str = request.args.get('data_final', '')

    query = Contribuicao.query.join(Membro)

    if busca_nome:
        query = query.filter(Membro.nome_completo.ilike(f'%{busca_nome}%'))
    if tipo_filtro:
        query = query.filter(Contribuicao.tipo == tipo_filtro)
    if campus_filtro:
        query = query.filter(Membro.campus == campus_filtro)
    if status_filtro:
        if status_filtro == 'Facilitador':
            query = query.filter(Membro.pgs_facilitados.any())
        elif status_filtro == 'Supervisor':
            query = query.filter(or_(Membro.setores_supervisionados.any(), Membro.areas_supervisionadas.any()))
        else:
            query = query.filter(Membro.status == status_filtro)

    if data_inicial_str:
        try:
            data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d').date()
            query = query.filter(Contribuicao.data_lanc >= data_inicial)
        except ValueError:
            flash("Formato de Data Inicial inválido para o download.", 'danger')
            return redirect(url_for('financeiro.lancamentos'))
    if data_final_str:
        try:
            data_final = datetime.strptime(data_final_str, '%Y-%m-%d').date()
            query = query.filter(Contribuicao.data_lanc <= data_final)
        except ValueError:
            flash("Formato de Data Final inválido para o download.", 'danger')
            return redirect(url_for('financeiro.lancamentos'))

    contribuicoes = query.order_by(Contribuicao.data_lanc.desc(), Membro.nome_completo).all()

    relatorio_dados = []
    for contrib in contribuicoes:
        relatorio_dados.append({
            'Data': contrib.data_lanc.strftime('%d/%m/%Y'),
            'Pessoa': contrib.membro.nome_completo,
            'Valor': contrib.valor,
            'Tipo': contrib.tipo,
            'Forma': contrib.forma,
            'Campus': contrib.membro.campus,
            'Observações': contrib.observacoes if contrib.observacoes else ''
        })

    df_final = pd.DataFrame(relatorio_dados)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Lançamentos Financeiros')
        workbook = writer.book
        worksheet = writer.sheets['Lançamentos Financeiros']

        for i, col in enumerate(df_final.columns):
            max_len = 0
            if not df_final[col].empty:
                 max_len = max(df_final[col].astype(str).map(len).max(), len(str(col)))
            else:
                 max_len = len(str(col))
            width = max_len + 2
            worksheet.set_column(i, i, width)

    output.seek(0)

    filename_parts = ['lancamentos']
    if busca_nome:
        filename_parts.append(f"nome_{busca_nome}")
    if tipo_filtro:
        filename_parts.append(f"tipo_{tipo_filtro}")
    if campus_filtro:
        filename_parts.append(f"campus_{campus_filtro}")
    if status_filtro:
        filename_parts.append(f"status_{status_filtro}")
    if data_inicial_str and data_final_str:
        filename_parts.append(f"de_{data_inicial_str}_ate_{data_final_str}")
    elif data_inicial_str:
        filename_parts.append(f"de_{data_inicial_str}")
    elif data_final_str:
        filename_parts.append(f"ate_{data_final_str}")

    filename = "_".join(filename_parts) + ".xlsx"

    return send_file(output,
                     download_name=filename,
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@financeiro_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@financeiro_required
def editar_contribuicao(id):
    contribuicao = Contribuicao.query.get_or_404(id)
    form = ContribuicaoForm(obj=contribuicao, contribuicao=contribuicao)

    old_membro = contribuicao.membro_id
    old_valor = contribuicao.valor
    old_tipo = contribuicao.tipo
    old_forma = contribuicao.forma

    form.membro_id.choices = [(contribuicao.membro.id, contribuicao.membro.nome_completo)]

    if form.validate_on_submit():
        query = Contribuicao.query.filter(
            Contribuicao.membro_id == form.membro_id.data,
            Contribuicao.valor == form.valor.data,
            Contribuicao.data_lanc == form.data_lanc.data
        ).filter(Contribuicao.id != contribuicao.id)

        if query.first():
            flash('Já existe uma contribuição com o mesmo valor e data para este membro.', 'danger')
            return redirect(url_for('financeiro.editar_contribuicao', id=id))

        form.populate_obj(contribuicao)
        
        try:
            db.session.commit()

            membro_associado = Membro.query.get(contribuicao.membro_id)
            if membro_associado and (old_valor != contribuicao.valor or old_tipo != contribuicao.tipo or old_forma != contribuicao.forma):
                descricao_membro = f"Contribuição de {membro_associado.nome_completo} ({old_tipo}) atualizada. Mudanças: "
                mudancas = []
                if old_tipo != contribuicao.tipo:
                    mudancas.append(f'Tipo: {old_tipo} -> {contribuicao.tipo}')
                if old_valor != contribuicao.valor:
                    mudancas.append(f'Valor: R$ {old_valor} -> R$ {contribuicao.valor}')
                if old_forma != contribuicao.forma:
                    mudancas.append(f'Forma: {old_forma} -> {contribuicao.forma}')
                
                descricao_membro += '; '.join(mudancas)

                registrar_evento_jornada(
                    tipo_acao='CONTRIBUICAO',
                    descricao_detalhada=descricao_membro,
                    usuario_executor=current_user,
                    membros=[membro_associado]
                )

                if contribuicao.tipo == 'Dízimo' and membro_associado.pg_participante:
                    pg_associado = membro_associado.pg_participante
                    descricao_pg = f"Contribuição de dízimo de {membro_associado.nome_completo} foi atualizada."
                    registrar_evento_jornada(
                        tipo_acao='CONTRIBUICAO',
                        descricao_detalhada=descricao_pg,
                        usuario_executor=current_user,
                        pgs=[pg_associado]
                    )
            
            flash(f'Contribuição de {contribuicao.membro.nome_completo} atualizada com sucesso!', 'success')
            return redirect(url_for('financeiro.lancamentos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar contribuição: {str(e)}', 'danger')

    return render_template('financeiro/registro.html',
                            form=form,
                            ano=ano,
                            versao=versao)

@financeiro_bp.route('/buscar_membros_financeiro')
@login_required
@financeiro_required
def buscar_membros_financeiro():
    search_term = request.args.get('term', '')
    results = []
    membros_ativos = Membro.query.filter(Membro.nome_completo.ilike(f'%{search_term}%'), Membro.ativo==True).limit(50).all()
    for membro in membros_ativos:
        results.append({'id': membro.id, 'text': membro.nome_completo})

    for campus_name, anon_id in Config.IDS_OFERTA_ANONIMA_POR_CAMPUS.items():
        membro_anonimo = Membro.query.get(anon_id)
        if membro_anonimo:
            anonimo_full_name = membro_anonimo.nome_completo.lower()
            if not search_term or \
               search_term.lower() in anonimo_full_name or \
               str(anon_id) == search_term:
                if not any(r['id'] == membro_anonimo.id for r in results):
                    results.insert(0, {'id': membro_anonimo.id, 'text': membro_anonimo.nome_completo})

    return jsonify(items=results)
