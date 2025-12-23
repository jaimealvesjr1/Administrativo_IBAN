from flask import Blueprint, render_template, url_for, redirect
from flask_login import login_required, current_user
from app.eleve.utils import check_pilula_concluida_hoje
from config import Config

main_bp = Blueprint('main', __name__)
ano=Config.ANO_ATUAL
versao=Config.VERSAO_APP

@main_bp.route('/')
@login_required
def index():
    if current_user.is_authenticated and current_user.membro:
        membro_id = current_user.membro.id
        concluida_hoje, pilula_do_dia = check_pilula_concluida_hoje(membro_id)
    else:
        concluida_hoje = True
        pilula_do_dia = None

    return render_template('base/main.html', ano=ano, versao=versao, concluida_hoje=concluida_hoje, pilula_do_dia=pilula_do_dia)
