from app.extensions import db
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from config import Config

jornada_membro_associacao = db.Table('jornada_membro_associacao',
    Column('jornada_id', Integer, ForeignKey('jornada_evento.id'), primary_key=True),
    Column('membro_id', Integer, ForeignKey('membro.id'), primary_key=True)
)

jornada_pg_associacao = db.Table('jornada_pg_associacao',
    Column('jornada_id', Integer, ForeignKey('jornada_evento.id'), primary_key=True),
    Column('pequeno_grupo_id', Integer, ForeignKey('pequeno_grupo.id'), primary_key=True)
)

jornada_setor_associacao = db.Table('jornada_setor_associacao',
    Column('jornada_id', Integer, ForeignKey('jornada_evento.id'), primary_key=True),
    Column('setor_id', Integer, ForeignKey('setor.id'), primary_key=True)
)

jornada_area_associacao = db.Table('jornada_area_associacao',
    Column('jornada_id', Integer, ForeignKey('jornada_evento.id'), primary_key=True),
    Column('area_id', Integer, ForeignKey('area.id'), primary_key=True)
)

jornada_turma_ctm_associacao = db.Table('jornada_turma_ctm_associacao',
    Column('jornada_id', Integer, ForeignKey('jornada_evento.id'), primary_key=True),
    Column('turma_ctm_id', Integer, ForeignKey('turma_ctm.id'), primary_key=True)
)

class JornadaEvento(db.Model):
    __tablename__ = 'jornada_evento'

    id = Column(Integer, primary_key=True)
    usuario_executor_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    data_evento = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    tipo_acao = Column(String(100), nullable=False)
    descricao_detalhada = Column(Text, nullable=False)

    membros_afetados = relationship('Membro', secondary=jornada_membro_associacao, backref=db.backref('jornada_eventos_membro', lazy='dynamic'), lazy='dynamic')
    pgs_afetados = relationship('PequenoGrupo', secondary=jornada_pg_associacao, backref=db.backref('jornada_eventos_pg', lazy='dynamic'), lazy='dynamic')
    setores_afetados = relationship('Setor', secondary=jornada_setor_associacao, backref=db.backref('jornada_eventos_setor', lazy='dynamic'), lazy='dynamic')
    areas_afetadas = relationship('Area', secondary=jornada_area_associacao, backref=db.backref('jornada_eventos_area', lazy='dynamic'), lazy='dynamic')
    turmas_ctm_afetadas = relationship('TurmaCTM', secondary=jornada_turma_ctm_associacao, backref=db.backref('jornada_eventos_turma', lazy='dynamic'), lazy='dynamic')

    executor = relationship('User', backref='eventos_executados')

    def __repr__(self):
        return f'<JornadaEvento {self.data_evento.strftime("%Y-%m-%d %H:%M")}: {self.tipo_acao}>'

def registrar_evento_jornada(tipo_acao, descricao_detalhada, usuario_executor, membros=None, pgs=None, setores=None, areas=None, turmas_ctm=None):
    try:
        evento = JornadaEvento(
            tipo_acao=tipo_acao,
            descricao_detalhada=descricao_detalhada,
            usuario_executor_id=usuario_executor.id if usuario_executor else None
        )
        db.session.add(evento)
        db.session.flush()

        if membros:
            for m in membros:
                evento.membros_afetados.append(m)
        if pgs:
            for p in pgs:
                evento.pgs_afetados.append(p)
        if setores:
            for s in setores:
                evento.setores_afetados.append(s)
        if areas:
            for a in areas:
                evento.areas_afetadas.append(a)
        if turmas_ctm:
            for t in turmas_ctm:
                evento.turmas_ctm_afetadas.append(t)

        db.session.commit()
        print(f"DEBUG: Evento de jornada registrado: '{tipo_acao}'")
    except Exception as e:
        db.session.rollback()
        print(f"ERRO ao registrar evento de jornada: {e}")
