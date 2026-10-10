"""add recommendations table

Revision ID: 421a0e038dd3
Revises: 32a099c6fe86
Create Date: 2026-08-24 02:31:50.873865

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '421a0e038dd3'
down_revision: Union[str, None] = '32a099c6fe86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('recommendations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('idea_text', sa.Text(), nullable=False),
    sa.Column('format', sa.Text(), nullable=False),
    sa.Column('best_time', sa.Text(), nullable=True),
    sa.Column('rationale', sa.Text(), nullable=False),
    sa.Column('predicted_score', sa.Float(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('linked_content_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("format IN ('short_video', 'long_video', 'image', 'carousel', 'text')", name='ck_recommendations_format'),
    sa.CheckConstraint("status IN ('proposed', 'actioned', 'dismissed')", name='ck_recommendations_status'),
    sa.ForeignKeyConstraint(['linked_content_id'], ['content.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recommendations_user_id'), 'recommendations', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_recommendations_user_id'), table_name='recommendations')
    op.drop_table('recommendations')