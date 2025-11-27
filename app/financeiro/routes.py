from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import login_required, current_user
from app.extensions import db
from datetime import datetime
from app.membresia.models import Membro
from app.grupos.models import PequenoGrupo, Setor, Area
from .models import Contribuicao, CategoriaDespesa, ItemDespesa, Despesa
from .forms import (
    ContribuicaoForm, ContribuicaoFilterForm, 
    CategoriaDespesaForm, ItemDespesaForm, DespesaForm, DespesaFilterForm
)
from config import Config
from sqlalchemy import func, extract, and_, or_
from app.jornada.models import registrar_evento_jornada, JornadaEvento
from app.filters import format_currency
import pandas as pd
import io, random
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

    # --- 1. CÁLCULO DOS CARDS (Valores do Mês Atual) ---
    
    # Receitas
    total_receitas_mes_query = db.session.query(func.sum(Contribuicao.valor)).filter(
        and_(
            extract('month', Contribuicao.data_lanc) == mes_atual,
            extract('year', Contribuicao.data_lanc) == ano_atual
        )
    ).scalar()
    total_receitas_mes = round(float(total_receitas_mes_query), 2) if total_receitas_mes_query else 0.0

    num_contribuicoes_mes = db.session.query(Contribuicao).filter(
        and_(
            extract('month', Contribuicao.data_lanc) == mes_atual,
            extract('year', Contribuicao.data_lanc) == ano_atual
        )
    ).count()

    # Despesas
    total_despesas_mes_query = db.session.query(func.sum(Despesa.valor)).filter(
        and_(
            extract('month', Despesa.data_lanc) == mes_atual,
            extract('year', Despesa.data_lanc) == ano_atual
        )
    ).scalar()
    total_despesas_mes = round(float(total_despesas_mes_query), 2) if total_despesas_mes_query else 0.0

    num_despesas_mes = db.session.query(Despesa).filter(
        and_(
            extract('month', Despesa.data_lanc) == mes_atual,
            extract('year', Despesa.data_lanc) == ano_atual
        )
    ).count()
    
    # Saldo
    saldo_mes_atual = total_receitas_mes - total_despesas_mes

    # --- 2. PREPARAÇÃO DOS DADOS DOS GRÁFICOS (Ano Atual) ---
    
    meses_presentes = set()
    
    # Query 1: Receitas (Entradas) por Centro de Custo
    receitas_cc_query = db.session.query(
        Contribuicao.centro_custo,
        extract('month', Contribuicao.data_lanc).label('mes'),
        func.sum(Contribuicao.valor).label('total_valor')
    ).filter(
        extract('year', Contribuicao.data_lanc) == ano_atual,
        Contribuicao.centro_custo.isnot(None) # Ignora lançamentos antigos sem C.C.
    ).group_by(Contribuicao.centro_custo, 'mes').all()
    
    dados_receitas_cc = {}
    for cc, mes, total in receitas_cc_query:
        meses_presentes.add(int(mes))
        if cc not in dados_receitas_cc: dados_receitas_cc[cc] = {}
        dados_receitas_cc[cc][int(mes)] = round(float(total), 2)

    # Query 2: Despesas (Saídas) por Centro de Custo
    despesas_cc_query = db.session.query(
        Despesa.centro_custo,
        extract('month', Despesa.data_lanc).label('mes'),
        func.sum(Despesa.valor).label('total_valor')
    ).filter(
        extract('year', Despesa.data_lanc) == ano_atual,
        Despesa.centro_custo.isnot(None) # Ignora lançamentos antigos sem C.C.
    ).group_by(Despesa.centro_custo, 'mes').all()

    dados_despesas_cc = {}
    for cc, mes, total in despesas_cc_query:
        meses_presentes.add(int(mes))
        if cc not in dados_despesas_cc: dados_despesas_cc[cc] = {}
        dados_despesas_cc[cc][int(mes)] = round(float(total), 2)

    # Query 3: Despesas (Saídas) por Categoria
    despesas_cat_query = db.session.query(
        CategoriaDespesa.nome,
        extract('month', Despesa.data_lanc).label('mes'),
        func.sum(Despesa.valor).label('total_valor')
    ).join(ItemDespesa, Despesa.item_id == ItemDespesa.id)\
     .join(CategoriaDespesa, ItemDespesa.categoria_id == CategoriaDespesa.id)\
     .filter(
        extract('year', Despesa.data_lanc) == ano_atual
    ).group_by(CategoriaDespesa.nome, 'mes').all()
    
    dados_despesas_cat = {}
    for cat, mes, total in despesas_cat_query:
        meses_presentes.add(int(mes))
        if cat not in dados_despesas_cat: dados_despesas_cat[cat] = {}
        dados_despesas_cat[cat][int(mes)] = round(float(total), 2)


    # --- 3. GERAÇÃO DOS LABELS E DATASETS (para o Chart.js) ---
    
    meses_ordenados_nomes_map = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }
    
    # Garante que mesmo meses sem dados apareçam se houver dados em outros gráficos
    meses_com_dados = sorted(list(meses_presentes))
    chart_labels_meses_nomes = [meses_ordenados_nomes_map.get(m, m) for m in meses_com_dados]

    # Cores
    cores_centro_custo_map = Config.CORES_CAMPUS.copy()
    cores_centro_custo_map.setdefault('Geral', '#6c757d') # Adiciona 'Geral' se não existir

    # Datasets 1: Receitas por Centro de Custo
    chart_datasets_receitas_cc = []
    for cc_nome in sorted(dados_receitas_cc.keys()):
        data = [dados_receitas_cc[cc_nome].get(mes_num, 0) for mes_num in meses_com_dados]
        cor = cores_centro_custo_map.get(cc_nome, '#6c757d')
        chart_datasets_receitas_cc.append({
            'label': cc_nome, 'data': data,
            'backgroundColor': cor, 'borderColor': cor, 'borderWidth': 1
        })

    # Datasets 2: Despesas por Centro de Custo
    chart_datasets_despesas_cc = []
    for cc_nome in sorted(dados_despesas_cc.keys()):
        data = [dados_despesas_cc[cc_nome].get(mes_num, 0) for mes_num in meses_com_dados]
        cor = cores_centro_custo_map.get(cc_nome, '#6c757d')
        chart_datasets_despesas_cc.append({
            'label': cc_nome, 'data': data,
            'backgroundColor': cor, 'borderColor': cor, 'borderWidth': 1
        })
    
    # Datasets 3: Despesas por Categoria
    chart_datasets_despesas_cat = []
    cores_basicas = ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff', '#ff9f40', '#c9cbcf']
    
    for i, cat_nome in enumerate(sorted(dados_despesas_cat.keys())):
        data = [dados_despesas_cat[cat_nome].get(mes_num, 0) for mes_num in meses_com_dados]
        # Usa cores básicas ou gera uma aleatória
        cor = cores_basicas[i % len(cores_basicas)] if i < len(cores_basicas) else f'#{random.randint(0, 0xFFFFFF):06x}'
        chart_datasets_despesas_cat.append({
            'label': cat_nome, 'data': data,
            'backgroundColor': cor, 'borderColor': cor, 'borderWidth': 1
        })

    # --- 4. RENDER TEMPLATE ---
    return render_template(
        'financeiro/index.html',
        ano=ano,
        versao=versao,
        now=datetime.now(),
        # Cards
        total_receitas_mes=total_receitas_mes,
        num_contribuicoes_mes=num_contribuicoes_mes,
        total_despesas_mes=total_despesas_mes,
        num_despesas_mes=num_despesas_mes,
        saldo_mes_atual=saldo_mes_atual,
        # Gráficos
        chart_labels_meses=chart_labels_meses_nomes,
        chart_datasets_receitas_cc=chart_datasets_receitas_cc,
        chart_datasets_despesas_cc=chart_datasets_despesas_cc,
        chart_datasets_despesas_cat=chart_datasets_despesas_cat
    )

