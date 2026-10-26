# Regras, concorrência e autenticação

## Regras do domínio

1. `ends_at > starts_at`; duração variável.
2. Criação e reagendamento exigem início futuro, verificado após adquirir locks.
3. Criação/reagendamento exigem sala ativa; cancelamento pode ocorrer em sala inativa.
4. Uma sala tem no máximo uma reserva scheduled em cada instante.
5. Intervalos semiabertos `[início, fim)`: 10–11 e 11–12 são adjacentes e permitidos.
6. Salas diferentes podem ter reservas no mesmo intervalo.
7. Cancelamento libera o intervalo, preservando registro e proprietário.
8. Cancelamento definitivo; não existe reativação.
9. Reagendar cancelada retorna 409.
10. Repetir cancelamento retorna registro sem alterar updated_at, inclusive após o horário original.
11. A primeira alteração/cancelamento só pode ocorrer antes do início existente.
12. Salas com histórico são desativadas, com FKs preservadas.
13. Client consulta/modifica apenas reservas próprias; tentativa contra outro cliente retorna 404.
14. Admin modifica qualquer reserva, respeitando estados e horários.
15. Cadastro público fixa client; role e campos extras geram 422.
16. Client não altera proprietário, papel ou sala de reserva existente. Para outra sala, cancele e crie nova.

## Constraint de exclusão

A migração SQL revisada contém:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
CONSTRAINT ex_appointments_no_overlap EXCLUDE USING gist
(resource_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&)
WHERE (status = 'scheduled')
```

O operador `&&` identifica sobreposição. `btree_gist` oferece igualdade do ID inteiro
no mesmo índice GiST que compara os intervalos. A constraint também protege gravações
feitas fora da API. O CHECK do intervalo protege entradas inválidas diretamente no banco.
Uma consulta prévia não é suficiente: duas transações poderiam observar o mesmo horário
livre. Aqui o PostgreSQL arbitra a disputa; uma grava e a outra recebe SQLSTATE `23P01`.

O service reconhece especificamente **23P01 + nome ex_appointments_no_overlap**, executa
rollback e responde 409. E-mail duplicado tem tratamento próprio de **23505 + users_email_key**.
Outros erros de integridade não viram falsos conflitos de agenda. O rollback desfaz
um reagendamento inteiro, preservando o horário anterior.

Alterações fazem `SELECT ... FOR UPDATE` na reserva, sob o isolamento padrão READ COMMITTED.
O segundo escritor aguarda o primeiro; após o lock recebe o estado confirmado mais
recente e verifica as regras novamente. Isso impede sobrescrever cancelled com um
reagendamento. Não há versão/ETag: duas alterações válidas sucessivas são serializadas,
e a última pode definir o horário final se ambas forem permitidas.

Criação/reagendamento usa `FOR SHARE` na sala até o commit. São locks compatíveis entre
criadores, permitindo a disputa real na exclusão. A alteração/desativação de sala usa
`FOR UPDATE`, que aguarda esses leitores e evita reservar sala já desativada. O caminho
de edição sempre bloqueia primeiro a reserva e depois a sala. Alterar sala não bloqueia
reservas, evitando um ciclo inverso entre esses caminhos.

## JWT, RBAC e propriedade

Senha: Argon2id via pwdlib. Login compara também um hash fictício quando não há usuário;
a mensagem 401 é genérica. Hashing roda em threadpool para não bloquear o event loop.
Tokens têm `sub`, `iat`, `exp`, `iss`, `aud`. O verificador exige essas claims e fixa
`algorithms=["HS256"]`, valida assinatura, expiração, emissor e audiência, sem aceitar
algoritmo escolhido pelo token. O segredo vem de configuração, mínimo de 32 caracteres;
o gerador local usa entropia criptográfica.

Validação criptográfica do access token dispensa sessão tradicional armazenada por login.
**A aplicação completa mantém estado**: usuários, papéis, recursos e reservas no banco.
Após validar JWT, ela consulta usuário ativo e o papel atual. Alterações no banco têm
efeito mesmo com um token emitido anteriormente. Não há blacklist/logout revogador,
refresh token nem rotação automática de segredo no núcleo; validade padrão é 15 minutos.

Autenticação identifica; RBAC permite administração; verificação de propriedade limita
qual registro o cliente pode usar. A consulta de reserva já filtra o proprietário antes
de carregar/bloquear a linha. Não há vazamento por diferença entre inexistente e alheia.

A limitação de login usa janela móvel de 60 s por IP da conexão, cinco tentativas
com corpo válido, incluindo logins bem-sucedidos. Não confia em X-Forwarded-For; Uvicorn
sobe com `--no-proxy-headers`. Atrás de proxy, configure identificação confiável e contador
compartilhado; do contrário todos podem compartilhar o IP do proxy. O contador tem alcance
de **um processo**, é limitado a 10 mil chaves e retorna 429 sob saturação sem descartar
limites ativos. Não basta para múltiplos workers/réplicas: usar Redis é extensão.

Logs JSON registram UUID gerado, método, rota **template**, status, duração e timestamp.
Não incluem corpo, query, senha, token ou headers de autenticação. Access logs padrão
são desativados nos comandos documentados; não habilite logging SQL de parâmetros.

## Datas, HTTP e limites

Entrada exige fuso (`Z` ou offset); intervalo é normalizado para UTC e saída usa UTC.
Banco armazena TIMESTAMPTZ; não atribua fuso silenciosamente a datas ingênuas.
A disponibilidade é informativa e tem janela padrão máxima 31 dias, configurável.
Paginação usa índice usuário/início e início/id; GiST protege intervalo por sala.

Criações retornam 201 + Location; leitura/PATCH retornam 200. PATCH tem união explícita
com discriminador action: cancel ou reschedule. Cancelamento é idempotente; POST de
reserva não tem chave de idempotência. A API usa rotas, verbos e status HTTP, mas não
implementa HATEOAS e não deve ser apresentada como Richardson nível 3.

## Fontes oficiais consultadas

- FastAPI, JWT e pwdlib: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- PostgreSQL 17, ranges: https://www.postgresql.org/docs/17/rangetypes.html
- PostgreSQL 17, btree_gist: https://www.postgresql.org/docs/17/btree-gist.html
- SQLAlchemy, AsyncSession por tarefa: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Alembic, asyncio: https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
- PyJWT, validação de claims: https://pyjwt.readthedocs.io/en/stable/usage.html
- Pydantic, AwareDatetime: https://docs.pydantic.dev/latest/api/types/#pydantic.types.AwareDatetime

As versões diretas e transitivas usadas estão fixadas em requirements.txt e
requirements-dev.txt; arquivos .in registram dependências escolhidas.
