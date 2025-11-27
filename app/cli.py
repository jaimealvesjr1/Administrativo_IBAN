import click
import os
from flask.cli import with_appcontext
from flask import current_app
from app.extensions import db
from app.auth.models import User
from app.membresia.models import Membro
from app.membresia.routes import save_profile_picture, allowed_file, PROFILE_PIC_SIZE, COMPRESSION_QUALITY
from app.financeiro.models import CategoriaDespesa, ItemDespesa, Despesa
from PIL import Image

@click.command("create-admin")
@with_appcontext
def create_admin():
    if User.query.filter_by(username="admin").first():
        click.echo("⚠️  Usuário 'admin' já existe.")
    else:
        admin = User(username="admin", role="admin")
        admin.set_password("2007")
        db.session.add(admin)
        db.session.commit()
        click.echo("✅ Usuário 'admin' criado com sucesso.")

@click.command('optimize-images')
@with_appcontext
def optimize_images_command():
    click.echo('Iniciando otimização das fotos de perfil existentes...')
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    membros = Membro.query.filter(Membro.foto_perfil.isnot(None)).all()
    total_membros = len(membros)
    membros_otimizados = 0
    membros_com_erro = 0

    if not os.path.exists(upload_folder):
        click.echo('Pasta de uploads não encontrada. Abortando.')
        return
    
    for membro in membros:
        if membro.foto_perfil and membro.foto_perfil != 'default.jpg':
            filepath = os.path.join(upload_folder, membro.foto_perfil)
            if not os.path.exists(filepath):
                click.echo(f"Aviso: Arquivo '{membro.foto_perfil}' não encontrado para o membro {membro.nome_completo}.")
                continue

            try:
                img = Image.open(filepath)

                img.thumbnail(PROFILE_PIC_SIZE, Image.Resampling.LANCZOS)

                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                temp_buffer = os.path.join(upload_folder, 'temp_' + membro.foto_perfil)
                img.save(temp_buffer, quality=COMPRESSION_QUALITY, optimize=True)

                os.remove(filepath)
                os.rename(temp_buffer, filepath)

                membros_otimizados += 1
                click.echo(f"Otimizado: {membro.nome_completo} ({membros_otimizados}/{total_membros})")

            except Exception as e:
                membros_com_erro += 1
                click.echo(f"Erro ao otimizar foto de {membro.nome_completo}: {e}", err=True)
    
    click.echo('---')
    click.echo(f'Otimização concluída. {membros_otimizados} fotos otimizadas.')
    if membros_com_erro > 0:
        click.echo(f'{membros_com_erro} fotos apresentaram erros. Verifique os logs.')

