"""add multitenancy foundation"""

from alembic import op
import sqlalchemy as sa


revision = "20260701_0003"
down_revision = "20260701_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_id"), "organizations", ["id"], unique=False)
    op.create_index(op.f("ix_organizations_name"), "organizations", ["name"], unique=True)

    op.create_table(
        "aws_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("access_key_id_encrypted", sa.String(length=1024), nullable=False),
        sa.Column("secret_access_key_encrypted", sa.String(length=1024), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", name="uq_aws_connections_organization"),
    )
    op.create_index(op.f("ix_aws_connections_id"), "aws_connections", ["id"], unique=False)
    op.create_index(op.f("ix_aws_connections_organization_id"), "aws_connections", ["organization_id"], unique=False)

    op.add_column("users", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.add_column("cost_records", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.add_column("cloud_resources", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.add_column("metric_samples", sa.Column("organization_id", sa.Integer(), nullable=True))

    op.execute("INSERT INTO organizations (name) VALUES ('Legacy Default Organization')")
    op.execute("UPDATE users SET organization_id = (SELECT id FROM organizations WHERE name = 'Legacy Default Organization' LIMIT 1)")
    op.execute("UPDATE cost_records SET organization_id = (SELECT id FROM organizations WHERE name = 'Legacy Default Organization' LIMIT 1)")
    op.execute("UPDATE cloud_resources SET organization_id = (SELECT id FROM organizations WHERE name = 'Legacy Default Organization' LIMIT 1)")
    op.execute("UPDATE metric_samples SET organization_id = (SELECT id FROM organizations WHERE name = 'Legacy Default Organization' LIMIT 1)")

    op.alter_column("users", "organization_id", nullable=False)
    op.alter_column("cost_records", "organization_id", nullable=False)
    op.alter_column("cloud_resources", "organization_id", nullable=False)
    op.alter_column("metric_samples", "organization_id", nullable=False)

    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)
    op.create_foreign_key("fk_users_organization_id", "users", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")

    op.create_index(op.f("ix_cost_records_organization_id"), "cost_records", ["organization_id"], unique=False)
    op.create_foreign_key("fk_cost_records_organization_id", "cost_records", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("uq_cost_records_natural_key", "cost_records", type_="unique")
    op.create_unique_constraint(
        "uq_cost_records_natural_key",
        "cost_records",
        ["organization_id", "date", "service", "region", "usage_type", "account_id"],
    )

    op.create_index(op.f("ix_cloud_resources_organization_id"), "cloud_resources", ["organization_id"], unique=False)
    op.create_foreign_key("fk_cloud_resources_organization_id", "cloud_resources", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("uq_cloud_resources_identity", "cloud_resources", type_="unique")
    op.create_unique_constraint(
        "uq_cloud_resources_identity",
        "cloud_resources",
        ["organization_id", "resource_id", "resource_type"],
    )

    op.create_index(op.f("ix_metric_samples_organization_id"), "metric_samples", ["organization_id"], unique=False)
    op.create_foreign_key("fk_metric_samples_organization_id", "metric_samples", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("uq_metric_samples_identity", "metric_samples", type_="unique")
    op.create_unique_constraint(
        "uq_metric_samples_identity",
        "metric_samples",
        ["organization_id", "resource_id", "metric_name", "timestamp"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_metric_samples_identity", "metric_samples", type_="unique")
    op.create_unique_constraint("uq_metric_samples_identity", "metric_samples", ["resource_id", "metric_name", "timestamp"])
    op.drop_constraint("fk_metric_samples_organization_id", "metric_samples", type_="foreignkey")
    op.drop_index(op.f("ix_metric_samples_organization_id"), table_name="metric_samples")
    op.drop_column("metric_samples", "organization_id")

    op.drop_constraint("uq_cloud_resources_identity", "cloud_resources", type_="unique")
    op.create_unique_constraint("uq_cloud_resources_identity", "cloud_resources", ["resource_id", "resource_type"])
    op.drop_constraint("fk_cloud_resources_organization_id", "cloud_resources", type_="foreignkey")
    op.drop_index(op.f("ix_cloud_resources_organization_id"), table_name="cloud_resources")
    op.drop_column("cloud_resources", "organization_id")

    op.drop_constraint("uq_cost_records_natural_key", "cost_records", type_="unique")
    op.create_unique_constraint("uq_cost_records_natural_key", "cost_records", ["date", "service", "region", "usage_type", "account_id"])
    op.drop_constraint("fk_cost_records_organization_id", "cost_records", type_="foreignkey")
    op.drop_index(op.f("ix_cost_records_organization_id"), table_name="cost_records")
    op.drop_column("cost_records", "organization_id")

    op.drop_constraint("fk_users_organization_id", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_organization_id"), table_name="users")
    op.drop_column("users", "organization_id")

    op.drop_index(op.f("ix_aws_connections_organization_id"), table_name="aws_connections")
    op.drop_index(op.f("ix_aws_connections_id"), table_name="aws_connections")
    op.drop_table("aws_connections")

    op.drop_index(op.f("ix_organizations_name"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_id"), table_name="organizations")
    op.drop_table("organizations")
