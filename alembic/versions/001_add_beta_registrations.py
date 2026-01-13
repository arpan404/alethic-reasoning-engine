"""Add beta_registrations table

Revision ID: 001_add_beta_registrations
Revises: 
Create Date: 2026-01-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '001_add_beta_registrations'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create beta_registrations table."""
    op.create_table(
        'beta_registrations',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('job_title', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('use_case', sa.Text(), nullable=True),
        sa.Column('referral_source', sa.String(length=100), nullable=True),
        sa.Column('newsletter_opt_in', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_beta_registrations_email'),
    )
    op.create_index('idx_beta_registrations_email', 'beta_registrations', ['email'])
    op.create_index('idx_beta_status_created', 'beta_registrations', ['status', 'created_at'])
    op.create_index('idx_beta_email_status', 'beta_registrations', ['email', 'status'])


def downgrade() -> None:
    """Drop beta_registrations table."""
    op.drop_index('idx_beta_email_status', table_name='beta_registrations')
    op.drop_index('idx_beta_status_created', table_name='beta_registrations')
    op.drop_index('idx_beta_registrations_email', table_name='beta_registrations')
    op.drop_table('beta_registrations')
