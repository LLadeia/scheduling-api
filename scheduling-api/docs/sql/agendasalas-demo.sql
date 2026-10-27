-- AgendaSalas: executar UMA VEZ em um banco VAZIO PostgreSQL 17.
-- Crie scheduling_demo pelo pgAdmin e abra o Query Tool nesse banco.
-- Inclui schema exato da migração Alembic 0001 e dados fictícios.
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE users (
        id SERIAL PRIMARY KEY, email VARCHAR(254) NOT NULL,
        password_hash VARCHAR(255) NOT NULL, role VARCHAR(16) NOT NULL DEFAULT 'client',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT users_email_key UNIQUE(email), CONSTRAINT ck_users_role CHECK (role IN ('admin','client'))
    );;

CREATE TABLE resources (
        id SERIAL PRIMARY KEY, name VARCHAR(120) NOT NULL, description TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );;

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
    );;

CREATE INDEX ix_appointments_user_start ON appointments (user_id, starts_at, id);

CREATE INDEX ix_appointments_start ON appointments (starts_at, id);

CREATE INDEX ix_appointments_resource_start ON appointments (resource_id, starts_at);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;




-- Dados fictícios, exclusivamente para demonstração local.
-- Senha das três contas: TesteSala@123456
INSERT INTO users (email, password_hash, role) VALUES
('admin.demo@example.com', '$argon2id$v=19$m=65536,t=3,p=4$OWyRxAYjH4kxagR20sUIGg$0xKZXwxONB4GA1y6D6iFzrzv2kRWH6gOaqHanVKdSUg', 'admin'),
('ana.demo@example.com', '$argon2id$v=19$m=65536,t=3,p=4$c3gHvowePwRoJBCEe+T30Q$0OpUjelpmhrGyljwcyoUX/8ZuhzAH3zNYjGJcQgdJfU', 'client'),
('bruno.demo@example.com', '$argon2id$v=19$m=65536,t=3,p=4$aMaUeIOui1v2XDVYLDWU8w$gHelie0IEYjpijlatNfzK78Tf2SpUK7/OMlwRAaHnhA', 'client');
INSERT INTO resources (name, description, is_active) VALUES
('Sala Demo Reuniões', 'Mesa para oito pessoas e tela para apresentação.', true),
('Sala Demo Estudos', 'Espaço silencioso para trabalhos em grupo.', true),
('Sala Demo Manutenção', 'Sala temporariamente indisponível.', false);
-- Doze reservas futuras da Ana, para exercitar paginação (dez itens por página).
-- Horário escolhido: 10h às 11h em America/Sao_Paulo.
INSERT INTO appointments (user_id, resource_id, starts_at, ends_at, status)
SELECT 2, 1,
 ((CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')::date + (7 + n) + TIME '10:00') AT TIME ZONE 'America/Sao_Paulo',
 ((CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')::date + (7 + n) + TIME '11:00') AT TIME ZONE 'America/Sao_Paulo',
 'scheduled'
FROM generate_series(0, 11) AS g(n);
INSERT INTO appointments (user_id, resource_id, starts_at, ends_at, status) VALUES
(3, 2, CURRENT_TIMESTAMP + INTERVAL '8 days', CURRENT_TIMESTAMP + INTERVAL '8 days 1 hour', 'scheduled'),
(2, 2, CURRENT_TIMESTAMP + INTERVAL '9 days', CURRENT_TIMESTAMP + INTERVAL '9 days 1 hour', 'cancelled'),
(2, 2, CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '1 hour', 'scheduled');
COMMIT;
-- Consultas sem expor hashes de senha.
SELECT id, email, role, is_active FROM users ORDER BY id;
SELECT id, name, is_active FROM resources ORDER BY id;
SELECT id, user_id, resource_id, starts_at, ends_at, status FROM appointments ORDER BY starts_at;
