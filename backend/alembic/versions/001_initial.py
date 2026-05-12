"""Initial schema — all tables

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('admin','hr','manager','employee','viewer', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ── departments ───────────────────────────────────────────────────────────
    op.create_table('departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('manager_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code'),
    )

    # ── shifts ────────────────────────────────────────────────────────────────
    op.create_table('shifts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('grace_minutes', sa.Integer(), nullable=True, server_default='15'),
        sa.Column('overtime_after_minutes', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── employees ─────────────────────────────────────────────────────────────
    op.create_table('employees',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', sa.String(50), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('shift_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('designation', sa.String(100), nullable=True),
        sa.Column('date_of_joining', sa.Date(), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        # AES-256-GCM encrypted face embedding stored as base64 text
        sa.Column('face_embedding', sa.Text(), nullable=True),
        sa.Column('face_image_url', sa.String(500), nullable=True),
        sa.Column('fingerprint_id', sa.String(100), nullable=True),
        sa.Column('biometric_enrolled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('biometric_enrolled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_employees_employee_id', 'employees', ['employee_id'], unique=True)
    op.create_index('ix_employees_email', 'employees', ['email'], unique=True)

    # FK: department manager → employee
    op.create_foreign_key('fk_dept_manager', 'departments', 'employees', ['manager_id'], ['id'])

    # ── attendance_logs ───────────────────────────────────────────────────────
    op.create_table('attendance_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shift_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('check_in', sa.DateTime(timezone=True), nullable=True),
        sa.Column('check_out', sa.DateTime(timezone=True), nullable=True),
        sa.Column('work_hours', sa.Float(), nullable=True, server_default='0'),
        sa.Column('overtime_hours', sa.Float(), nullable=True, server_default='0'),
        sa.Column('status', sa.Enum('present','absent','late','half_day','on_leave','holiday', name='attendancestatus'), nullable=True),
        sa.Column('method', sa.String(20), nullable=True, server_default="'face'"),
        sa.Column('check_out_method', sa.String(20), nullable=True),
        sa.Column('device_id', sa.String(100), nullable=True),
        sa.Column('check_in_image_url', sa.String(500), nullable=True),
        sa.Column('check_in_location', sa.String(255), nullable=True),
        sa.Column('check_out_location', sa.String(255), nullable=True),
        sa.Column('face_match_score', sa.Float(), nullable=True),
        sa.Column('is_late', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('late_minutes', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('early_out', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('early_out_minutes', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id']),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_attendance_logs_date', 'attendance_logs', ['date'])

    # ── leave_requests ────────────────────────────────────────────────────────
    op.create_table('leave_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('leave_type', sa.Enum('casual','sick','earned','maternity','paternity','unpaid', name='leavetype'), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('days', sa.Float(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending','approved','rejected', name='leavestatus'), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── leave_balances ────────────────────────────────────────────────────────
    op.create_table('leave_balances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('leave_type', sa.Enum('casual','sick','earned','maternity','paternity','unpaid', name='leavetype'), nullable=False),
        sa.Column('entitled', sa.Float(), nullable=True, server_default='0'),
        sa.Column('used', sa.Float(), nullable=True, server_default='0'),
        sa.Column('pending', sa.Float(), nullable=True, server_default='0'),
        sa.Column('carried_fwd', sa.Float(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'year', 'leave_type', name='uq_leave_balance'),
    )

    # ── holidays ──────────────────────────────────────────────────────────────
    op.create_table('holidays',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_optional', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date'),
    )

    # ── geofence_zones ────────────────────────────────────────────────────────
    op.create_table('geofence_zones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('radius_meters', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('bypass_kiosk', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(50), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── password_reset_tokens ─────────────────────────────────────────────────
    op.create_table('password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )


def downgrade() -> None:
    op.drop_table('password_reset_tokens')
    op.drop_table('audit_logs')
    op.drop_table('geofence_zones')
    op.drop_table('holidays')
    op.drop_table('leave_balances')
    op.drop_table('leave_requests')
    op.drop_index('ix_attendance_logs_date', 'attendance_logs')
    op.drop_table('attendance_logs')
    op.drop_constraint('fk_dept_manager', 'departments', type_='foreignkey')
    op.drop_index('ix_employees_email', 'employees')
    op.drop_index('ix_employees_employee_id', 'employees')
    op.drop_table('employees')
    op.drop_table('shifts')
    op.drop_table('departments')
    op.drop_index('ix_users_email', 'users')
    op.drop_table('users')
    for enum in ('userrole','attendancestatus','leavetype','leavestatus'):
        sa.Enum(name=enum).drop(op.get_bind())
