from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship

participantes_evento = db.Table('participantes_evento',
    db.Column('evento_id', db.Integer, db.ForeignKey('evento.id'), primary_key=True),
    db.Column('membro_id', db.Integer, db.ForeignKey('membro.id'), primary_key=True)
)

class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    tipo_evento = db.Column(db.String(50), nullable=False)
    data_evento = db.Column(db.Date, nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    concluido = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    participantes = db.relationship(
        'Membro',
        secondary=participantes_evento,
        backref='eventos_inscritos',
        lazy='dynamic'
    )

class InscricaoEvento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), nullable=False)
    presente = db.Column(db.Boolean, default=False)
    status_conclusao = db.Column(db.String(50), nullable=True)
    observacao_admin = db.Column(db.Text, nullable=True)

    membro = db.relationship('Membro', backref='inscricoes')
    evento = db.relationship('Evento', backref='inscricoes')