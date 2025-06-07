"""add chart tables

Revision ID: 20240321000000
Revises: 20240320000000
Create Date: 2024-03-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240321000000'
down_revision = '20240320000000'
branch_labels = None
depends_on = None

def upgrade():
    # Create chart_elements table
    op.create_table(
        'chart_elements',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('deal_id', sa.String(36), nullable=False),
        sa.Column('document_id', sa.String(36), nullable=False),
        sa.Column('chart_type', sa.String(50), nullable=False),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('data_points', postgresql.JSONB, nullable=True),
        sa.Column('source_page', sa.Integer, nullable=True),
        sa.Column('confidence_score', sa.Float, nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE')
    )

    # Create chart_relationships table
    op.create_table(
        'chart_relationships',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('chart_id', sa.String(36), nullable=False),
        sa.Column('related_text', sa.Text, nullable=False),
        sa.Column('relationship_type', sa.String(50), nullable=False),
        sa.Column('confidence_score', sa.Float, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['chart_id'], ['chart_elements.id'], ondelete='CASCADE')
    )

    # Create indexes
    op.create_index('ix_chart_elements_deal_id', 'chart_elements', ['deal_id'])
    op.create_index('ix_chart_elements_document_id', 'chart_elements', ['document_id'])
    op.create_index('ix_chart_elements_chart_type', 'chart_elements', ['chart_type'])
    op.create_index('ix_chart_relationships_chart_id', 'chart_relationships', ['chart_id'])
    op.create_index('ix_chart_relationships_relationship_type', 'chart_relationships', ['relationship_type'])

def downgrade():
    # Drop indexes
    op.drop_index('ix_chart_relationships_relationship_type')
    op.drop_index('ix_chart_relationships_chart_id')
    op.drop_index('ix_chart_elements_chart_type')
    op.drop_index('ix_chart_elements_document_id')
    op.drop_index('ix_chart_elements_deal_id')

    # Drop tables
    op.drop_table('chart_relationships')
    op.drop_table('chart_elements') 