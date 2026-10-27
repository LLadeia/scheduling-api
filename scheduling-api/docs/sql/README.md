# Banco de demonstração no pgAdmin

Requer PostgreSQL 17 e pgAdmin instalado no computador. Os dados são fictícios,
com senhas públicas de demonstração. Use apenas localmente.

1. Se o banco existente estiver recusando a senha, corrija a autenticação antes.
   O arquivo SQL não altera a senha do PostgreSQL nem apaga o volume existente.
2. Na pasta do Compose, execute:
   `docker compose -f compose.yaml -f compose.pgadmin.yaml up -d db`
3. No pgAdmin do Windows, registre um servidor: nome AgendaSalas; host `localhost`;
   porta `5433`; Maintenance database `postgres`; usuário igual ao POSTGRES_USER
   do `.env` (padrão scheduling); senha igual à senha real desse usuário no banco.
   A senha não é a senha das contas web de teste abaixo.
4. Em Databases > Create > Database, crie `scheduling_demo` com o mesmo usuário
   como proprietário. Não remova o banco scheduling já existente.
5. Abra o Query Tool especificamente em `scheduling_demo`, abra
   `agendasalas-demo.sql` e execute o arquivo completo UMA VEZ. O banco deve estar
   vazio. O script cria o schema real da migração 0001, registra a revisão Alembic
   e adiciona os exemplos dentro de uma transação. Não contém DROP/TRUNCATE.
6. No `.env`, altere SOMENTE o nome do banco ao final de DATABASE_URL para
   `/scheduling_demo`. Preserve usuário, senha e host interno `db:5432`.
   Não use localhost:5433 na URL dos containers. Não sobrescreva seu .env.
7. Execute `docker compose -f compose.yaml -f compose.pgadmin.yaml up -d`.
   A migração reconhecerá a revisão 0001. Abra http://localhost:3000.

Contas de demonstração (não são credenciais do PostgreSQL):

| Papel | E-mail | Senha de teste |
| --- | --- | --- |
| Administrador | admin.demo@example.com | TesteSala@123456 |
| Cliente | ana.demo@example.com | TesteSala@123456 |
| Cliente | bruno.demo@example.com | TesteSala@123456 |

Dados: duas salas ativas e uma inativa; 12 reservas futuras da Ana para testar
paginação; uma futura do Bruno; uma cancelada e uma já iniciada da Ana. As 12
reservas começam às 10h de São Paulo, em dias diferentes, a partir de sete dias
após a execução. Confirme as datas na interface e tente reservar 10h30–11h30 no
mesmo dia/sala para testar conflito 409. Reagende uma reserva futura e cancele com
confirmação. A Ana não deve ver a reserva do Bruno; o administrador vê todas.

Validação realizada: importação completa em banco temporário PostgreSQL 17;
contagens 3 usuários, 3 salas, 15 reservas e revisão Alembic 0001.

Para voltar ao banco original, restaure apenas o nome do banco em DATABASE_URL e
recrie os serviços com `docker compose -f compose.yaml -f compose.pgadmin.yaml up -d`.
Os dados do banco original não são modificados pelo SQL de demonstração.
