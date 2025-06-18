import click
from flask.cli import with_appcontext
from app.extensions import db
from app.auth.models import User

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
