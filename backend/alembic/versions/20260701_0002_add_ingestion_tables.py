"""add ingestion tables"""

from alembic import op
import sqlalchemy as sa


revision = "20260701_0002"
down_revision = "20260629_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("service", sa.String(length=255), server_default="", nullable=False),
        sa.Column("region", sa.String(length=255), server_default="", nullable=False),
        sa.Column("amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("usage_type", sa.String(length=255), server_default="", nullable=False),
        sa.Column("account_id", sa.String(length=64), server_default="", nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "service", "region", "usage_type", "account_id", name="uq_cost_records_natural_key"),
    )
    op.create_index(op.f("ix_cost_records_date"), "cost_records", ["date"], unique=False)
    op.create_index(op.f("ix_cost_records_id"), "cost_records", ["id"], unique=False)
    op.create_index(op.f("ix_cost_records_synced_at"), "cost_records", ["synced_at"], unique=False)

    op.create_table(
        "cloud_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=64), server_default="", nullable=False),
        sa.Column("state", sa.String(length=64), server_default="", nullable=False),
        sa.Column("instance_type", sa.String(length=128), server_default="", nullable=False),
        sa.Column("tags_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource_id", "resource_type", name="uq_cloud_resources_identity"),
    )
    op.create_index(op.f("ix_cloud_resources_id"), "cloud_resources", ["id"], unique=False)
    op.create_index(op.f("ix_cloud_resources_last_seen"), "cloud_resources", ["last_seen"], unique=False)
    op.create_index(op.f("ix_cloud_resources_resource_id"), "cloud_resources", ["resource_id"], unique=False)
    op.create_index(op.f("ix_cloud_resources_resource_type"), "cloud_resources", ["resource_type"], unique=False)

    op.create_table(
        "metric_samples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=False),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=64), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource_id", "metric_name", "timestamp", name="uq_metric_samples_identity"),
    )
    op.create_index(op.f("ix_metric_samples_id"), "metric_samples", ["id"], unique=False)
    op.create_index(op.f("ix_metric_samples_metric_name"), "metric_samples", ["metric_name"], unique=False)
    op.create_index(op.f("ix_metric_samples_resource_id"), "metric_samples", ["resource_id"], unique=False)
    op.create_index(op.f("ix_metric_samples_timestamp"), "metric_samples", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_metric_samples_timestamp"), table_name="metric_samples")
    op.drop_index(op.f("ix_metric_samples_resource_id"), table_name="metric_samples")
    op.drop_index(op.f("ix_metric_samples_metric_name"), table_name="metric_samples")
    op.drop_index(op.f("ix_metric_samples_id"), table_name="metric_samples")
    op.drop_table("metric_samples")

    op.drop_index(op.f("ix_cloud_resources_resource_type"), table_name="cloud_resources")
    op.drop_index(op.f("ix_cloud_resources_resource_id"), table_name="cloud_resources")
    op.drop_index(op.f("ix_cloud_resources_last_seen"), table_name="cloud_resources")
    op.drop_index(op.f("ix_cloud_resources_id"), table_name="cloud_resources")
    op.drop_table("cloud_resources")

    op.drop_index(op.f("ix_cost_records_synced_at"), table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_id"), table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_date"), table_name="cost_records")
    op.drop_table("cost_records")
