# AgendaSalas

Sistema de agendamento de salas com FastAPI e frontend React/TypeScript.

O código da aplicação, Compose e instruções completas estão em [scheduling-api/README.md](scheduling-api/README.md).

```bash
cd scheduling-api
python3 scripts/init_env.py # somente se .env não existir
# Requer Docker Engine e Compose v2.
docker compose up -d --build
```

Interface: http://localhost:3000 · Swagger: http://localhost:8000/docs
