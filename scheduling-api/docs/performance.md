# Ensaio de desempenho

## Estado

O ensaio formal deve ocorrer no ambiente Docker do projeto com recursos registrados.
Não confunda testes funcionais ou uma execução curta de Locust com os nove ensaios
experimentais. Resultados p50/p95 só devem ser preenchidos com medições reais.
Veja validation.md para distinguir o que foi executado neste ambiente.

## Preparação

Use um banco **novo** `scheduling_load` no mesmo PostgreSQL 17 ou em instância própria.
Não use o banco de aplicação ou teste: o seed recusa bancos sem sufixo `_load` e recusa
banco com usuários existentes. Configure DATABASE_URL para esse banco no terminal,
JWT_SECRET igual ao da API de carga e ACCESS_TOKEN_MINUTES=120, suficientes para
cada repetição; o runner renova os tokens antes de cada uma. Todos os comandos a seguir
rodam num ambiente Python 3.12 com `pip install -r requirements-dev.txt`.

```bash
# Exemplo Linux, substitua as credenciais de ambiente local dedicado.
export DATABASE_URL='postgresql+asyncpg://usuario:senha@localhost:5432/scheduling_load'
export JWT_SECRET='segredo-local-dedicado-a-carga-minimo-32-caracteres'
export ACCESS_TOKEN_MINUTES=120
alembic upgrade head
python -m scripts.seed_load
uvicorn app.main:app --host 127.0.0.1 --port 8001 --no-access-log --no-proxy-headers
# Em outro terminal, com as mesmas variáveis e ambiente:
python -m scripts.run_load --host http://127.0.0.1:8001 \
  --environment-notes 'Preencher CPU, RAM, SO, versões Python/PostgreSQL/Docker, workers, limites, rede e máquina geradora'
```

No Docker, crie previamente `scheduling_load` pelo administrador e use uma segunda
API dev apontada para esse banco. Uma alternativa com a rede Compose existente:

```bash
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" scheduling_load'
docker build --target dev -t scheduling-api:dev .
# Defina uma configuração de carga dedicada, apontando @db para scheduling_load.
# Não inclua esse arquivo no Git nem use a API de produção para carga.
docker run --rm --network scheduling-api_backend --env-file .env.load \
  scheduling-api:dev alembic upgrade head
docker run --rm --network scheduling-api_backend --env-file .env.load \
  -v "$PWD/reports:/app/reports" scheduling-api:dev python -m scripts.seed_load
```

A rede acima supõe pasta/projeto Compose `scheduling-api`; confira o nome com
`docker network ls`. Garanta que o UID 10001 possa escrever em reports no host.
Para API de carga e runner, use processos separados da imagem dev na mesma rede
com `.env.load`, volume reports e `--host http://NOME_API_CARGA:8000`. O runner usa
localhost:8090 apenas dentro do próprio container para controlar Locust.
O script não depende de acesso público, não altera usuários de produção e não
reduz o limite de login da API: gera tokens somente para os usuários sintéticos.

## Protocolo

- Seed: 100 usuários, 10 salas, 10.000 reservas scheduled sem sobreposição.
- Uma instância de Locust (sem workers distribuídos); contas diferentes por usuário virtual.
- Pesos das tarefas: 4 leituras de GET /appointments para 1 criação. É uma distribuição
  probabilística esperada de 80%/20%; confira a proporção efetiva nos CSVs.
- Escritas usam slots livres pré-definidos por rodada, conta e contador, com intervalos
  de 20 minutos e espaçamento de 30 minutos; não disputam slots já usados no seed.
- 1, 10 e 25 usuários simultâneos; 3 repetições cada: nove execuções.
- 30 s aquecendo; reset de estatísticas; 180 s de medição.
- O runner salva ambiente, CSVs de Locust, logs, JSON final e summary.csv.
- Cada repetição renova tokens. A distribuição dos slots exige uma única instância
  do runner; iniciar workers com o mesmo arquivo duplicaria os slots.
- Seed é executado uma vez, reservas novas acumulam nas repetições; registre os totais
  antes/depois. Para comparar implementações, recomece com banco `_load` novo e mesmo seed.

Meta inicial: p95 de leituras simples < 300 ms com 10 usuários, sem erros inesperados.
A soma de leituras e escritas não substitui a métrica separada das leituras. Compare
as três repetições, mostre dispersão e não descarte resultados ruins. Locust arredonda
latências por buckets; descreva essa precisão no relatório.

## Modelo de relatório

**Data:** pendente. **Commit/versão:** pendente. **CPU/RAM/SO:** pendente.
**PostgreSQL/Python/Docker:** pendente. **Workers/pool/limites:** pendente.
**Gerador de carga/rede:** pendente. **Tamanho inicial/final do banco:** pendente.

| Usuários | Repetição | p50 leitura (ms) | p95 leitura (ms) | Vazão total (req/s) | Erros inesperados | % leitura |
|---|---|---|---|---|---|---|
| 1 | 1, 2, 3 (uma linha por repetição) | Pendente | Pendente | Pendente | Pendente | Pendente |
| 10 | 1, 2, 3 (uma linha por repetição) | Pendente | Pendente | Pendente | Pendente | Pendente |
| 25 | 1, 2, 3 (uma linha por repetição) | Pendente | Pendente | Pendente | Pendente | Pendente |

**Análise:** comparar a meta de 300 ms, erros, índices, plano EXPLAIN ANALYZE,
latência do banco, pool, CPU do hashing se houver login, custo de logs e saturação.
**Conclusão experimental:** somente após medições. **Ameaças à validade:** carga
sintética, máquina geradora compartilhada, crescimento do banco e rede local.
