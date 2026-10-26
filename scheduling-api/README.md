# API de Agendamento de Salas — TFG

Projeto individual de Engenharia da Computação. API REST em Python 3.12, FastAPI,
SQLAlchemy 2, PostgreSQL 17, JWT HS256 e RBAC. Duas funções: `admin` e `client`.
Reservas de duração variável, uma reserva por sala a cada intervalo.

## Começar com Docker (Linux, Windows ou macOS)

Pré-requisitos: Python 3.12 para gerar a configuração e Docker Engine com Compose v2+
(ou Docker Desktop iniciado). Execute na pasta que contém este README.

```bash
python scripts/init_env.py
docker compose up -d --build
# O serviço migrate executa alembic upgrade head após o healthcheck do banco.
docker compose ps
docker compose logs migrate
docker compose exec api python -m scripts.create_admin --email admin@example.com
```

No Linux pode ser necessário usar `python3`. A senha administrativa é solicitada
sem eco e confirmada; mínimo de 12 e máximo de 128 caracteres. Ela não é argumento CLI.
O gerador recusa sobrescrever `.env` e gera senhas e segredo aleatórios sem imprimi-los.
`.env.example` mostra as variáveis possíveis, com valores fictícios; não copie seus
placeholders como segredos reais. O arquivo `.env` não deve ser versionado.

- Swagger: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Prontidão: <http://localhost:8000/health>
- Vitalidade: <http://localhost:8000/health/live>

Migração explícita para revisões posteriores (antes de reiniciar a API):

```bash
docker compose run --rm migrate
docker compose up -d api
```

Um banco vazio passa pela migração antes da API. O banco usa volume persistente,
rede própria e não publica porta no host. A API usa usuário UID 10001 e só publica
porta no loopback. `docker compose down` para os serviços sem apagar o volume.
Faça backup antes de qualquer mudança destrutiva no banco.

## Primeiro uso

O login recebe JSON. Use o token retornado em `Authorization: Bearer ...`.
No Swagger, cole apenas o token no botão **Authorize** após fazer login.
As senhas dos exemplos abaixo são fictícias, próprias para estudo local.

```bash
curl -i http://localhost:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"cliente@example.com","password":"senha-local-exemplo-123"}'
curl http://localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"cliente@example.com","password":"senha-local-exemplo-123"}'
curl http://localhost:8000/users/me -H 'Authorization: Bearer TOKEN_CLIENTE'

# Faça login também com o admin criado pelo comando administrativo.
curl -i http://localhost:8000/resources -H 'Authorization: Bearer TOKEN_ADMIN' \
  -H 'Content-Type: application/json' -d '{"name":"Sala de reuniões","description":"Sala principal"}'
curl -i http://localhost:8000/appointments -H 'Authorization: Bearer TOKEN_CLIENTE' \
  -H 'Content-Type: application/json' \
  -d '{"resource_id":1,"starts_at":"2030-01-10T13:00:00Z","ends_at":"2030-01-10T14:00:00Z"}'
curl http://localhost:8000/appointments -H 'Authorization: Bearer TOKEN_CLIENTE'
curl -X PATCH http://localhost:8000/appointments/1 -H 'Authorization: Bearer TOKEN_CLIENTE' \
  -H 'Content-Type: application/json' \
  -d '{"action":"reschedule","starts_at":"2030-01-10T15:00:00Z","ends_at":"2030-01-10T16:00:00Z"}'
curl -X PATCH http://localhost:8000/appointments/1 -H 'Authorization: Bearer TOKEN_CLIENTE' \
  -H 'Content-Type: application/json' -d '{"action":"cancel"}'
```

Escolha datas futuras ao executar. Reenviar a criação original antes do cancelamento
retorna 409 por sobreposição. Repetir o cancelamento retorna 200 com o mesmo registro.
Um cliente diferente recebe 404 para consultar ou alterar essa reserva.

## Endpoints e contratos

| Método | Rota | Permissão / comportamento |
|---|---|---|
| POST | `/auth/register` | Público; somente client; 201 e Location `/users/me` |
| POST | `/auth/login` | Público; JSON email/password; 200 com JWT; limite 5/min/IP |
| GET | `/users/me` | Usuário ativo; seu perfil sem hash |
| GET | `/resources` | Autenticado; salas ativas e inativas, ordenadas por id |
| GET | `/resources/{id}` | Autenticado; resolução do Location da criação |
| POST | `/resources` | Admin; 201 e Location |
| PATCH | `/resources/{id}` | Admin; name, description e/ou is_active |
| GET | `/resources/{id}/availability` | Autenticado; starts_at e ends_at com fuso, até 31 dias |
| POST | `/appointments` | Autenticado; proprietário é o usuário atual; 201 e Location |
| GET | `/appointments` | Cliente vê suas reservas; admin vê todas |
| GET | `/appointments/{id}` | Próprio cliente ou admin |
| PATCH | `/appointments/{id}` | action `cancel` ou `reschedule`, próprio cliente ou admin |
| GET | `/health` | Público; banco e revisão 0001 disponíveis: 200; falha: 503 |
| GET | `/health/live` | Público; aplicação em execução: 200 |