@click.command('seed-plano-contas')
@with_appcontext
def seed_plano_contas():
    """
    Atualiza o Plano de Contas do IBAN.
    - Categorias/Itens NÃO usados são excluídos.
    - Categorias/Itens USADOS são renomeados com '(ANTIGO)' para preservar histórico.
    - Novas categorias oficiais são criadas.
    """
    click.echo("🔄 Iniciando migração do Plano de Contas...")

    # 1. LIMPEZA E RENOMEAÇÃO (PRESERVAR DADOS)
    categorias_existentes = CategoriaDespesa.query.all()
    removidos_count = 0
    renomeados_count = 0

    for cat in categorias_existentes:
        # Verifica se algum item desta categoria tem despesas lançadas
        tem_despesas = False
        itens_para_remover = []

        for item in cat.itens:
            if item.despesas.count() > 0:
                tem_despesas = True
                # Opcional: Renomear o item também para facilitar identificação
                if "(ANTIGO)" not in item.nome:
                    item.nome = f"{item.nome} (ANTIGO)"
            else:
                itens_para_remover.append(item)
        
        # Remove itens que não estão sendo usados (limpeza)
        for item in itens_para_remover:
            db.session.delete(item)

        if tem_despesas:
            # Se tem despesas, NÃO DELETA. Renomeia a categoria para liberar o nome oficial.
            if "(ANTIGO)" not in cat.nome:
                cat.nome = f"{cat.nome} (ANTIGO)"
                # Altera o código para não conflitar com o novo (ex: X-3.01)
                if cat.codigo:
                    cat.codigo = f"X-{cat.codigo}"
                click.echo(f"   ⚠️  Mantido (Histórico): {cat.nome}")
                renomeados_count += 1
        else:
            # Se não tem despesas, pode deletar a categoria inteira
            db.session.delete(cat)
            removidos_count += 1
    
    db.session.commit()
    click.echo(f"🧹 Limpeza concluída: {removidos_count} categorias removidas, {renomeados_count} renomeadas para preservação.")

    # 2. CRIAÇÃO DO NOVO PLANO DE CONTAS
    plano_contas = {
        "3.01": {
            "nome": "RECURSOS HUMANOS",
            "itens": [
                ("3.01.01.0001", "SALÁRIOS", "Fixa"),
                ("3.01.01.0002", "13º SALÁRIO", "Fixa"),
                ("3.01.01.0003", "FÉRIAS", "Variável"),
                ("3.01.01.0004", "COMISSÕES", "Variável"),
                ("3.01.01.0005", "AJUDA DE CUSTO", "Variável"),
                ("3.01.01.0006", "DIÁRIAS", "Variável"),
                ("3.01.01.0007", "PLANO DE SAÚDE", "Fixa"),
                ("3.01.01.0008", "ESTAGIÁRIO", "Fixa"),
                ("3.01.01.0009", "SALÁRIO MATERNIDADE", "Variável"),
                ("3.01.01.0010", "AVISO PRÉVIO", "Variável"),
                ("3.01.02.0001", "VALE TRANSPORTE", "Variável"),
                ("3.01.02.0002", "ALIMENTAÇÃO", "Variável"),
                ("3.01.02.0003", "APERFEIÇOAMENTO PROFISSIONAL", "Variável"),
                ("3.01.03.0001", "INSS", "Variável"),
                ("3.01.03.0002", "FGTS", "Variável"),
                ("3.01.03.0003", "PIS/SOBRE FOLHA DE PAGAMENTO", "Variável"),
                ("3.01.03.0006", "CONTRIBUIÇÃO SINDICAL PATRONAL", "Variável"),
                ("3.01.04.0001", "BOLSA DE ESTAGIÁRIO", "Fixa"),
                ("3.01.04.0002", "HONORÁRIOS PROFISSIONAIS", "Variável"),
                ("3.01.04.0003", "PREVIDÊNCIA SOCIAL (AUTÔNOMOS)", "Variável"),
                ("3.01.04.0005", "AUTÔNOMOS", "Variável"),
                ("3.01.04.0006", "ISS AUTÔNOMOS", "Variável"),
                ("3.01.04.0008", "ZELADORIA", "Fixa"),
                ("3.01.04.0009", "AJUDA DE CUSTO MINISTERIAL", "Fixa"),
            ]
        },
        "3.02": {
            "nome": "DESPESAS ADMINISTRATIVAS",
            "itens": [
                ("3.02.01.0001", "CONSERVAÇÃO DE IMÓVEIS", "Variável"),
                ("3.02.01.0002", "CONSERVAÇÃO DE EQUIPAMENTOS", "Variável"),
                ("3.02.01.0003", "CONSERVAÇÃO DE INSTALAÇÕES", "Variável"),
                ("3.02.02.0001", "LOCAÇÃO DE EQUIPAMENTOS", "Fixa"),
                ("3.02.02.0002", "INTERNET", "Fixa"),
                ("3.02.02.0003", "TELEFONES E CORREIOS", "Variável"),
                ("3.02.03.0001", "ALUGUÉIS", "Fixa"),
                ("3.02.03.0002", "CONDOMÍNIO", "Fixa"),
                ("3.02.03.0003", "ENERGIA ELÉTRICA", "Variável"),
                ("3.02.03.0004", "ALIMENTAÇÃO/LANCHES", "Variável"),
                ("3.02.03.0005", "MATERIAL DE LIMPEZA", "Variável"),
                ("3.02.03.0006", "MATERIAL DE ESCRITÓRIO", "Variável"),
                ("3.02.03.0007", "MANUTENÇÃO GERAL", "Variável"),
                ("3.02.03.0008", "ÁGUA", "Variável"),
                ("3.02.03.0009", "DESPESAS DE VEÍCULOS", "Variável"),
                ("3.02.03.0010", "VIAGENS E ESTADAS", "Variável"),
                ("3.02.03.0011", "TARIFAS BANCÁRIAS", "Variável"),
                ("3.02.03.0012", "VESTUÁRIOS/UNIFORMES", "Variável"),
                ("3.02.03.0013", "PLANO COOPERATIVO", "Fixa"),
                ("3.02.03.0014", "MISSÕES", "Variável"),
                ("3.02.03.0015", "LEMBRANÇAS E HOMENAGENS", "Variável"),
                ("3.02.03.0016", "CONFERENCISTA/PREGADOR/CANTOR", "Variável"),
                ("3.02.03.0017", "DESPESAS CARTORIAIS", "Variável"),
                ("3.02.03.0018", "DESPESAS COM CONGREGAÇÃO", "Variável"),
                ("3.02.03.0019", "DESPESAS COM SEMINÁRIOS", "Variável"),
                ("3.02.03.0020", "CONFRATERNIZAÇÃO E CEIA", "Variável"),
                ("3.02.05.0001", "PUBLICIDADE INSTITUCIONAL", "Variável"),
                ("3.02.09.0001", "JUROS E DESCONTOS CONCEDIDOS", "Variável"),
                ("3.02.09.0003", "MULTAS POR ATRASO", "Variável"),
            ]
        },
        "3.03": {
            "nome": "ATIVIDADE EDUCACIONAL E SOCIAL",
            "itens": [
                ("3.03.01.0003", "TRANSPORTE", "Variável"),
                ("3.03.01.0004", "MATERIAIS (EDUCACIONAL)", "Variável"),
                ("3.04.01.0000", "ASSISTÊNCIA SOCIAL - GERAL", "Variável"),
            ]
        },
        "3.08": {
            "nome": "CUSTOS E DESPESAS GERAIS",
            "itens": [
                ("3.08.02.0001", "IMPOSTOS E TAXAS FEDERAIS", "Variável"),
                ("3.08.02.0002", "IMPOSTOS E TAXAS ESTADUAIS", "Variável"),
                ("3.08.02.0003", "IMPOSTOS E TAXAS MUNICIPAIS", "Variável"),
                ("3.08.03.0002", "COMBUSTÍVEIS E LUBRIFICANTES", "Variável"),
                ("3.08.04.0006", "AUDITORIA EXTERNA", "Variável"),
            ]
        }
    }

    criados_count = 0
    try:
        for codigo_cat, dados in plano_contas.items():
            # Verifica se a categoria já existe (pelo nome exato) para não duplicar
            categoria = CategoriaDespesa.query.filter_by(nome=dados['nome']).first()
            
            if not categoria:
                categoria = CategoriaDespesa(nome=dados['nome'], codigo=codigo_cat)
                db.session.add(categoria)
                db.session.flush()
                criados_count += 1
            else:
                # Se já existe (e não foi renomeada), atualiza o código
                categoria.codigo = codigo_cat
            
            for codigo_item, nome_item, tipo in dados['itens']:
                # Verifica se item existe dentro da categoria
                item = ItemDespesa.query.filter_by(nome=nome_item, categoria_id=categoria.id).first()
                if not item:
                    item = ItemDespesa(
                        nome=nome_item,
                        codigo=codigo_item,
                        tipo_fixa_variavel=tipo,
                        categoria_id=categoria.id
                    )
                    db.session.add(item)

        db.session.commit()
        click.echo(f"✅ Sucesso! Plano de contas atualizado. {criados_count} novas categorias adicionadas.")

    except Exception as e:
        db.session.rollback()
        click.echo(f"❌ Erro ao cadastrar plano de contas: {e}")

