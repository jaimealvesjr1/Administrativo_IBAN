from app.extensions import db
from datetime import datetime
from flask_login import UserMixin

class Membro(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(120), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=True)
    data_recepcao = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), nullable=False)
    campus = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True)

    presencas = db.relationship('Presenca', backref='membro', lazy=True)
    jornada_evento = db.relationship('JornadaEvento', backref='membro', lazy=True)

    def __repr__(self):
        return f'<Membro {self.nome}>'
    
    def registrar_evento_jornada(self, descricao, tipo_evento):
        evento = JornadaEvento(membro_id=self.id, descricao=descricao, tipo_evento=tipo_evento)
        db.session.add(evento)
        db.session.commit()

class JornadaEvento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    data_evento = db.Column(db.DateTime, default=datetime.utcnow)
    descricao = db.Column(db.Text, nullable=False)
    tipo_evento = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<JornadaEvento {self.data_evento}: {self.descricao}>'
