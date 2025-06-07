"""add document quotes table

Revision ID: 20240320000000
Revises: 20240319000000
Create Date: 2024-03-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240320000000'
down_revision = '20240319000000'
branch_labels = None
depends_on = None

def upgrade():
    # Create document_quotes table
    op.create_table(
        'document_quotes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('deal_id', sa.String(36), nullable=False),
        sa.Column('document_id', sa.String(36), nullable=False),
        sa.Column('quote_text', sa.Text, nullable=False),
        sa.Column('speaker', sa.String(255), nullable=True),
        sa.Column('speaker_title', sa.String(255), nullable=True),
        sa.Column('context', sa.Text, nullable=True),
        sa.Column('significance_score', sa.Float, nullable=False),
        sa.Column('quote_type', sa.String(50), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE')
    )

    # Create quote_relationships table
    op.create_table(
        'quote_relationships',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('quote_id', sa.String(36), nullable=False),
        sa.Column('related_metric', sa.String(255), nullable=False),
        sa.Column('relationship_type', sa.String(50), nullable=False),
        sa.Column('confidence_score', sa.Float, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['quote_id'], ['document_quotes.id'], ondelete='CASCADE')
    )

    # Create indexes
    op.create_index('ix_document_quotes_deal_id', 'document_quotes', ['deal_id'])
    op.create_index('ix_document_quotes_document_id', 'document_quotes', ['document_id'])
    op.create_index('ix_document_quotes_quote_type', 'document_quotes', ['quote_type'])
    op.create_index('ix_quote_relationships_quote_id', 'quote_relationships', ['quote_id'])
    op.create_index('ix_quote_relationships_relationship_type', 'quote_relationships', ['relationship_type'])

def downgrade():
    # Drop indexes
    op.drop_index('ix_quote_relationships_relationship_type')
    op.drop_index('ix_quote_relationships_quote_id')
    op.drop_index('ix_document_quotes_quote_type')
    op.drop_index('ix_document_quotes_document_id')
    op.drop_index('ix_document_quotes_deal_id')

    # Drop tables
    op.drop_table('quote_relationships')
    op.drop_table('document_quotes') 