from flask import Blueprint, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app.extensions import db
from .models import JornadaEvento
from app.decorators import admin_required

jornada_bp = Blueprint('jornada', __name__, url_prefix='/jornada')

@jornada_bp.route('/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_jornada_evento(event_id):
    evento = JornadaEvento.query.get_or_404(event_id)
    
    try:
        db.session.delete(evento)
        db.session.commit()
        flash('Evento da jornada excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir o evento da jornada: {e}', 'danger')
        
    return redirect(request.referrer or url_for('main.index'))