@financeiro_bp.route('/novo', methods=['GET', 'POST'])
@login_required
@financeiro_required
def nova_contribuicao():
    form = ContribuicaoForm()
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
            observacoes=form.observacoes.data,
            centro_custo=form.centro_custo.data
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
            return redirect(url_for('financeiro.lancamentos_receitas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao lançar contribuição: {str(e)}', 'error')

    return render_template('financeiro/registro_receita.html',
                            form=form, ano=ano, versao=versao, Config=Config)

@financeiro_bp.route('/lancamentos_receitas')
@login_required
@financeiro_required
def lancamentos_receitas():
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 30

    filter_form = ContribuicaoFilterForm(request.args, meta={'csrf': False})

    query = Contribuicao.query.join(Membro)

    busca_nome = ""
    tipo_filtro = ""
    status_filtro = ""
    centro_custo_filtro = ""
    data_inicial = None
    data_final = None

    if filter_form.validate():
        busca_nome = filter_form.busca_nome.data
        tipo_filtro = filter_form.tipo_filtro.data
        status_filtro = filter_form.status_filtro.data
        centro_custo_filtro = filter_form.centro_custo_filtro.data
        data_inicial = filter_form.data_inicial.data
        data_final = filter_form.data_final.data

        if busca_nome:
            query = query.filter(Membro.nome_completo.ilike(f'%{busca_nome}%'))
        if tipo_filtro:
            query = query.filter(Contribuicao.tipo == tipo_filtro)
        if centro_custo_filtro:
            query = query.filter(Contribuicao.centro_custo == centro_custo_filtro)
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
    soma_valores = round(float(soma_valores_query), 2) if soma_valores_query else 0.0

    pagination = query.order_by(Contribuicao.data_lanc.desc(), Membro.nome_completo).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    contribuicoes = pagination.items

    cores_map = Config.CORES_CAMPUS.copy()
    if 'Geral' not in cores_map:
        cores_map['Geral'] = '#6c757d'

    return render_template(
        'financeiro/lancamentos_receitas.html',
        contribuicoes=contribuicoes,
        pagination=pagination,
        soma_valores=soma_valores,
        filter_form=filter_form,
        versao=versao,
        ano=ano,
        cores_map=cores_map,
        busca_nome=busca_nome,
        tipo_filtro=tipo_filtro,
        status_filtro=status_filtro,
        centro_custo_filtro=centro_custo_filtro,
        data_inicial=data_inicial,
        data_final=data_final
    )

@financeiro_bp.route('download_receitas_excel')
@login_required
@financeiro_required
def download_receitas_excel():
    busca_nome = request.args.get('busca_nome', '')
    tipo_filtro = request.args.get('tipo_filtro', '')
    status_filtro = request.args.get('status_filtro', '')
    centro_custo_filtro = request.args.get('centro_custo_filtro', '')
    data_inicial_str = request.args.get('data_inicial', '')
    data_final_str = request.args.get('data_final', '')

    query = Contribuicao.query.join(Membro)

    if busca_nome:
        query = query.filter(Membro.nome_completo.ilike(f'%{busca_nome}%'))
    if tipo_filtro:
        query = query.filter(Contribuicao.tipo == tipo_filtro)
    if centro_custo_filtro: # NOVO
        query = query.filter(Contribuicao.centro_custo == centro_custo_filtro)
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
            flash("Formato de Data Inicial inválido.", 'danger')
            return redirect(url_for('financeiro.lancamentos_receitas'))
    if data_final_str:
        try:
            data_final = datetime.strptime(data_final_str, '%Y-%m-%d').date()
            query = query.filter(Contribuicao.data_lanc <= data_final)
        except ValueError:
            flash("Formato de Data Final inválido.", 'danger')
            return redirect(url_for('financeiro.lancamentos_receitas'))

    contribuicoes = query.order_by(Contribuicao.data_lanc.desc(), Membro.nome_completo).all()

    relatorio_dados = []
    for contrib in contribuicoes:
        relatorio_dados.append({
            'Data': contrib.data_lanc.strftime('%d/%m/%Y'),
            'Pessoa': contrib.membro.nome_completo,
            'Valor': contrib.valor,
            'Centro de Custo': contrib.centro_custo,
            'Tipo': contrib.tipo,
            'Forma': contrib.forma,
            'Campus do Membro': contrib.membro.campus,
            'Observações': contrib.observacoes if contrib.observacoes else ''
        })

    df_final = pd.DataFrame(relatorio_dados)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Receitas')
        workbook = writer.book
        worksheet = writer.sheets['Receitas']
        for i, col in enumerate(df_final.columns):
            column_len = max(df_final[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, column_len)
    output.seek(0)
    
    filename_parts = ['receitas']
    if centro_custo_filtro:
        filename_parts.append(f"cc_{centro_custo_filtro}")
    if data_inicial_str:
        filename_parts.append(f"de_{data_inicial_str}")
    if data_final_str:
        filename_parts.append(f"ate_{data_final_str}")

    filename = "_".join(filename_parts) + ".xlsx"

    return send_file(output,
                     download_name=filename,
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@financeiro_bp.route('download_despesas_excel')
@login_required
@financeiro_required
def download_despesas_excel():
    categoria_filtro = request.args.get('categoria_filtro', '')
    centro_custo_filtro = request.args.get('centro_custo_filtro', '')
    recorrencia_filtro = request.args.get('recorrencia_filtro', '')
    data_inicial_str = request.args.get('data_inicial', '')
    data_final_str = request.args.get('data_final', '')

    query = Despesa.query.join(ItemDespesa).join(CategoriaDespesa)

    if categoria_filtro:
        query = query.filter(ItemDespesa.categoria_id == int(categoria_filtro))
    if centro_custo_filtro:
        query = query.filter(Despesa.centro_custo == centro_custo_filtro)
    if recorrencia_filtro:
        query = query.filter(Despesa.recorrencia == recorrencia_filtro)
    if data_inicial_str:
        try:
            data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d').date()
            query = query.filter(Despesa.data_lanc >= data_inicial)
        except ValueError:
            flash("Formato de Data Inicial inválido.", 'danger')
            return redirect(url_for('financeiro.lancamentos_despesas'))
    if data_final_str:
        try:
            data_final = datetime.strptime(data_final_str, '%Y-%m-%d').date()
            query = query.filter(Despesa.data_lanc <= data_final)
        except ValueError:
            flash("Formato de Data Final inválido.", 'danger')
            return redirect(url_for('financeiro.lancamentos_despesas'))

    despesas = query.order_by(Despesa.data_lanc.desc(), CategoriaDespesa.nome, ItemDespesa.nome).all()

    relatorio_dados = []
    for despesa in despesas:
        relatorio_dados.append({
            'Data': despesa.data_lanc.strftime('%d/%m/%Y'),
            'Categoria': despesa.item.categoria.nome,
            'Item': despesa.item.nome,
            'Centro de Custo': despesa.centro_custo,
            'Recorrência': despesa.recorrencia,
            'Valor': despesa.valor,
            'Observações': despesa.observacoes if despesa.observacoes else ''
        })

    df_final = pd.DataFrame(relatorio_dados)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Despesas')
        workbook = writer.book
        worksheet = writer.sheets['Despesas']
        for i, col in enumerate(df_final.columns):
            max_len = max(df_final[col].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.set_column(i, i, max_len)
    output.seek(0)
    
    filename_parts = ['despesas']
    if categoria_filtro:
        filename_parts.append(f"cat_{categoria_filtro}")
    if centro_custo_filtro:
        filename_parts.append(f"cc_{centro_custo_filtro}")
    if data_inicial_str:
        filename_parts.append(f"de_{data_inicial_str}")
    if data_final_str:
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
            return redirect(url_for('financeiro.lancamentos_receitas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar contribuição: {str(e)}', 'danger')

    return render_template('financeiro/registro_receita.html',
                            form=form,
                            ano=ano,
                            versao=versao,
                            Config=Config)

@financeiro_bp.route('/buscar_membros_financeiro')
@login_required
@financeiro_required
def buscar_membros_financeiro():
    search_term = request.args.get('term', '')
    results = []
    membros_ativos_query = Membro.query.filter(
        Membro.nome_completo.ilike(f'%{search_term}%'), 
        Membro.ativo==True,
        Membro.id != Config.ID_OFERTA_ANONIMA 
    )
    
    membros_ativos = membros_ativos_query.order_by(Membro.nome_completo).limit(50).all()
    
    for membro in membros_ativos:
        results.append({
            'id': membro.id, 
            'text': membro.nome_completo,
            'campus': membro.campus
        })

    membro_anonimo = Membro.query.get(Config.ID_OFERTA_ANONIMA)
    if membro_anonimo:
        anonimo_full_name = membro_anonimo.nome_completo.lower()
        if not search_term or search_term.lower() in anonimo_full_name:
            results.insert(0, {
                'id': membro_anonimo.id,
                'text': membro_anonimo.nome_completo,
                'campus': membro_anonimo.campus
            })

    return jsonify(items=results)

@financeiro_bp.route('/configuracao', methods=['GET', 'POST'])
@login_required
@financeiro_required
def configuracao_financeira():
    form_categoria = CategoriaDespesaForm(prefix='cat')
    form_item = ItemDespesaForm(prefix='item')

    if request.method == 'POST':
        if 'submit_categoria' in request.form and form_categoria.validate_on_submit():
            try:
                nova_cat = CategoriaDespesa(
                    nome=form_categoria.nome.data,
                    codigo=form_categoria.codigo.data 
                )
                db.session.add(nova_cat)
                db.session.commit()
                flash('Nova categoria de despesa criada com sucesso!', 'success')
                return redirect(url_for('financeiro.configuracao_financeira'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao criar categoria: {str(e)}', 'danger')

        elif 'submit_item' in request.form and form_item.validate_on_submit():
            try:
                novo_item = ItemDespesa(
                    categoria_id=form_item.categoria_id.data,
                    nome=form_item.nome.data,
                    codigo=form_item.codigo.data,
                    tipo_fixa_variavel=form_item.tipo_fixa_variavel.data
                )
                db.session.add(novo_item)
                db.session.commit()
                flash('Novo item de despesa criado com sucesso!', 'success')
                return redirect(url_for('financeiro.configuracao_financeira'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao criar item: {str(e)}', 'danger')
    
    categorias = CategoriaDespesa.query.order_by(CategoriaDespesa.codigo, CategoriaDespesa.nome).all()
    itens = ItemDespesa.query.join(CategoriaDespesa).order_by(CategoriaDespesa.codigo, ItemDespesa.codigo, ItemDespesa.nome).all()
    
    return render_template(
        'financeiro/configuracao.html',
        ano=ano,
        versao=versao,
        form_categoria=form_categoria,
        form_item=form_item,
        categorias=categorias,
        itens=itens
    )

@financeiro_bp.route('/nova_despesa', methods=['GET', 'POST'])
@login_required
@financeiro_required
def nova_despesa():
    form = DespesaForm()

    if form.validate_on_submit():
        desp = Despesa(
            item_id=form.item_id.data,
            valor=form.valor.data,
            data_lanc=form.data_lanc.data,
            observacoes=form.observacoes.data,
            centro_custo=form.centro_custo.data,
            recorrencia=form.recorrencia.data
        )
        try:
            db.session.add(desp)
            db.session.commit()
            flash('Despesa lançada com sucesso!', 'success')
            return redirect(url_for('financeiro.lancamentos_despesas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao lançar despesa: {str(e)}', 'error')

    return render_template('financeiro/registro_despesa.html',
                            form=form, ano=ano, versao=versao,
                            title="Lançamento de Despesa")

@financeiro_bp.route('/editar_despesa/<int:id>', methods=['GET', 'POST'])
@login_required
@financeiro_required
def editar_despesa(id):
    despesa = Despesa.query.get_or_404(id)
    form = DespesaForm(obj=despesa)

    if form.validate_on_submit():
        form.populate_obj(despesa)
        try:
            db.session.commit()
            flash(f'Despesa atualizada com sucesso!', 'success')
            return redirect(url_for('financeiro.lancamentos_despesas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar despesa: {str(e)}', 'danger')

    return render_template('financeiro/registro_despesa.html',
                            form=form, ano=ano, versao=versao,
                            title="Editar Despesa")

@financeiro_bp.route('/lancamentos_despesas')
@login_required
@financeiro_required
def lancamentos_despesas():
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 30
    filter_form = DespesaFilterForm(request.args, meta={'csrf': False})
    
    query = Despesa.query.join(ItemDespesa).join(CategoriaDespesa)

    categoria_filtro = ""
    item_filtro = ""
    recorrencia_filtro = ""
    centro_custo_filtro = ""
    data_inicial = None
    data_final = None

    if filter_form.validate():
        categoria_filtro = filter_form.categoria_filtro.data
        item_filtro = filter_form.item_filtro.data
        recorrencia_filtro = filter_form.recorrencia_filtro.data
        centro_custo_filtro = filter_form.centro_custo_filtro.data
        data_inicial = filter_form.data_inicial.data
        data_final = filter_form.data_final.data

        if categoria_filtro:
            query = query.filter(ItemDespesa.categoria_id == categoria_filtro)
        if item_filtro:
            query = query.filter(Despesa.item_id == item_filtro)
        if recorrencia_filtro:
            query = query.filter(Despesa.recorrencia == recorrencia_filtro)
        if centro_custo_filtro:
            query = query.filter(Despesa.centro_custo == centro_custo_filtro)
        if data_inicial:
            query = query.filter(Despesa.data_lanc >= data_inicial)
        if data_final:
            query = query.filter(Despesa.data_lanc <= data_final)
    else:
        for field_name, errors in filter_form.errors.items():
            for error in errors:
                if field_name != 'csrf_token':
                    field_obj = getattr(filter_form, field_name, None)
                    field_label = field_obj.label.text if field_obj and hasattr(field_obj, 'label') else field_name
                    flash(f"Erro no filtro '{field_label}': {error}", 'danger')

    soma_valores_query = query.with_entities(func.sum(Despesa.valor)).scalar()
    soma_valores = round(float(soma_valores_query), 2) if soma_valores_query else 0.0

    pagination = query.order_by(Despesa.data_lanc.desc(), CategoriaDespesa.nome, ItemDespesa.nome).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    despesas = pagination.items

    cores_map = Config.CORES_CAMPUS.copy()
    if 'Geral' not in cores_map:
        cores_map['Geral'] = '#6c757d'

    return render_template(
        'financeiro/lancamentos_despesas.html',
        despesas=despesas,
        pagination=pagination,
        soma_valores=soma_valores,
        filter_form=filter_form,
        versao=versao,
        ano=ano,
        cores_map=cores_map,
        categoria_filtro=categoria_filtro,
        item_filtro=item_filtro,
        recorrencia_filtro=recorrencia_filtro,
        centro_custo_filtro=centro_custo_filtro,
        data_inicial=data_inicial,
        data_final=data_final
    )

@financeiro_bp.route('/delete_contribuicao/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_contribuicao(id):
    contribuicao = Contribuicao.query.get_or_404(id)

    nome_membro = contribuicao.membro.nome_completo
    valor_contribuicao = contribuicao.valor
    
    db.session.delete(contribuicao)
    
    try:
        db.session.commit()
        flash(f'Contribuição de {contribuicao.membro.nome_completo} excluída com sucesso!', 'success')
        
        registrar_evento_jornada(
            tipo_acao='CONTRIBUICAO_EXCLUIDA',
            descricao_detalhada=f'Contribuição de {nome_membro} (R$ {valor_contribuicao}) excluída.', 
            usuario_executor=current_user
        )
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro interno ao tentar excluir a contribuição. Tente novamente ou contate o suporte. Detalhe: {str(e)}', 'danger') 

    return redirect(url_for('financeiro.lancamentos_receitas'))

@financeiro_bp.route('/delete_despesa/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_despesa(id):
    despesa = Despesa.query.get_or_404(id)
    
    nome_item = despesa.item.nome
    valor_despesa = despesa.valor
    
    db.session.delete(despesa)
    
    try:
        db.session.commit()
        flash(f'Despesa "{nome_item}" no valor de R$ {valor_despesa} excluída com sucesso!', 'success')
        
        registrar_evento_jornada(
            tipo_acao='DESPESA_EXCLUIDA',
            descricao_detalhada=f'Despesa de {nome_item} (R$ {valor_despesa}) excluída.',
            usuario_executor=current_user
        )
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir a despesa: {str(e)}', 'danger')

    return redirect(url_for('financeiro.lancamentos_despesas'))
