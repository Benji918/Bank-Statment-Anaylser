"""first migrations

Revision ID: 9019b8d585f6
Revises: 7f4276fdb496
Create Date: 2025-06-29 14:40:28.377072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9019b8d585f6'
down_revision: Union[str, None] = '7f4276fdb496'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('company', sa.String(length=255), nullable=True),
    sa.Column('role', sa.Enum('ADMIN', 'USER', 'PREMIUM', name='userrole'), nullable=False),
    sa.Column('subscription_tier', sa.Enum('FREE', 'BASIC', 'PROFESSIONAL', 'ENTERPRISE', name='subscriptiontier'), nullable=False),
    sa.Column('last_login', sa.DateTime(), nullable=True),
    sa.Column('email_verified', sa.String(length=1), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('avatar_url', sa.Text(), nullable=True),
    sa.Column('preferences', sa.Text(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_table('statements',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=False),
    sa.Column('file_type', sa.String(length=50), nullable=False),
    sa.Column('cloudinary_public_id', sa.String(length=255), nullable=True),
    sa.Column('cloudinary_url', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED', 'DELETED', name='statementstatus'), nullable=False),
    sa.Column('processing_started_at', sa.String(length=50), nullable=True),
    sa.Column('processing_completed_at', sa.String(length=50), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('category', sa.Enum('PERSONAL', 'BUSINESS', 'INVESTMENT', 'CREDIT_CARD', name='statementcategory'), nullable=False),
    sa.Column('bank_name', sa.String(length=100), nullable=True),
    sa.Column('account_type', sa.String(length=50), nullable=True),
    sa.Column('account_number_masked', sa.String(length=20), nullable=True),
    sa.Column('statement_period_start', sa.String(length=50), nullable=True),
    sa.Column('statement_period_end', sa.String(length=50), nullable=True),
    sa.Column('tags', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_statements_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_statements'))
    )
    op.create_index(op.f('ix_statements_id'), 'statements', ['id'], unique=False)
    op.create_table('analyses',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('statement_id', sa.Integer(), nullable=False),
    sa.Column('analysis_type', sa.String(length=50), nullable=False),
    sa.Column('model_version', sa.String(length=50), nullable=False),
    sa.Column('processing_time_seconds', sa.Float(), nullable=True),
    sa.Column('total_income', sa.Float(), nullable=True),
    sa.Column('total_expenses', sa.Float(), nullable=True),
    sa.Column('net_cash_flow', sa.Float(), nullable=True),
    sa.Column('opening_balance', sa.Float(), nullable=True),
    sa.Column('closing_balance', sa.Float(), nullable=True),
    sa.Column('transaction_categories', sa.JSON(), nullable=True),
    sa.Column('spending_patterns', sa.JSON(), nullable=True),
    sa.Column('income_analysis', sa.JSON(), nullable=True),
    sa.Column('anomalies', sa.JSON(), nullable=True),
    sa.Column('insights', sa.JSON(), nullable=True),
    sa.Column('recommendations', sa.JSON(), nullable=True),
    sa.Column('risk_assessment', sa.JSON(), nullable=True),
    sa.Column('financial_health_score', sa.Float(), nullable=True),
    sa.Column('transactions_data', sa.JSON(), nullable=True),
    sa.Column('excel_data_summary', sa.JSON(), nullable=True),
    sa.Column('summary_text', sa.Text(), nullable=True),
    sa.Column('detailed_analysis', sa.Text(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['statement_id'], ['statements.id'], name=op.f('fk_analyses_statement_id_statements')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_analyses_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_analyses'))
    )
    op.create_index(op.f('ix_analyses_id'), 'analyses', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_analyses_id'), table_name='analyses')
    op.drop_table('analyses')
    op.drop_index(op.f('ix_statements_id'), table_name='statements')
    op.drop_table('statements')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    # ### end Alembic commands ###
