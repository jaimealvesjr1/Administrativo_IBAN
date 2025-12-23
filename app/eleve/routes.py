from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from app.extensions import db
from . import eleve_bp
from app.decorators import admin_required, leader_required
from .models import PilulaDiaria, QuizQuestion, QuizOption, RegistroPresenca, IndiceProgresso, PontuacaoAnual
from .forms import PilulaDiariaForm, RegistroPresencaDiariaForm
from app.eleve.utils import calcular_monthly_pg_final, get_month_start_end
from sqlalchemy import func
from app.membresia.models import Membro
from app.grupos.models import Setor 


def save_quiz_from_form(pilula, form):
    """
    Processa o formulário com 3 perguntas simples, salva no formato de 
    Questão/Opções, recalculando pontos.
    """
    # 1. Limpa questões antigas
    pilula.questoes_quiz.delete() 
    db.session.flush()
    
    # Estrutura de todas as perguntas
    perguntas_quiz = [
        {'pergunta': form.quiz_p1, 'alt_a': form.alt_a1, 'alt_b': form.alt_b1, 'alt_c': form.alt_c1, 'alt_d': form.alt_d1, 'correta': form.quiz_c1},
        {'pergunta': form.quiz_p2, 'alt_a': form.alt_a2, 'alt_b': form.alt_b2, 'alt_c': form.alt_c2, 'alt_d': form.alt_d2, 'correta': form.quiz_c2},
        {'pergunta': form.quiz_p3, 'alt_a': form.alt_a3, 'alt_b': form.alt_b3, 'alt_c': form.alt_c3, 'alt_d': form.alt_d3, 'correta': form.quiz_c3},
    ]

    perguntas_validas = 0
    for q_data in perguntas_quiz:
        if q_data['pergunta'].data and q_data['correta'].data:
            # 1.1. Cria a Questão
            questao = QuizQuestion(pilula=pilula, texto=q_data['pergunta'].data)
            db.session.add(questao)
            db.session.flush() # Para obter o ID
            
            perguntas_validas += 1

            alternativas = [
                {'key': 'A', 'texto': q_data['alt_a'].data},
                {'key': 'B', 'texto': q_data['alt_b'].data},
                {'key': 'C', 'texto': q_data['alt_c'].data},
                {'key': 'D', 'texto': q_data['alt_d'].data},
            ]
            
            # 1.2. Adiciona as 4 Opções
            for alt in alternativas:
                opcao = QuizOption(
                    questao=questao,
                    texto=alt['texto'],
                    correta=(alt['key'] == q_data['correta'].data)
                )
                db.session.add(opcao)
    
    # 2. Cálculo dos Pontos Base (PG)
    pontos_base = 0
    if pilula.link_video:
        pontos_base += 2
    if pilula.descricao_tarefa:
        pontos_base += 2
        
    # Quiz: 6 pontos se houver pelo menos 1 pergunta válida (se quiz_p1 foi preenchida)
    if perguntas_validas > 0:
        pontos_base += 6 

    pilula.pontos_base = pontos_base
# =======================================================================
# DADOS MOCK (SIMULAÇÃO) - REMOVA APÓS INTEGRAR COM OS MODELOS DO SQLAlchemy
# =======================================================================
class MockMembro:
    def __init__(self, id, nome_completo):
        self.id = id
        self.nome_completo = nome_completo
        self.primeiro_nome = nome_completo.split(' ')[0]

class MockPontuacao:
    def __init__(self, membro, pj, pcr_max, slot=False, num_class=0, pcr_acum=0):
        self.membro_id = membro.id
        self.membro = membro
        self.pj_total = pj
        self.pcr_max = pcr_max
        self.slot_classificacao = slot
        self.num_classificacoes = num_class
        self.pcr_acumulado = pcr_acum

class MockSetor:
    def __init__(self, id, nome):
        self.id = id
        self.nome = nome

# Substitua com dados reais do DB (db.session.get(Membro, current_user.membro_id))
mock_membro_logado = MockMembro(id=10, nome_completo="João da Silva")
mock_pontuacao_logado = MockPontuacao(
    membro=mock_membro_logado, 
    pj=50, 
    pcr_max=720, 
    slot=True, 
    num_class=5, 
    pcr_acum=3100
)

