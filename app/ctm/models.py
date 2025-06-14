from app.extensions import db
from datetime import datetime
from app.membresia.models import Membro, JornadaEvento

class Aula(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, unique=True)
    tema = db.Column(db.String(30), nullable=False)
    chave = db.Column(db.String(10), nullable=False)

    presencas_associadas = db.relationship('Presenca', backref='aula', lazy=True)

    def __repr__(self):
        return f"<Aula {self.data} - {self.tema}>"

class Presenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    aula_id = db.Column(db.Integer, db.ForeignKey('aula.id'), nullable=False)
    avaliacao = db.Column(db.Integer)

    def __repr__(self):
        return f"<Presenca {self.id} - Membro: {self.membro.nome_completo if self.membro else 'N/A'} - Data: {self.aula.data if self.aula else 'N/A'}>"
    
    def registrar_evento_jornada(self):
        membro = Membro.query.get(self.membro_id)
        aula = Aula.query.get(self.aula_id)
        if membro and aula:
            descricao = f'Participou da aula {aula.tema}.'
            membro.registrar_evento_jornada(descricao, 'Presenca')
