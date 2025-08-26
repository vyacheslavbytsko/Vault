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
        sa.Column('id', sa.UUID, primary_key=True, nullable=False, index=True),
        sa.Column('user_id', sa.UUID, nullable=False, index=True),
        sa.Column('name', sa.String, nullable=False, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False)
    )
    with op.batch_alter_table('BVRepos', schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_user_id",
            "BVUsers",
            ["user_id"],
            ["id"],
            ondelete="CASCADE"
        )
        batch_op.create_unique_constraint(
            "uc_user_id_name",
            ["user_id", "name"]
        )

    op.create_table(
        'BVBranches',
        sa.Column('id', sa.UUID, primary_key=True, nullable=False, index=True),
        sa.Column('repo_id', sa.UUID, nullable=False, index=True),
        sa.Column('name', sa.String, nullable=False, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('first_commit', sa.UUID, nullable=True),
        sa.Column('last_commit', sa.UUID, nullable=True),
    )
    with op.batch_alter_table('BVRepos', schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_repo_id",
            "BVRepos",
            ["repo_id"],
            ["id"],
            ondelete="CASCADE"
        )
        batch_op.create_unique_constraint(
            "uc_repo_id_name",
            ["repo_id", "name"]
        )

    op.create_table(
        'BVCommits',
        sa.Column('id', sa.UUID, primary_key=True, nullable=False, index=True),
        sa.Column('branch_id', sa.UUID, nullable=False, index=True),
        sa.Column('prev_commit_id', sa.UUID, nullable=True),
        sa.Column('next_commit_id', sa.UUID, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('type', sa.String, nullable=False),
        sa.Column('v', sa.String, nullable=False),
        sa.Column('data', sa.JSON, nullable=False),
        sa.Column('files_ids', sa.JSON, nullable=True)
    )
    with op.batch_alter_table('BVCommits', schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_branch_id",
            "BVBranches",
            ["branch_id"],
            ["id"],
            ondelete="CASCADE"
        )
        batch_op.create_unique_constraint(
            "uc_branch_id_prev_commit",
            ["branch_id", "prev_commit_id"],
        )
        batch_op.create_unique_constraint(
            "uc_branch_id_next_commit",
            ["branch_id", "next_commit_id"],
        )


def downgrade() -> None:
    op.drop_table('BVRepos')
    op.drop_table('BVBranches')