mock_ranking = [
    MockPontuacao(MockMembro(id=1, nome_completo="Ana Carolina"), 70, 850),
    MockPontuacao(MockMembro(id=2, nome_completo="Lucas Pereira"), 65, 800),
    MockPontuacao(MockMembro(id=3, nome_completo="Mariana Castro"), 60, 780),
    mock_pontuacao_logado,
    MockPontuacao(MockMembro(id=11, nome_completo="Carlos Lima"), 45, 690),
    MockPontuacao(MockMembro(id=12, nome_completo="Sofia Nunes"), 40, 650),
]

mock_indices_roda = {
    'Saúde / Lazer': 90, 'Família': 75, 'Finanças': 80,
    'Santidade': 85, 'Tempo de Leitura': 60, 'Tempo de Oração': 70,
    'Culto': 95, 'Pastoreio de Líderes': 40, 'Célula': 65,
    'Carreira': 70, 'Aperfeiçoamento': 55, 'Planejamento / Sonho': 80
}
mock_setores = [
    MockSetor(1, 'Setor Alpha'),
    MockSetor(2, 'Setor Beta'),
    MockSetor(3, 'Setor Gama'),
]
# =======================================================================

@eleve_bp.route('/painel', methods=['GET'])
@login_required 
@admin_required
def painel():
    """Painel de Gestão do Sistema ELEVE (Admin)."""
    ano_atual = datetime.now().year

    # 1. Buscas Reais do DB (Substituindo Mocks)
    try:
        # Total de Pílulas Cadastradas
        total_pilulas = PilulaDiaria.query.count()

        # Total de Discípulos com Slot Anual (SC=True)
        total_classificados = PontuacaoAnual.query.filter_by(
            slot_classificacao=True, 
            ano=ano_atual
        ).count()
        
        # Lista de Setores para o formulário de Ranking Mensal
        # Assumindo que o modelo Setor está disponível e importado
        setores = Setor.query.order_by(Setor.nome).all()

    except Exception as e:
        # Lidar com erro de DB se as migrações não estiverem rodadas (temporário)
        print(f"Erro ao acessar o DB no Painel ELEVE: {e}")
        total_pilulas = 'Erro DB'
        total_classificados = 'Erro DB'
        setores = []

    return render_template(
        'eleve/painel.html',
        total_pilulas=total_pilulas,
        total_classificados=total_classificados,
        setores=setores,
        # Variáveis para a simulação de formulário no template:
        now=datetime.now,
        ano=ano_atual
    )

@eleve_bp.route('/membros/search', methods=['GET'])
@login_required 
def search_membros():
    """Endpoint AJAX para buscar membros para o Select2."""
    query = request.args.get('q', '')
    if len(query) < 3:
        return jsonify({'results': []})
        
    # Busca por nome completo ou por parte do nome (ilike)
    membros = Membro.query.filter(Membro.nome_completo.ilike(f'%{query}%')).limit(10).all()
    
    # É crucial que o 'id' seja o ID do Membro e 'text' seja o nome completo.
    results = [{'id': m.id, 'text': m.nome_completo} for m in membros]
    return jsonify({'results': results})

