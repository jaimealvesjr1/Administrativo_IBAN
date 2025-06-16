from flask import Blueprint, render_template, url_for, redirect
from config import Config

main_bp = Blueprint('main', __name__)
ano=Config.ANO_ATUAL
versao=Config.VERSAO_APP

@main_bp.route('/')
def index():
    return render_template('base/main.html', ano=ano, versao=versao)
