import click
from flask.cli import with_appcontext
from app.extensions import db
from app.auth.models import User
from app.membresia.models import Membro
from config import Config

@click.command("create-admin")
@with_appcontext
def create_admin():
    if User.query.filter_by(username="admin").first():
        click.echo("⚠️  Usuário 'admin' já existe.")
    else:
        admin = User(username="admin", role="admin")
        admin.set_password("1234")
        db.session.add(admin)
        db.session.commit()
        click.echo("✅ Usuário 'admin' criado com sucesso.")

@click.command("create-anonymous-members")
@with_appcontext
def create_anonymous_members():
    click.echo("Iniciando a criação/verificação de membros de oferta anônima...")

    if not hasattr(Config, 'IDS_OFERTA_ANONIMA'):
        click.echo("❌ Erro: 'IDS_OFERTA_ANONIMA' não encontrado em config.py. Verifique sua configuração.")
        return

    from datetime import datetime

    created_count = 0
    existing_count = 0

    for campus_name, anon_id in Config.IDS_OFERTA_ANONIMA_POR_CAMPUS.items():
        membro_anonimo = Membro.query.get(anon_id)
        if not membro_anonimo:
            try:
                membro_anonimo = Membro(
                    id=anon_id,
                    nome_completo=f'Oferta Anônima ({campus_name})',
                    status='Não-Membro',
                    campus=campus_name,
                    ativo=False,
                    data_nascimento=datetime.strptime('01/01/1900', '%d/%m/%Y').date(),
                    data_recepcao=datetime.strptime('01/01/1900', '%d/%m/%Y').date()
                )
                db.session.add(membro_anonimo)
                click.echo(f"✅ Membro 'Oferta Anônima ({campus_name})' (ID: {anon_id}) criado.")
                created_count += 1
            except Exception as e:
                db.session.rollback()
                click.echo(f"❌ Erro ao criar membro para {campus_name} (ID: {anon_id}): {e}")
        else:
            click.echo(f"⚠️ Membro 'Oferta Anônima ({campus_name})' (ID: {anon_id}) já existe.")
            existing_count += 1

    try:
        db.session.commit()
        click.echo(f"\nResumo da Operação:")
        if created_count > 0:
            click.echo(f"✅ {created_count} membro(s) anônimo(s) novo(s) criado(s) com sucesso.")
        if existing_count > 0:
            click.echo(f"⚠️ {existing_count} membro(s) anônimo(s) já existente(s) verificado(s).")
        if created_count == 0 and existing_count == 0:
            click.echo("Nenhum membro anônimo processado (verifique a configuração).")

    except Exception as e:
        db.session.rollback()
        click.echo(f"❌ Erro ao salvar alterações no banco de dados: {e}")
