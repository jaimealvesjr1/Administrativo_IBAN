import click
import os
from flask.cli import with_appcontext
from flask import current_app
from app.extensions import db
from app.auth.models import User
from app.membresia.models import Membro
from app.membresia.routes import save_profile_picture, allowed_file, PROFILE_PIC_SIZE, COMPRESSION_QUALITY
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
