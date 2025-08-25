"""create repos

Revision ID: 4594589a1259
Revises: c360318a95a5
Create Date: 2025-08-25 10:07:15.503440

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4594589a1259'
down_revision: Union[str, None] = 'c360318a95a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'BVRepos',
        sa.Column('user_id', sa.UUID, primary_key=True, nullable=False, index=True),
        sa.Column('name', sa.String, primary_key=True, nullable=False, index=True)
    )
    with op.batch_alter_table('BVRepos', schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_user_id",
            "BVUsers",
            ["user_id"],
            ["id"],
            ondelete="CASCADE"
        )


def downgrade() -> None:
    op.drop_table('BVRepos')
