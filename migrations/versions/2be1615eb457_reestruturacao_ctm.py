"""Reestruturacao CTM

Revision ID: 2be1615eb457
Revises: 396fd74b70c8
Create Date: 2025-08-14 10:22:40.920322

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '2be1615eb457'
down_revision = '396fd74b70c8'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    # Operações de DROP e alteração de colunas existentes
    if 'presenca' in tables:
        with op.batch_alter_table('presenca', schema=None) as batch_op:
            batch_op.drop_column('aula_id')

    if 'aula' in tables:
        op.drop_table('aula')

    # Cria as novas tabelas
    op.create_table('classe_ctm',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=50), nullable=False),
        sa.Column('supervisor_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['supervisor_id'], ['membro.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )
    op.create_table('turma_ctm',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=50), nullable=False),
        sa.Column('classe_id', sa.Integer(), nullable=False),
        sa.Column('facilitador_id', sa.Integer(), nullable=True),
        sa.Column('ativa', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['classe_id'], ['classe_ctm.id'], ),
        sa.ForeignKeyConstraint(['facilitador_id'], ['membro.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('aluno_turma',
        sa.Column('membro_id', sa.Integer(), nullable=False),
        sa.Column('turma_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['membro_id'], ['membro.id'], ),
        sa.ForeignKeyConstraint(['turma_id'], ['turma_ctm.id'], ),
        sa.PrimaryKeyConstraint('membro_id', 'turma_id')
    )
    op.create_table('aula_modelo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tema', sa.String(length=100), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('classe_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['classe_id'], ['classe_ctm.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('classe_id', 'ordem', name='_classe_ordem_uc')
    )
    op.create_table('aula_realizada',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('chave', sa.String(length=10), nullable=False),
        sa.Column('aula_modelo_id', sa.Integer(), nullable=False),
        sa.Column('turma_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['aula_modelo_id'], ['aula_modelo.id'], ),
        sa.ForeignKeyConstraint(['turma_id'], ['turma_ctm.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('data', 'turma_id', name='_data_turma_uc')
    )
    with op.batch_alter_table('presenca', schema=None) as batch_op:
        batch_op.add_column(sa.Column('aula_realizada_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key('fk_presenca_aula_realizada', 'aula_realizada', ['aula_realizada_id'], ['id'])
        batch_op.create_unique_constraint('_membro_aula_realizada_uc', ['membro_id', 'aula_realizada_id'])

def downgrade():
    with op.batch_alter_table('presenca', schema=None) as batch_op:
        batch_op.add_column(sa.Column('campus', sa.VARCHAR(length=50), nullable=True))
        batch_op.drop_constraint('_membro_aula_realizada_uc', type_='unique')
        batch_op.drop_constraint('fk_presenca_aula_realizada', type_='foreignkey')
        batch_op.drop_column('aula_realizada_id')

    op.create_table('aula',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('data', sa.DATE(), nullable=False),
        sa.Column('tema', sa.VARCHAR(length=30), nullable=False),
        sa.Column('chave', sa.VARCHAR(length=10), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('data')
    )

    with op.batch_alter_table('presenca', schema=None) as batch_op:
        batch_op.add_column(sa.Column('aula_id', sa.INTEGER(), nullable=False))
        batch_op.create_foreign_key('fk_presenca_aula', 'aula', ['aula_id'], ['id'])

    op.drop_table('aula_realizada')
    op.drop_table('aluno_turma')
    op.drop_table('turma_ctm')
    op.drop_table('aula_modelo')
    op.drop_table('classe_ctm')
