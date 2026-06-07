"""为文件表新增归属用户元数据。

修订版本 ID: 20260607_000003
依赖修订: 20260606_000002
创建日期: 2026-06-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260607_000003"
down_revision = "20260606_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("files", sa.Column("user_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        op.f("fk_files_user_id_users"),
        "files",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_files_user_id_users"), "files", type_="foreignkey")
    op.drop_column("files", "user_id")