@eleve_bp.route('/marcar_presenca_diaria', methods=['GET', 'POST'])
@login_required 
def marcar_presenca_diaria():
    """Rota para registrar Presença em Culto, PG e Serviço de Departamento."""
    form = RegistroPresencaDiariaForm()
    
    if form.validate_on_submit():
        # O Select2 envia o nome do membro de volta no campo 'membro_nome'.
        # O ID real do membro é enviado como um campo oculto no JS.
        # Precisamos de um pequeno ajuste: usar o ID do membro em vez do nome no submit.
        membro_id = request.form.get('membro_id_selecionado') # Obtido do campo Select2 via JS
        
        try:
            membro = Membro.query.get(int(membro_id))
        except (ValueError, TypeError):
            membro = None

        if not membro:
            flash(f'Discípulo não encontrado. Use o campo de busca corretamente.', 'danger')
            return render_template('eleve/form_presenca_diaria.html', form=form, title='Registro de Presença')

        data_presenca = form.data.data
        pontos_totais = 0
        mensagens = []

        # Dicionário de atividades e pontos
        atividades = {
            'Culto': {'check': form.culto.data, 'pontos': 5},
            'PG': {'check': form.pg.data, 'pontos': 5},
            'Servico': {'check': form.servico.data, 'pontos': 3}
        }
        
        # Processar e Registrar no DB
        for tipo, dados in atividades.items():
            if dados['check']:
                # Verifica se o registro já existe para evitar duplicidade (UniqueConstraint)
                registro = RegistroPresenca.query.filter_by(
                    membro_id=membro.id, 
                    data=data_presenca, 
                    tipo=tipo
                ).first()
                
                if not registro:
                    pontos_totais += dados['pontos']
                    db.session.add(RegistroPresenca(
                        membro_id=membro.id, 
                        data=data_presenca, 
                        tipo=tipo, 
                        pontuacao_ganha=dados['pontos']
                    ))
                    mensagens.append(f'{tipo} ({dados["pontos"]} PG)')
        
        if pontos_totais > 0:
            db.session.commit()
            flash(f'Presenças de {membro.nome_completo} registradas com sucesso! Total: {pontos_totais} PG. Registros: {", ".join(mensagens)}', 'success')
        else:
            flash(f'Nenhuma nova presença para {membro.nome_completo} foi registrada na data {data_presenca}. Verifique se já estão marcadas.', 'warning')
            
        return redirect(url_for('eleve.marcar_presenca_diaria'))

    return render_template('eleve/form_presenca_diaria.html', form=form, title='Registro de Presença')

@eleve_bp.route('/minha_jornada', methods=['GET'])
@login_required # Garante que o usuário esteja logado
def minha_jornada():
    """Visão do Discípulo sobre sua própria Jornada ELEVE."""
    # Substitua com dados reais do DB (relacionados ao current_user.membro_id):
    # membro = Membro.query.get(current_user.membro_id)
    # pontuacao_anual = PontuacaoAnual.query.filter_by(membro_id=membro.id, ano=datetime.now().year).first()
    # indices_roda = {ip.subcategoria_rv: ip.indice for ip in IndiceProgresso.query.filter_by(membro_id=membro.id, ano=datetime.now().year).all()}
    # ranking_top = PontuacaoAnual.query.order_by(PontuacaoAnual.pj_total.desc(), PontuacaoAnual.pcr_max.desc()).limit(10).all()

    # Usando mocks:
    membro = mock_membro_logado
    pontuacao_anual = mock_pontuacao_logado
    indices_roda = mock_indices_roda
    ranking_top = mock_ranking

    return render_template(
        'eleve/minha_jornada.html',
        membro=membro,
        pontuacao_anual=pontuacao_anual,
        indices_roda=indices_roda,
        ranking_top=ranking_top,
        ano=datetime.now().year
    )

@eleve_bp.route('/pilulas', methods=['GET'])
@login_required 
@admin_required
def gerenciar_pilulas():
    """Rota para listar Pílulas Diárias."""
    # Obtém todas as pílulas para a listagem
    pilulas = PilulaDiaria.query.order_by(PilulaDiaria.data_publicacao.desc()).all()
    # O formulário é criado aqui apenas para o caso de você querer um modal no futuro
    form = PilulaDiariaForm() 
    
    return render_template(
        'eleve/listagem_pilulas.html', 
        form=form,
        pilulas=pilulas,
        title='Gerenciar Pílulas Diárias'
    )

