from flask import Blueprint

eventos_bp = Blueprint('eventos', __name__, url_prefix='/eventos', template_folder='templates')

from . import routes, models