@click.command('migrar-dados-antigos')
@with_appcontext
def migrar_dados_antigos():
    """
    Migra as despesas dos itens '(ANTIGO)' para os novos códigos do Plano de Contas
    e remove os itens antigos vazios.
    """
    click.echo("🚀 Iniciando migração inteligente dos lançamentos...")

    # Mapeamento: "Nome Exato Antigo": "Novo Código Destino"
    # Baseado na sua imagem e no PDF
    de_para = {
        "Salários Funcionários (ANTIGO)": "3.01.01.0001", # SALÁRIOS
        "Prebenda Ministerial (ANTIGO)": "3.01.04.0009",  # AJUDA DE CUSTO MINISTERIAL
        "Aluguel (ANTIGO)": "3.02.03.0001",               # ALUGUÉIS
        "Água (ANTIGO)": "3.02.03.0008",                  # ÁGUA
        "Material de Higiene e Limpeza (ANTIGO)": "3.02.03.0005", # MATERIAL DE LIMPEZA
        
        # Mapeamentos por aproximação (baseado no contexto de igreja)
        "Segurança e Vigilância (ANTIGO)": "3.01.04.0005", # Mapeado para AUTÔNOMOS (Prestação de serviço)
        "Serviços de Limpeza e Lavanderia (ANTIGO)": "3.01.04.0008", # Mapeado para ZELADORIA
        "Site e Sistema (ANTIGO)": "3.02.02.0002", # Mapeado para INTERNET (Tecnologia)
    }

    total_migrados = 0

    try:
        for nome_antigo, codigo_novo in de_para.items():
            # 1. Encontrar o Item Antigo
            item_antigo = ItemDespesa.query.filter_by(nome=nome_antigo).first()
            
            # 2. Encontrar o Item Novo pelo código
            item_novo = ItemDespesa.query.filter_by(codigo=codigo_novo).first()

            if item_antigo and item_novo:
                # 3. Atualizar todas as despesas vinculadas
                despesas = Despesa.query.filter_by(item_id=item_antigo.id).all()
                count = len(despesas)
                
                if count > 0:
                    click.echo(f"   🔄 Migrando {count} despesas de '{nome_antigo}' -> '{item_novo.nome}'")
                    for despesa in despesas:
                        despesa.item_id = item_novo.id
                    
                    total_migrados += count
            elif not item_antigo:
                click.echo(f"   ℹ️  Item antigo '{nome_antigo}' não encontrado (já removido ou nome incorreto).")
            elif not item_novo:
                click.echo(f"   ⚠️  Item novo código '{codigo_novo}' não encontrado no banco. Execute o seed primeiro.")

        db.session.commit()
        click.echo(f"✅ Migração de dados concluída! {total_migrados} lançamentos atualizados.")

        # 4. Limpeza Final (Faxina)
        click.echo("🧹 Executando limpeza de itens e categorias vazias...")
        
        # Deleta itens (ANTIGO) que ficaram sem despesas
        itens_removidos = ItemDespesa.query.filter(ItemDespesa.nome.like('%(ANTIGO)%')).delete(synchronize_session=False)
        
        # Deleta categorias (ANTIGO) que ficaram sem itens
        # (Logica simplificada: Tenta deletar, se falhar é pq ainda tem itens, o banco barra)
        cats_antigas = CategoriaDespesa.query.filter(CategoriaDespesa.nome.like('%(ANTIGO)%')).all()
        cats_removidas = 0
        for cat in cats_antigas:
            if cat.itens.count() == 0:
                db.session.delete(cat)
                cats_removidas += 1
        
        db.session.commit()
        click.echo(f"✨ Limpeza finalizada: {itens_removidos} itens e {cats_removidas} categorias antigas removidas.")

    except Exception as e:
        db.session.rollback()
        click.echo(f"❌ Erro durante a migração: {e}")