@eleve_bp.route('/pilulas/cadastrar', methods=['GET', 'POST'])
@login_required 
@admin_required
def cadastrar_pilula():
    form = PilulaDiariaForm()
    form.pilula_id = None  

    if form.validate_on_submit():
        pilula = PilulaDiaria(
            titulo=form.titulo.data,
            data_publicacao=form.data_publicacao.data,
            subcategoria_rv=form.subcategoria_rv.data,
            link_video=form.link_video.data,
            descricao_tarefa=form.descricao_tarefa.data,
            pontos_base=0
        )
        db.session.add(pilula)
        db.session.flush() # Salva a Pilula para obter o ID
        
        save_quiz_from_form(pilula, form) # Salva Quiz e recalcula pontos
        
        db.session.commit()
        flash(f'Pílula "{pilula.titulo}" cadastrada para {pilula.data_publicacao.strftime("%d/%m/%Y")} com sucesso! Pontuação máxima: {pilula.pontos_base} PG.', 'success')
        return redirect(url_for('eleve.gerenciar_pilulas'))

    return render_template('eleve/form_pilula.html', form=form, title='Cadastrar Nova Pílula')


@eleve_bp.route('/pilulas/editar/<int:pilula_id>', methods=['GET', 'POST'])
@login_required 
@admin_required
def editar_pilula(pilula_id):
    pilula = PilulaDiaria.query.get_or_404(pilula_id)
    form = PilulaDiariaForm(obj=pilula)

    form.pilula_id = pilula.id

    if request.method == 'GET':
        questoes = pilula.questoes_quiz.order_by(QuizQuestion.id).all()
        
        for i, questao in enumerate(questoes):
            if i >= 3: # Limita a 3 perguntas, conforme o form
                break

            # Determina qual set de campos no formulário usar (p1, p2 ou p3)
            q_index = i + 1
            
            # 1. Carrega o texto da pergunta
            getattr(form, f'quiz_p{q_index}').data = questao.texto
            
            opcoes = sorted(questao.opcoes.all(), key=lambda x: x.id) # Ordena pelo ID para consistência

            # 2. Carrega as 4 opções e encontra a correta
            alternativas_map = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}
            
            for j, opcao in enumerate(opcoes):
                if j >= 4: break
                
                letra_alt = alternativas_map.get(j)
                
                if letra_alt == 'A':
                    getattr(form, f'alt_a{q_index}').data = opcao.texto
                elif letra_alt == 'B':
                    getattr(form, f'alt_b{q_index}').data = opcao.texto
                elif letra_alt == 'C':
                    getattr(form, f'alt_c{q_index}').data = opcao.texto
                elif letra_alt == 'D':
                    getattr(form, f'alt_d{q_index}').data = opcao.texto
                    
                if opcao.correta:
                    # Seta o SelectField correto
                    getattr(form, f'quiz_c{q_index}').data = letra_alt
            
    if form.validate_on_submit():
        # Atualiza dados da Pilula
        form.populate_obj(pilula)
        
        save_quiz_from_form(pilula, form) # Limpa, salva Quiz e recalcula pontos
        
        db.session.commit()
        flash(f'Pílula "{pilula.titulo}" ({pilula.data_publicacao.strftime("%d/%m/%Y")}) atualizada com sucesso! Pontuação máxima: {pilula.pontos_base} PG.', 'success')
        return redirect(url_for('eleve.gerenciar_pilulas'))

    return render_template('eleve/form_pilula.html', form=form, title=f'Editar Pílula ID {pilula.id}')

@eleve_bp.route('/pilulas/excluir/<int:pilula_id>', methods=['POST'])
@login_required 
@admin_required
def excluir_pilula(pilula_id):
    """Rota para excluir uma Pílula Diária."""
    pilula = PilulaDiaria.query.get_or_404(pilula_id)
    
    db.session.delete(pilula)
    db.session.commit()
    flash(f'Pílula "{pilula.titulo}" excluída com sucesso.', 'info')
    return redirect(url_for('eleve.gerenciar_pilulas'))

