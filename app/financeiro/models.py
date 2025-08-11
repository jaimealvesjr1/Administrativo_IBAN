from app.extensions import db
from datetime import datetime, date, timezone
from app.membresia.models import Membro
from app.filters import format_currency

class Contribuicao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False, index=True)
    membro = db.relationship('Membro', backref='contribuicoes', lazy=True)
    tipo = db.Column(db.String(30), nullable=False, index=True)
    valor = db.Column(db.Float, nullable=False)
    data_lanc = db.Column(db.Date, nullable=False, default=date.today, index=True)
    forma = db.Column(db.String(20), nullable=False)
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Contribuicao Membro: {self.membro_id} Valor: {self.valor}>'
    
    def registrar_evento_jornada(self):
        membro = Membro.query.get(self.membro_id)
        if membro:
            descricao = f'Contribuiu com {self.tipo} {self.forma} no valor de {format_currency(self.valor)}.'
            membro.registrar_evento_jornada(descricao, 'Contribuicao')
