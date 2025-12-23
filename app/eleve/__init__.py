from flask import Blueprint

eleve_bp = Blueprint('eleve', __name__, url_prefix='/eleve')

from . import routes

try:
    from . import cli
    eleve_bp.cli.add_command(cli.eleve)
except ImportError:
    pass