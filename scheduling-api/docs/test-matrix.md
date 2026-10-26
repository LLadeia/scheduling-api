# Requisitos e testes

Execute a suíte completa; as provas de banco exigem PostgreSQL real.

| Requisito | Evidência automatizada |
|---|---|
| Cadastro somente client, extras proibidos, e-mail normalizado | test_register_login |
| Hash Argon2id e login correto/incorreto | test_password_and_token; test_register_login |
| Token ausente/expirado/adulterado, algoritmo/iss/aud, claims obrigatórias | test_invalid_tokens; test_register_login; test_missing_claims_and_subject |
| Usuário ativo e papel atual do banco | test_active_user_current_role |
| Propriedade: A não lê, reagenda ou cancela B | test_permissions |
| Client não cria/edita salas | test_permissions |
| Fim posterior, início futuro, fuso obrigatório | test_invalid_interval; test_utc_and_future; test_intervals_extra_fields_and_started |
| Sobreposição bloqueada e adjacência válida | test_overlap_adjacency_different_resource |
| Recursos diferentes no mesmo horário | test_overlap_adjacency_different_resource |
| Duas conexões disputam horário 30 vezes, respostas 201/409 e uma ativa | test_http_competing_reservations_30_times |
| Constraint funciona sem services | test_database_constraint_without_services |
| Alteração simultânea preserva cancelamento | test_cancel_wins_locked_reschedule |
| Repetição de cancelamento, cancelamento definitivo e horário livre | test_cancel_reuse_and_rollback |
| Reagendamento conflitante faz rollback | test_cancel_reuse_and_rollback |
| Alterações após início recusadas e proprietário/recurso imutáveis | test_intervals_extra_fields_and_started |
| Disponibilidade sem proprietário, limites e recurso inativo | test_resources_and_availability |
| Paginação, filtros, total, admin e propriedade | test_pagination_filters |
| Limitação 429 e expiração da janela | test_limiter_health_and_schema; test_rate_window |
| Migrações vazias, downgrade/upgrade, constraints e tipos | test_migration_roundtrip |
| Prontidão 200/503 e vitalidade 200 | test_limiter_health_and_schema |
| Erro de integridade alheio não vira conflito | test_unrelated_integrity_not_mapped |
| Configuração e PATCH inválidos | test_config_validation; test_invalid_resource_patch |
| Logs estruturados sem corpo/headers | test_structured_logging |
| Falhas impedem CI e cobertura abaixo de 80% falha | Comandos do workflow sem continue-on-error, pytest-cov fail_under=80 |

A coordenação de concorrência usa barreiras no caminho de serviço sem simular banco,
conexões, constraints ou persistência. O teste de escrita fora do service também
executa duas transações independentes com uma barreira. O cenário de cancelamento
confirma uma espera de lock real em pg_stat_activity antes de liberar a transação.
O ciclo de migrações altera somente o banco dedicado `_test`; testes são sequenciais.
