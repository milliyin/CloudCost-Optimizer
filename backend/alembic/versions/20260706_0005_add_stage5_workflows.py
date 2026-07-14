"""add stage 5 workflow tables"""

from alembic import op
import sqlalchemy as sa


revision = "20260706_0005"
down_revision = "20260705_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("finding_id", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("estimated_monthly_savings", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("explanation", sa.Text(), server_default="", nullable=False),
        sa.Column("decided_by", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("finding_id", name="uq_recommendations_finding_id"),
    )
    op.create_index(op.f("ix_recommendations_id"), "recommendations", ["id"], unique=False)
    op.create_index(op.f("ix_recommendations_organization_id"), "recommendations", ["organization_id"], unique=False)
    op.create_index(op.f("ix_recommendations_finding_id"), "recommendations", ["finding_id"], unique=False)
    op.create_index(op.f("ix_recommendations_action_type"), "recommendations", ["action_type"], unique=False)
    op.create_index(op.f("ix_recommendations_status"), "recommendations", ["status"], unique=False)
    op.create_index(op.f("ix_recommendations_created_at"), "recommendations", ["created_at"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("details_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_audit_logs_organization_id"), "audit_logs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_target_type"), "audit_logs", ["target_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_target_id"), "audit_logs", ["target_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_timestamp"), "audit_logs", ["timestamp"], unique=False)

    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("scope_value", sa.String(length=255), server_default="", nullable=False),
        sa.Column("threshold_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("period", sa.String(length=32), server_default="monthly", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_budgets_id"), "budgets", ["id"], unique=False)
    op.create_index(op.f("ix_budgets_organization_id"), "budgets", ["organization_id"], unique=False)
    op.create_index(op.f("ix_budgets_owner_id"), "budgets", ["owner_id"], unique=False)
    op.create_index(op.f("ix_budgets_scope"), "budgets", ["scope"], unique=False)
    op.create_index(op.f("ix_budgets_period"), "budgets", ["period"], unique=False)
    op.create_index(op.f("ix_budgets_is_active"), "budgets", ["is_active"], unique=False)
    op.create_index(op.f("ix_budgets_created_at"), "budgets", ["created_at"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("budget_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("spend_at_trigger", sa.Numeric(12, 2), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("budget_id", "period_start", name="uq_alerts_budget_period"),
    )
    op.create_index(op.f("ix_alerts_id"), "alerts", ["id"], unique=False)
    op.create_index(op.f("ix_alerts_organization_id"), "alerts", ["organization_id"], unique=False)
    op.create_index(op.f("ix_alerts_budget_id"), "alerts", ["budget_id"], unique=False)
    op.create_index(op.f("ix_alerts_period_start"), "alerts", ["period_start"], unique=False)
    op.create_index(op.f("ix_alerts_triggered_at"), "alerts", ["triggered_at"], unique=False)
    op.create_index(op.f("ix_alerts_acknowledged"), "alerts", ["acknowledged"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_alerts_acknowledged"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_triggered_at"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_period_start"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_budget_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_organization_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_id"), table_name="alerts")
    op.drop_table("alerts")

    op.drop_index(op.f("ix_budgets_created_at"), table_name="budgets")
    op.drop_index(op.f("ix_budgets_is_active"), table_name="budgets")
    op.drop_index(op.f("ix_budgets_period"), table_name="budgets")
    op.drop_index(op.f("ix_budgets_scope"), table_name="budgets")
    op.drop_index(op.f("ix_budgets_owner_id"), table_name="budgets")
    op.drop_index(op.f("ix_budgets_organization_id"), table_name="budgets")
    op.drop_index(op.f("ix_budgets_id"), table_name="budgets")
    op.drop_table("budgets")

    op.drop_index(op.f("ix_audit_logs_timestamp"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_target_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_target_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_organization_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_recommendations_created_at"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_status"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_action_type"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_finding_id"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_organization_id"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_id"), table_name="recommendations")
    op.drop_table("recommendations")