@eleve_bp.route('/ranking_anual', methods=['GET'])
@login_required 
def ranking_anual_completo():
    """Rota para exibir o Ranking Anual Geral completo (P7 do cronograma)."""
    
    ano_atual = datetime.now().year
    
    # Busca todas as pontuações anuais para o ano atual que tenham Slot Conquistado (SC=True).
    # Ordena estritamente pelos 4 primeiros critérios de desempate, conforme a Estrutura ELEVE.pdf.
    ranking_completo = PontuacaoAnual.query.filter_by(ano=ano_atual, slot_classificacao=True).order_by(
        PontuacaoAnual.pj_total.desc(),        # 1. PJ Total (maior)
        PontuacaoAnual.pcr_max.desc(),         # 2. PCr Máximo (pico de performance)
        PontuacaoAnual.num_classificacoes.desc(), # 3. Nº de Classificações
        PontuacaoAnual.pcr_acumulado.desc()    # 4. PCr Acumulado (desempate fino)
    ).all()
    
    return render_template(
        'eleve/ranking_anual_completo.html',
        ranking_completo=ranking_completo,
        ano=ano_atual,
        title='Ranking Anual - Jornada ELEVE'
    )

@eleve_bp.route('/pilulas/acessar/<int:pilula_id>', methods=['GET'])
@login_required 
def acessar_pilula(pilula_id):
    """
    Rota inicial para o discípulo consumir a Pílula. 
    Contém a lógica de prazo (Req 3).
    """
    pilula = PilulaDiaria.query.get_or_404(pilula_id)
    hoje = date.today()
    membro = current_user.membro

    # REQ 3: Lógica de Prazo
    if pilula.data_publicacao != hoje:
        if pilula.data_publicacao < hoje:
            flash(f'Esta Pílula expirou e só poderia ser acessada em {pilula.data_publicacao.strftime("%d/%m/%Y")}.', 'danger')
        else:
            flash(f'Esta Pílula estará disponível apenas em {pilula.data_publicacao.strftime("%d/%m/%Y")}.', 'warning')
        return redirect(url_for('membresia.perfil', id=membro.id))

    # Verifica se já concluiu (evita refazer)
    registro_existente = RegistroPresenca.query.filter_by(
        membro_id=membro.id, 
        data=hoje, 
        tipo='Pilula'
    ).first()
    if registro_existente:
       flash('Você já concluiu esta Pílula hoje.', 'info')
       return redirect(url_for('membresia.perfil', id=membro.id))
       
    questoes_json = []
    
    questoes = pilula.questoes_quiz.all()
    
    for q in questoes:
        opcoes_list = []
        opcoes_db = sorted(q.opcoes.all(), key=lambda o: o.id) 
        
        letras = ['A', 'B', 'C', 'D']
        
        for i, o in enumerate(opcoes_db):
            if i >= 4: break
            opcoes_list.append({
                'id': o.id, 
                'letra': letras[i],
                'texto': o.texto
            })
            
        questoes_json.append({
            'id': q.id,
            'texto': q.texto,
            'opcoes': opcoes_list
        })
    
    return render_template(
        'eleve/visualizar_pilula.html',
        pilula=pilula,
        membro=membro,
        questoes=questoes_json
    )

