# Evidências e estado da entrega

Validação realizada em 13/10/2026. Projeto implementado neste workspace vazio;
nenhum arquivo do usuário foi substituído. Não havia AGENTS.md ou código anterior.
Nenhum commit, envio a repositório, publicação ou deploy foi realizado.

## Resultado verificado

| Verificação | Resultado real | Evidência |
|---|---|---|
| Instalação e resolução dos locks | 69 pacotes compatíveis | evidence/dependencies.txt |
| Ruff lint | Passou | evidence/lint.txt |
| Ruff formatação | Passou | evidence/format.txt |
| Compilação sintática Python | Passou | evidence/syntax.txt |
| Alembic em banco vazio | Passou, revisão 0001 | evidence/migrations.txt |
| Testes unitários e integração PostgreSQL real | 34 passaram, sem avisos | evidence/tests.txt; evidence/junit.xml |
| Cobertura de linhas | 479/540 = 88,70% | evidence/coverage.xml |
| Cobertura combinada de linhas/branches, exigência 80% | 85,00%, passou | evidence/tests.txt |
| Disputa de intervalo com duas transações | 30 rodadas: 201/409 e uma ativa em cada | test_http_competing_reservations_30_times na suíte |
| Constraint sem service e cancelamento/reagendamento concorrentes | Passaram | test_database_constraint_without_services; test_cancel_wins_locked_reschedule |
| Comando admin com senha protegida | Passou via terminal PTY, senha sem eco | evidence/http-smoke.txt |
| Fluxo HTTP real completo via Uvicorn | Passou | evidence/http-smoke.txt |
| OpenAPI exportada da API em execução | Gerada | openapi.json |
| Seed sintético | 100 usuários, 10 salas, 10.000 reservas | evidence/load-smoke.txt |
| Locust, tentativa curta | Bloqueada pelo ambiente, não concluiu requisições | evidence/load-smoke.txt |
| Docker Compose e build | Não executáveis: Docker ausente, exit 127 | evidence/docker.txt |
| GitHub Actions | Workflow escrito; execução remota pendente | ../.github/workflows/ci.yml |
| Experimento formal de carga | Pendente, sem resultado p95 formal | performance.md |

O smoke HTTP usa Uvicorn e conexões reais, além dos testes HTTPX em processo. Ele
confirma cadastro, login, sala, criação 201, sobreposição 409, outro cliente 404,
reagendamento 200, cancelamento 200, repetição 200 e endpoints de saúde.
A senha gerada para o smoke nunca foi salva no pacote e a saída do comando admin
foi verificada para confirmar ausência de eco. Tokens não aparecem nas evidências.

## Ambiente e limitações da validação

Python 3.12.14; Linux x86_64; PostgreSQL 17.9 compilado da fonte oficial. As versões
Python diretas e transitivas estão nos dois arquivos requirements fixados. O ambiente
não fornece Docker nem PostgreSQL pré-instalados. Para provar integridade, foi criada
uma instância temporária local de PostgreSQL, com btree_gist real.

O namespace deste ambiente mapeia somente UID 0. **Somente a cópia temporária do código
PostgreSQL usada para teste** teve removidas as recusas de inicialização por UID 0,
sem alterar SQL, transações, constraints ou locks. A instância ficou no loopback,
sem socket Unix, com autenticação trust restrita ao ambiente temporário de teste.
Essas adaptações não integram o projeto entregue nem as imagens PostgreSQL do Compose.
A imagem de execução da API define usuário sem privilégios.

Processos e rede são isolados entre execuções neste ambiente; servidor, migrações,
API e testes foram coordenados na mesma execução. No ensaio curto, Locust falhou
antes de enviar carga: `psutil.NoSuchProcess` ao consultar seu próprio PID via /proc.
A evidência contém a falha real. Não foram fabricadas latências ou vazão, e esse
smoke não substitui o protocolo experimental de 30 s + 180 s, nove rodadas.

## Comandos efetivamente usados

A configuração de teste apontou para um banco PostgreSQL temporário chamado
`scheduling_test`; a fixture confirmou o sufixo `_test` antes de truncar tabelas.
Não compartilhe credenciais reais em relatórios. Os comandos foram:

```bash
uv pip sync --python .venv/bin/python scheduling-api/requirements-dev.txt
uv pip check --python .venv/bin/python
# Na pasta scheduling-api, com variáveis do banco de teste:
python -m alembic upgrade head
python -m pytest --cov=app --cov-report=term-missing \
  --cov-report=xml:docs/evidence/coverage.xml --cov-fail-under=80 \
  --junitxml=docs/evidence/junit.xml -q
ruff check .
ruff format --check .
python -m compileall -q app scripts tests alembic
# Banco separado scheduling_load:
python -m scripts.seed_load --output /tmp/scheduling-load-users.json
# API real para smoke funcional:
uvicorn app.main:app --host 127.0.0.1 --port 8001 --no-access-log --no-proxy-headers
# Tentativa curta de carga (falhou pela restrição de /proc):
locust -f scripts/locustfile.py --headless --host http://127.0.0.1:8001 \
  --users 2 --spawn-rate 2 --run-time 5s --only-summary
```

## Pendências para concluir todos os critérios do anexo

1. Rodar Compose e build em host com Docker, seguindo README, e anexar saídas reais.
2. Após envio autorizado a um repositório, executar o workflow CI no GitHub e configurar
   o check obrigatório `validate` na branch principal. Nenhuma configuração remota foi alterada.
3. Executar os nove ensaios no ambiente de avaliação, preencher o relatório e analisar
   p95 de leituras com 10 usuários. Os scripts estão entregues; medição formal pendente.

O núcleo funcional foi implementado e validado com PostgreSQL real. **O critério
completo de conclusão que inclui build Docker ainda depende da primeira pendência.**

## Decisões para explicar à banca

- Uma API com JWT ainda guarda estado de usuários, papéis e reservas no banco.
- JWT identifica o usuário; papel atual e propriedade determinam a autorização.
- Constraint GiST impede a corrida entre duas consultas de disponibilidade.
- Intervalos semiabertos permitem horários adjacentes.
- Locks de linha serializam alterações na mesma reserva; rollback preserva o horário
  anterior quando um reagendamento conflita.
- SHARE na sala permite criações simultâneas e coordena desativação.
- Testes PostgreSQL reais provam comportamento que SQLite não representa.
- Cobertura mede execução, não substitui cenários críticos de concorrência e segurança.
- CI valida alterações; publicação de imagem e deploy não fazem parte da entrega.
- Resultados de desempenho exigem medições reais e descrição do ambiente.
