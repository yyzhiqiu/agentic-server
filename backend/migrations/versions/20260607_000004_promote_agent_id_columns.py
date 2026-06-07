"""将会话和运行记录中的 agent_id 提升为一等字段。

修订版本 ID: 20260607_000004
依赖修订: 05caddd65fed
创建日期: 2026-06-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260607_000004"
down_revision = "05caddd65fed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "agent_id",
            sa.String(length=100),
            nullable=True,
            comment="绑定的智能体 ID。",
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE conversations
            SET agent_id = COALESCE(
                NULLIF(metadata ->> 'agent_id', ''),
                'chat_agent'
            )
            WHERE agent_id IS NULL
            """
        )
    )
    op.alter_column(
        "conversations",
        "agent_id",
        existing_type=sa.String(length=100),
        nullable=False,
        server_default="chat_agent",
        comment="绑定的智能体 ID。",
    )

    op.add_column(
        "agent_runs",
        sa.Column(
            "agent_id",
            sa.String(length=100),
            nullable=True,
            comment="执行该次运行的智能体 ID。",
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE agent_runs
            SET agent_id = COALESCE(
                NULLIF(metadata ->> 'agent_id', ''),
                NULLIF(output ->> 'agent_id', ''),
                NULLIF(input ->> 'agent_id', ''),
                NULLIF(input -> 'metadata' ->> 'agent_id', ''),
                (
                    SELECT conversations.agent_id
                    FROM conversations
                    WHERE conversations.id = agent_runs.conversation_id
                ),
                'chat_agent'
            )
            WHERE agent_id IS NULL
            """
        )
    )
    op.alter_column(
        "agent_runs",
        "agent_id",
        existing_type=sa.String(length=100),
        nullable=False,
        server_default="chat_agent",
        comment="执行该次运行的智能体 ID。",
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "agent_id")
    op.drop_column("conversations", "agent_id")