`GET /appointments` aceita `page >= 1`, `1 <= limit <= 100`, `starts_from`,
`starts_before`, `status` e `user_id` (apenas admin). Os filtros de data selecionam
**o início** das reservas em `[starts_from, starts_before)`, não todo intervalo
intersectante. Resposta: `items`, `total`, `page`, `limit`. Ordem `starts_at, id`;
uma consulta SQL obtém total e página no mesmo snapshot, inclusive páginas vazias.

A disponibilidade retorna `free_intervals`, sem dados dos proprietários. Recurso
inativo retorna lista vazia. Consultá-la não garante uma futura reserva.

Erros: 401 token/credenciais; 403 privilégio insuficiente; 404 registro inexistente
ou de outro cliente; 409 horário/estado proibido ou e-mail duplicado; 422 entrada
ou regra temporal inválida; 429 tentativas excedidas. Swagger descreve schemas,
autenticação e respostas. Nenhum schema permite campos extras para promover usuário
ou transferir proprietário/recurso da reserva.

## Desenvolvimento sem Docker

Requer PostgreSQL **17** real, com permissão para instalar `btree_gist` no banco.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Gere `.env` com `python scripts/init_env.py`. Altere `DATABASE_URL` para a conexão
real do seu PostgreSQL: `postgresql+asyncpg://usuario:senha@localhost:5432/scheduling`.
Crie o banco previamente com seu administrador PostgreSQL. Não imprima segredos
em relatórios nem salve o `.env` no Git.

```bash
alembic upgrade head
python -m scripts.create_admin --email admin@example.com
uvicorn app.main:app --reload --no-access-log --no-proxy-headers
```

A inicialização exige `DATABASE_URL` PostgreSQL/asyncpg e `JWT_SECRET` de ao menos
32 caracteres. O papel vem do banco em cada requisição. O segredo deve ser aleatório.
O teste de prontidão confirma a revisão esperada; atualize esse requisito ao criar
futuras migrações.

## Testes e qualidade

Ambiente isolado e descartável com Docker:

```bash
docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.test.yaml down
```

Ou crie um banco separado chamado `scheduling_test`, configure ambas as variáveis
no terminal e rode localmente:

```bash
# Linux/macOS, substitua a conexão por credenciais de TESTE:
export TEST_DATABASE_URL='postgresql+asyncpg://usuario:senha@localhost:5432/scheduling_test'
export DATABASE_URL="$TEST_DATABASE_URL"
export JWT_SECRET='segredo-ficticio-apenas-testes-minimo-32-caracteres'
alembic upgrade head
ruff check .
ruff format --check .
pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-report=html \
  --cov-fail-under=80 --junitxml=junit.xml
docker build --target production -t scheduling-api:local .
```

No PowerShell use `$env:TEST_DATABASE_URL = '...'`,
`$env:DATABASE_URL = $env:TEST_DATABASE_URL` e `$env:JWT_SECRET = '...'`.
Os testes truncam tabelas **somente** em um banco cujo nome termine em `_test`.
Não há fallback para SQLite nem skip silencioso para integração indisponível.
A suíte é sequencial; não use xdist sobre um mesmo banco. O teste concorrente
coordena duas sessões reais e disputa o horário 30 vezes. Outro cenário verifica
que um reagendamento aguarda o bloqueio de um cancelamento da mesma reserva.

CI em `.github/workflows/ci.yml`: push/PR, Python 3.12, PostgreSQL 17,
ruff, migrações, pytest/cobertura mínima 80%, relatórios e build Docker.
Falhas não usam `continue-on-error`. Para proteger a main: GitHub Settings → Rules
→ Rulesets → regra para main → exigir pull request e status check `validate`.
Faça isso depois do primeiro CI para o check aparecer. Nenhuma configuração remota
foi alterada, nenhum commit/deploy/publicação foi feito.

## Estudo e apresentação

- [Arquitetura, ER e permissões](docs/architecture.md)
- [Regras, transações e segurança](docs/design.md)
- [Requisitos relacionados aos testes](docs/test-matrix.md)
- [Ensaio de carga e relatório experimental](docs/performance.md)
- [Validações realmente executadas e pendências](docs/validation.md)

O núcleo usa apenas uma organização. Extensões: refresh tokens, e-mail, frontend,
recorrência, múltiplas organizações, IA/WhatsApp, WebSocket e Kubernetes.
A cobertura é uma meta quantitativa; os testes de integridade e autorização são
obrigatórios mesmo quando o percentual já foi alcançado.
