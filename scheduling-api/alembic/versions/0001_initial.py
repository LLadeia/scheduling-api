"""Initial PostgreSQL schema; reviewed exclusion constraint, not autogenerate.

Revision ID: 0001
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("""
    CREATE TABLE users (
        id SERIAL PRIMARY KEY, email VARCHAR(254) NOT NULL,
        password_hash VARCHAR(255) NOT NULL, role VARCHAR(16) NOT NULL DEFAULT 'client',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT users_email_key UNIQUE(email), CONSTRAINT ck_users_role CHECK (role IN ('admin','client'))
    );
    """)
    op.execute("""
    CREATE TABLE resources (
        id SERIAL PRIMARY KEY, name VARCHAR(120) NOT NULL, description TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)
    op.execute("""
    CREATE TABLE appointments (
        id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE RESTRICT,
        starts_at TIMESTAMPTZ NOT NULL, ends_at TIMESTAMPTZ NOT NULL,
        status VARCHAR(16) NOT NULL DEFAULT 'scheduled',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_appointments_interval CHECK (ends_at > starts_at),
        CONSTRAINT ck_appointments_status CHECK (status IN ('scheduled','cancelled')),
        CONSTRAINT ex_appointments_no_overlap EXCLUDE USING gist
        (resource_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&)
        WHERE (status = 'scheduled')
    );
    """)
    op.create_index("ix_appointments_user_start", "appointments", ["user_id", "starts_at", "id"])
    op.create_index("ix_appointments_start", "appointments", ["starts_at", "id"])
    op.create_index("ix_appointments_resource_start", "appointments", ["resource_id", "starts_at"])


def downgrade():
    op.drop_table("appointments")
    op.drop_table("resources")
    op.drop_table("users")
    # Preserve extension: it may be shared by other schemas.