@eleve_bp.route('/pilulas/concluir/<int:pilula_id>', methods=['POST'])
@login_required
def concluir_pilula(pilula_id):
    """Processa o resultado do Quiz e registra a conclusão da Pílula (Lógica P3)."""
    pilula = PilulaDiaria.query.get_or_404(pilula_id)
    membro = current_user.membro
    hoje = date.today()
    data = request.get_json()
    quiz_respostas = data.get('quiz_respostas', [])

    try:
        data = request.get_json(silent=True) or {}
        quiz_respostas = data.get('quiz_respostas', [])
    except Exception:
        return jsonify({'success': False, 'message': 'Erro na leitura do JSON da requisição.'}), 400
    
    # 1. Validação de Prazo e Duplicidade (Segurança no Backend)
    if pilula.data_publicacao != hoje or RegistroPresenca.query.filter_by(membro_id=membro.id, data=hoje, tipo='Pilula').first():
        return jsonify({'success': False, 'message': 'Operação inválida (prazo/duplicidade).'}), 400

    # 2. Cálculo dos Pontos Ganhos
    pontos_ganhos = 0
    pontos_video = 2 if pilula.link_video else 0
    pontos_tarefa = 2 if pilula.descricao_tarefa else 0
    pontos_quiz = 0
    
    # Lógica do Quiz (6 PG)
    if pilula.questoes_quiz.count() > 0:
        respostas_corretas = 0
        total_questoes = pilula.questoes_quiz.count()
        
        # Verifica as respostas no DB
        for resp in quiz_respostas:
            # Opção correta para a questão
            opcao_correta = QuizOption.query.filter_by(
                questao_id=resp['questao_id'], 
                correta=True
            ).first()

            if opcao_correta and opcao_correta.id == resp['opcao_selecionada_id']:
                respostas_corretas += 1

        # Regra de Pontuação Sugerida: Acertar no mínimo 2 de 3 questões.
        if respostas_corretas >= 2 or (total_questoes == 1 and respostas_corretas == 1):
            pontos_quiz = 6
        
    pontos_ganhos = pontos_video + pontos_tarefa + pontos_quiz
    
    # 3. Registro de Presença e IP
    registro = RegistroPresenca(
        membro=membro, data=hoje, tipo='Pilula', pilula=pilula, pontuacao_ganha=pontos_ganhos
    )
    db.session.add(registro)

    ip_ganhos = 0
    if pontos_ganhos > 0: # Se ganhou qualquer pontuação, atribui os 10 IP
        ip_ganhos = 10
        indice_progresso = IndiceProgresso.query.filter_by(
            membro=membro, subcategoria_rv=pilula.subcategoria_rv, ano=hoje.year
        ).first()

        if not indice_progresso:
            indice_progresso = IndiceProgresso(membro=membro, subcategoria_rv=pilula.subcategoria_rv, ano=hoje.year, indice=0)
            db.session.add(indice_progresso)
        
        indice_progresso.indice = func.min(100, indice_progresso.indice + ip_ganhos)
        
    db.session.commit()
    
    return jsonify({
        'success': True,
        'pontos_ganhos': pontos_ganhos,
        'ip_ganhos': ip_ganhos,
        'message': f'Pílula concluída com sucesso! Pontos ganhos: {pontos_ganhos}.'
    })

@eleve_bp.route('/ranking_mensal/<int:setor_id>/<int:mes>/<int:ano>', methods=['GET', 'POST'])
@login_required 
def ver_ranking_mensal(setor_id, mes, ano):
    """
    Rota para calcular Pontos Finais (PG x Multiplicador), classificar o Top 20% 
    e exibir o ranking de um Setor para um dado mês/ano.
    """
    setor = Setor.query.get_or_404(setor_id)
    
    # 1. Obter membros pertencentes ao PG deste Setor (participantes, facilitador, anfitrião)
    # Lista de IDs de membros no setor
    membros_no_setor = set()
    for pg in setor.pequenos_grupos:
        membros_no_setor.update([m.id for m in pg.membros_completos])
    
    membros = Membro.query.filter(Membro.id.in_(membros_no_setor)).all()

    # 2. Calcular o PG Final para cada membro
    ranking_data = []
    
    for membro in membros:
        pg_final = calcular_monthly_pg_final(membro.id, ano, mes)
        
        ranking_data.append({
            'membro': membro,
            'pg_final': pg_final
        })

    # 3. Classificar os membros (decrescente por PG Final)
    ranking_data.sort(key=lambda x: x['pg_final'], reverse=True)
    
    # 4. Determinar o Top 20% (para P6)
    total_membros = len(ranking_data)
    num_classificados = max(1, int(total_membros * 0.20)) # Pelo menos 1
    
    # 5. Exibir o Ranking
    context = {
        'setor': setor,
        'mes': mes,
        'ano': ano,
        'ranking': ranking_data,
        'num_classificados': num_classificados
    }

    # Se for POST (processar a etapa)
    if request.method == 'POST' and current_user.is_admin: # Apenas admins podem processar
        # Lógica de processamento (P6) a ser implementada no próximo passo
        # Por enquanto, apenas exibe a lista.
        flash("Funcionalidade de processamento (salvamento de PJ/SC) desativada. Exibindo apenas a simulação do ranking.", 'warning')

    return render_template('eleve/ranking_mensal.html', **context)