"""create users table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260629_0001"
down_revision = None
branch_labels = None
depends_on = None


user_role = postgresql.ENUM("admin", "viewer", name="userrole", create_type=False)


def upgrade() -> None:
    postgresql.ENUM("admin", "viewer", name="userrole").create(op.get_bind(), checkfirst=True)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    postgresql.ENUM("admin", "viewer", name="userrole").drop(op.get_bind(), checkfirst=True)
