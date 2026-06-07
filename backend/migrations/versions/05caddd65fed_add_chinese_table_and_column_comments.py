"""添加中文表注释和字段注释

修订版本: 05caddd65fed
依赖版本: 20260607_000003
创建时间: 2026-06-07 17:34:40.040142
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '05caddd65fed'
down_revision = '20260607_000003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### 以下命令由 Alembic 自动生成，请按需核对。 ###
    op.alter_column('agent_runs', 'conversation_id',
               existing_type=sa.VARCHAR(length=36),
               comment='关联会话 ID。',
               existing_nullable=True)
    op.alter_column('agent_runs', 'user_id',
               existing_type=sa.VARCHAR(length=36),
               comment='发起用户 ID。',
               existing_nullable=True)
    op.alter_column('agent_runs', 'status',
               existing_type=sa.VARCHAR(length=50),
               comment='当前运行状态。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'input',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='序列化后的输入载荷。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'output',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='序列化后的输出载荷。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='运行扩展元数据。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment='主键。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录最后更新时间。',
               existing_nullable=False)
    op.create_table_comment(
        'agent_runs',
        '智能体运行记录。',
        existing_comment=None,
        schema=None
    )
    op.alter_column('api_keys', 'user_id',
               existing_type=sa.VARCHAR(length=36),
               comment='所属用户 ID。',
               existing_nullable=True)
    op.alter_column('api_keys', 'name',
               existing_type=sa.VARCHAR(length=100),
               comment='API Key 展示名称。',
               existing_nullable=False)
    op.alter_column('api_keys', 'key_hash',
               existing_type=sa.VARCHAR(length=255),
               comment='API Key 哈希值。',
               existing_nullable=False)
    op.alter_column('api_keys', 'expires_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='API Key 过期时间。',
               existing_nullable=True)
    op.alter_column('api_keys', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment='主键。',
               existing_nullable=False)
    op.alter_column('api_keys', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('api_keys', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录最后更新时间。',
               existing_nullable=False)
    op.create_table_comment(
        'api_keys',
        '签发给用户的 API Key 记录。',
        existing_comment=None,
        schema=None
    )
    op.alter_column('audit_logs', 'action',
               existing_type=sa.VARCHAR(length=100),
               comment='操作名称。',
               existing_nullable=False)
    op.alter_column('audit_logs', 'result',
               existing_type=sa.VARCHAR(length=50),
               comment='操作结果。',
               existing_nullable=False)
    op.alter_column('audit_logs', 'actor_id',
               existing_type=sa.VARCHAR(length=100),
               comment='操作者标识。',
               existing_nullable=True)
    op.alter_column('audit_logs', 'trace_id',
               existing_type=sa.VARCHAR(length=100),
               comment='请求或链路追踪 ID。',
               existing_nullable=True)
    op.alter_column('audit_logs', 'resource_type',
               existing_type=sa.VARCHAR(length=100),
               comment='影响资源类型。',
               existing_nullable=True)
    op.alter_column('audit_logs', 'resource_id',
               existing_type=sa.VARCHAR(length=100),
               comment='影响资源 ID。',
               existing_nullable=True)
    op.alter_column('audit_logs', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='审计扩展上下文。',
               existing_nullable=False)
    op.alter_column('audit_logs', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment='主键。',
               existing_nullable=False)
    op.alter_column('audit_logs', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('audit_logs', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录最后更新时间。',
               existing_nullable=False)
    op.create_table_comment(
        'audit_logs',
        '重要应用操作的审计日志。',
        existing_comment=None,
        schema=None
    )
    op.alter_column('conversations', 'user_id',
               existing_type=sa.VARCHAR(length=36),
               comment='所属用户 ID。',
               existing_nullable=True)
    op.alter_column('conversations', 'title',
               existing_type=sa.VARCHAR(length=255),
               comment='会话标题。',
               existing_nullable=True)
    op.alter_column('conversations', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='会话扩展元数据。',
               existing_nullable=False)
    op.alter_column('conversations', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment='主键。',
               existing_nullable=False)
    op.alter_column('conversations', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('conversations', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('conversations', 'deleted_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='软删除时间，空值表示记录有效。',
               existing_nullable=True)
    op.create_table_comment(
        'conversations',
        '用户与智能体的会话记录。',
        existing_comment=None,
        schema=None
    )
    op.alter_column('documents', 'file_id',
               existing_type=sa.VARCHAR(length=36),
               comment='来源文件 ID。',
               existing_nullable=True)
    op.alter_column('documents', 'title',
               existing_type=sa.VARCHAR(length=255),
               comment='文档标题。',
               existing_nullable=True)
    op.alter_column('documents', 'content',
               existing_type=sa.TEXT(),
               comment='标准化后的文档内容。',
               existing_nullable=True)
    op.alter_column('documents', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='文档扩展元数据。',
               existing_nullable=False)
    op.alter_column('documents', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment='主键。',
               existing_nullable=False)
    op.alter_column('documents', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('documents', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('documents', 'deleted_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='软删除时间，空值表示记录有效。',
               existing_nullable=True)
    op.create_table_comment(
        'documents',
        '与文件关联的文档内容。',
        existing_comment=None,
        schema=None
    )
    op.alter_column('files', 'user_id',
               existing_type=sa.VARCHAR(length=36),
               comment='所属用户 ID。',
               existing_nullable=True)
    op.alter_column('files', 'filename',
               existing_type=sa.VARCHAR(length=255),
               comment='原始文件名。',
               existing_nullable=False)
    op.alter_column('files', 'content_type',
               existing_type=sa.VARCHAR(length=100),
               comment='文件 MIME 类型。',
               existing_nullable=True)
    op.alter_column('files', 'storage_key',
               existing_type=sa.VARCHAR(length=500),
               comment='文件内容的对象存储键。',
               existing_nullable=True)
    op.alter_column('files', 'size',
               existing_type=sa.BIGINT(),
               comment='文件大小（字节）。',
               existing_nullable=True)
    op.alter_column('files', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='文件扩展元数据。',
               existing_nullable=False)
    op.alter_column('files', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment='主键。',
               existing_nullable=False)
    op.alter_column('files', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('files', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('files', 'deleted_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='软删除时间，空值表示记录有效。',
               existing_nullable=True)
    op.create_table_comment(
        'files',
        '上传文件元数据。',
        existing_comment=None,
        schema=None
    )
    op.alter_column('messages', 'conversation_id',
               existing_type=sa.VARCHAR(length=36),
               comment='所属会话 ID。',
               existing_nullable=False)
    op.alter_column('messages', 'role',
               existing_type=sa.VARCHAR(length=50),
               comment='消息角色，如 user 或 assistant。',
               existing_nullable=False)
    op.alter_column('messages', 'content',
               existing_type=sa.TEXT(),
               comment='消息内容。',
               existing_nullable=False)
    op.alter_column('messages', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='消息扩展元数据。',
               existing_nullable=False)
    op.alter_column('messages', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment='主键。',
               existing_nullable=False)
    op.alter_column('messages', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('messages', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('messages', 'deleted_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='软删除时间，空值表示记录有效。',
               existing_nullable=True)
    op.create_table_comment(
        'messages',
        '会话中的消息记录。',
        existing_comment=None,
        schema=None
    )
    op.alter_column('tool_calls', 'agent_run_id',
               existing_type=sa.VARCHAR(length=36),
               comment='所属智能体运行 ID。',
               existing_nullable=True)
    op.alter_column('tool_calls', 'tool_name',
               existing_type=sa.VARCHAR(length=100),
               comment='工具名称。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'status',
               existing_type=sa.VARCHAR(length=50),
               comment='当前工具调用状态。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'input',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='序列化后的工具输入载荷。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'output',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='序列化后的工具输出载荷。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='工具调用扩展元数据。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment='主键。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录最后更新时间。',
               existing_nullable=False)
    op.create_table_comment(
        'tool_calls',
        '智能体工具调用记录。',
        existing_comment=None,
        schema=None
    )
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(length=255),
               comment='用户邮箱。',
               existing_nullable=True)
    op.alter_column('users', 'name',
               existing_type=sa.VARCHAR(length=100),
               comment='应用内展示名称。',
               existing_nullable=False)
    op.alter_column('users', 'is_active',
               existing_type=sa.BOOLEAN(),
               comment='用户是否处于启用状态。',
               existing_nullable=False)
    op.alter_column('users', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment='主键。',
               existing_nullable=False)
    op.alter_column('users', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('users', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('users', 'deleted_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='软删除时间，空值表示记录有效。',
               existing_nullable=True)
    op.create_table_comment(
        'users',
        '应用用户与访客用户记录。',
        existing_comment=None,
        schema=None
    )
    # ### Alembic 自动生成命令结束。 ###


def downgrade() -> None:
    # ### 以下命令由 Alembic 自动生成，请按需核对。 ###
    op.drop_table_comment(
        'users',
        existing_comment='应用用户与访客用户记录。',
        schema=None
    )
    op.alter_column('users', 'deleted_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='软删除时间，空值表示记录有效。',
               existing_nullable=True)
    op.alter_column('users', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('users', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('users', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='主键。',
               existing_nullable=False)
    op.alter_column('users', 'is_active',
               existing_type=sa.BOOLEAN(),
               comment=None,
               existing_comment='用户是否处于启用状态。',
               existing_nullable=False)
    op.alter_column('users', 'name',
               existing_type=sa.VARCHAR(length=100),
               comment=None,
               existing_comment='应用内展示名称。',
               existing_nullable=False)
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(length=255),
               comment=None,
               existing_comment='用户邮箱。',
               existing_nullable=True)
    op.drop_table_comment(
        'tool_calls',
        existing_comment='智能体工具调用记录。',
        schema=None
    )
    op.alter_column('tool_calls', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='主键。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='工具调用扩展元数据。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'output',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='序列化后的工具输出载荷。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'input',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='序列化后的工具输入载荷。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'status',
               existing_type=sa.VARCHAR(length=50),
               comment=None,
               existing_comment='当前工具调用状态。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'tool_name',
               existing_type=sa.VARCHAR(length=100),
               comment=None,
               existing_comment='工具名称。',
               existing_nullable=False)
    op.alter_column('tool_calls', 'agent_run_id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='所属智能体运行 ID。',
               existing_nullable=True)
    op.drop_table_comment(
        'messages',
        existing_comment='会话中的消息记录。',
        schema=None
    )
    op.alter_column('messages', 'deleted_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='软删除时间，空值表示记录有效。',
               existing_nullable=True)
    op.alter_column('messages', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('messages', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('messages', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='主键。',
               existing_nullable=False)
    op.alter_column('messages', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='消息扩展元数据。',
               existing_nullable=False)
    op.alter_column('messages', 'content',
               existing_type=sa.TEXT(),
               comment=None,
               existing_comment='消息内容。',
               existing_nullable=False)
    op.alter_column('messages', 'role',
               existing_type=sa.VARCHAR(length=50),
               comment=None,
               existing_comment='消息角色，如 user 或 assistant。',
               existing_nullable=False)
    op.alter_column('messages', 'conversation_id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='所属会话 ID。',
               existing_nullable=False)
    op.drop_table_comment(
        'files',
        existing_comment='上传文件元数据。',
        schema=None
    )
    op.alter_column('files', 'deleted_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='软删除时间，空值表示记录有效。',
               existing_nullable=True)
    op.alter_column('files', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('files', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('files', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='主键。',
               existing_nullable=False)
    op.alter_column('files', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='文件扩展元数据。',
               existing_nullable=False)
    op.alter_column('files', 'size',
               existing_type=sa.BIGINT(),
               comment=None,
               existing_comment='文件大小（字节）。',
               existing_nullable=True)
    op.alter_column('files', 'storage_key',
               existing_type=sa.VARCHAR(length=500),
               comment=None,
               existing_comment='文件内容的对象存储键。',
               existing_nullable=True)
    op.alter_column('files', 'content_type',
               existing_type=sa.VARCHAR(length=100),
               comment=None,
               existing_comment='文件 MIME 类型。',
               existing_nullable=True)
    op.alter_column('files', 'filename',
               existing_type=sa.VARCHAR(length=255),
               comment=None,
               existing_comment='原始文件名。',
               existing_nullable=False)
    op.alter_column('files', 'user_id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='所属用户 ID。',
               existing_nullable=True)
    op.drop_table_comment(
        'documents',
        existing_comment='与文件关联的文档内容。',
        schema=None
    )
    op.alter_column('documents', 'deleted_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='软删除时间，空值表示记录有效。',
               existing_nullable=True)
    op.alter_column('documents', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('documents', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('documents', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='主键。',
               existing_nullable=False)
    op.alter_column('documents', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='文档扩展元数据。',
               existing_nullable=False)
    op.alter_column('documents', 'content',
               existing_type=sa.TEXT(),
               comment=None,
               existing_comment='标准化后的文档内容。',
               existing_nullable=True)
    op.alter_column('documents', 'title',
               existing_type=sa.VARCHAR(length=255),
               comment=None,
               existing_comment='文档标题。',
               existing_nullable=True)
    op.alter_column('documents', 'file_id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='来源文件 ID。',
               existing_nullable=True)
    op.drop_table_comment(
        'conversations',
        existing_comment='用户与智能体的会话记录。',
        schema=None
    )
    op.alter_column('conversations', 'deleted_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='软删除时间，空值表示记录有效。',
               existing_nullable=True)
    op.alter_column('conversations', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('conversations', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('conversations', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='主键。',
               existing_nullable=False)
    op.alter_column('conversations', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='会话扩展元数据。',
               existing_nullable=False)
    op.alter_column('conversations', 'title',
               existing_type=sa.VARCHAR(length=255),
               comment=None,
               existing_comment='会话标题。',
               existing_nullable=True)
    op.alter_column('conversations', 'user_id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='所属用户 ID。',
               existing_nullable=True)
    op.drop_table_comment(
        'audit_logs',
        existing_comment='重要应用操作的审计日志。',
        schema=None
    )
    op.alter_column('audit_logs', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('audit_logs', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('audit_logs', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='主键。',
               existing_nullable=False)
    op.alter_column('audit_logs', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='审计扩展上下文。',
               existing_nullable=False)
    op.alter_column('audit_logs', 'resource_id',
               existing_type=sa.VARCHAR(length=100),
               comment=None,
               existing_comment='影响资源 ID。',
               existing_nullable=True)
    op.alter_column('audit_logs', 'resource_type',
               existing_type=sa.VARCHAR(length=100),
               comment=None,
               existing_comment='影响资源类型。',
               existing_nullable=True)
    op.alter_column('audit_logs', 'trace_id',
               existing_type=sa.VARCHAR(length=100),
               comment=None,
               existing_comment='请求或链路追踪 ID。',
               existing_nullable=True)
    op.alter_column('audit_logs', 'actor_id',
               existing_type=sa.VARCHAR(length=100),
               comment=None,
               existing_comment='操作者标识。',
               existing_nullable=True)
    op.alter_column('audit_logs', 'result',
               existing_type=sa.VARCHAR(length=50),
               comment=None,
               existing_comment='操作结果。',
               existing_nullable=False)
    op.alter_column('audit_logs', 'action',
               existing_type=sa.VARCHAR(length=100),
               comment=None,
               existing_comment='操作名称。',
               existing_nullable=False)
    op.drop_table_comment(
        'api_keys',
        existing_comment='签发给用户的 API Key 记录。',
        schema=None
    )
    op.alter_column('api_keys', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('api_keys', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('api_keys', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='主键。',
               existing_nullable=False)
    op.alter_column('api_keys', 'expires_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='API Key 过期时间。',
               existing_nullable=True)
    op.alter_column('api_keys', 'key_hash',
               existing_type=sa.VARCHAR(length=255),
               comment=None,
               existing_comment='API Key 哈希值。',
               existing_nullable=False)
    op.alter_column('api_keys', 'name',
               existing_type=sa.VARCHAR(length=100),
               comment=None,
               existing_comment='API Key 展示名称。',
               existing_nullable=False)
    op.alter_column('api_keys', 'user_id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='所属用户 ID。',
               existing_nullable=True)
    op.drop_table_comment(
        'agent_runs',
        existing_comment='智能体运行记录。',
        schema=None
    )
    op.alter_column('agent_runs', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录最后更新时间。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment=None,
               existing_comment='记录创建时间。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='主键。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'metadata',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='运行扩展元数据。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'output',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='序列化后的输出载荷。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'input',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='序列化后的输入载荷。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'status',
               existing_type=sa.VARCHAR(length=50),
               comment=None,
               existing_comment='当前运行状态。',
               existing_nullable=False)
    op.alter_column('agent_runs', 'user_id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='发起用户 ID。',
               existing_nullable=True)
    op.alter_column('agent_runs', 'conversation_id',
               existing_type=sa.VARCHAR(length=36),
               comment=None,
               existing_comment='关联会话 ID。',
               existing_nullable=True)
    # ### Alembic 自动生成命令结束。 ###
