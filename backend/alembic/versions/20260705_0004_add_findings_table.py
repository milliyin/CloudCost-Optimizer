"""add findings table"""

from alembic import op
import sqlalchemy as sa


revision = "20260705_0004"
down_revision = "20260701_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("finding_type", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("evidence_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "resource_id", "finding_type", name="uq_findings_identity"),
    )
    op.create_index(op.f("ix_findings_id"), "findings", ["id"], unique=False)
    op.create_index(op.f("ix_findings_organization_id"), "findings", ["organization_id"], unique=False)
    op.create_index(op.f("ix_findings_resource_id"), "findings", ["resource_id"], unique=False)
    op.create_index(op.f("ix_findings_resource_type"), "findings", ["resource_type"], unique=False)
    op.create_index(op.f("ix_findings_finding_type"), "findings", ["finding_type"], unique=False)
    op.create_index(op.f("ix_findings_severity"), "findings", ["severity"], unique=False)
    op.create_index(op.f("ix_findings_status"), "findings", ["status"], unique=False)
    op.create_index(op.f("ix_findings_detected_at"), "findings", ["detected_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_findings_detected_at"), table_name="findings")
    op.drop_index(op.f("ix_findings_status"), table_name="findings")
    op.drop_index(op.f("ix_findings_severity"), table_name="findings")
    op.drop_index(op.f("ix_findings_finding_type"), table_name="findings")
    op.drop_index(op.f("ix_findings_resource_type"), table_name="findings")
    op.drop_index(op.f("ix_findings_resource_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_organization_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_id"), table_name="findings")
    op.drop_table("findings")
