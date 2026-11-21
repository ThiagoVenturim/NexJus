# NexJus backend (opcional)

Servidor FastAPI opcional para quem usa a extensao NexJus em mais de uma maquina. Ele oferece:

- sincronizacao de clientes, veiculos, processos, prazos e feriados locais entre maquinas;
- agenda diaria de prazos (vencidos, vencendo hoje, urgentes ate 3 dias e proximos);
- alerta diario por e-mail com essa agenda;
- healthcheck em `GET /health`.

A extensao funciona sem este backend. Sem ele, os dados ficam apenas no `chrome.storage.local`.

## Instalacao

Requer Python 3.11 ou mais novo.

```bash
cd app
python -m venv .venv
.venv/bin/pip install -e ".[dev]"          # SQLite (padrao)
.venv/bin/pip install -e ".[dev,postgres]" # com driver do Postgres
cp .env.example .env                         # ajuste NEXJUS_API_TOKEN
.venv/bin/nexjus-backend serve               # aplica migracoes e sobe em 127.0.0.1:8000
```

No Windows use `.venv\Scripts\` no lugar de `.venv/bin/`.

## Configuracao

Tudo vem de variaveis de ambiente ou do arquivo `.env` (fora do Git). Veja `.env.example`.

| Variavel | Uso |
| --- | --- |
| `NEXJUS_DATABASE_URL` | URL do SQLAlchemy. Padrao `sqlite:///./nexjus.db`. Postgres: `postgresql+psycopg://usuario:senha@127.0.0.1:5432/nexjus` (codifique caracteres especiais da senha). |
| `NEXJUS_API_TOKEN` | Token Bearer exigido em `/sync/*` e `/agenda` (minimo 16 caracteres). Sem ele essas rotas respondem 503. |
| `NEXJUS_CORS_ORIGINS` | Origens liberadas, separadas por virgula, por exemplo `chrome-extension://<id>`. |
| `NEXJUS_SMTP_*`, `NEXJUS_ALERT_FROM`, `NEXJUS_ALERT_TO` | Envio do alerta diario. Sem `NEXJUS_SMTP_HOST` nada e enviado. |
| `NEXJUS_AGENDA_HORA`, `NEXJUS_AGENDA_DIAS` | Horario do alerta (HH:MM) e janela de dias da agenda. |

Os segredos nunca sao registrados em log: a URL do banco aparece com a senha mascarada e o token e a
senha do SMTP ficam em `SecretStr`.

## Sincronizacao

Cada maquina tem um `device_id` e guarda o ultimo `cursor` recebido.

1. `POST /sync/push` com `{"device_id": "...", "changes": [...]}`. Cada alteracao tem `entity`
   (`clientes`, `veiculos`, `processos`, `prazos` ou `feriadosLocais`), `id`, `updated_at` (ISO 8601),
   `deleted`, `payload` e, apenas para prazos, `due_date` e `done`.
2. `GET /sync/changes?since=<cursor>&device_id=<device_id>` devolve as alteracoes das outras maquinas
   em ordem, o novo `cursor` e `has_more` para paginar.

Conflitos: vence o `updated_at` mais recente. Quando o servidor ja tem uma versao igual ou mais nova, a
alteracao volta em `stale` com a versao do servidor. Datas mais de 5 minutos no futuro sao recusadas,
para que um relogio errado nao sobrescreva as outras maquinas. Exclusoes ficam como marcadores sem
payload.

## LGPD

- O servidor guarda `payload` como texto opaco e nao o interpreta. Recomenda-se enviar o payload ja
  criptografado pela extensao (AES-GCM com a senha do usuario), assim o servidor nunca ve dados de clientes.
- A agenda usa somente `due_date` e `done` dos prazos. O e-mail diario traz contagens, datas e o
  identificador interno do prazo; nomes, documentos e numeros de processo nao entram.
- Mensagens de erro e logs nunca repetem o payload.
- Registros excluidos perdem o payload no servidor.

## Agenda e alertas

```bash
nexjus-backend agenda                 # imprime a agenda de hoje
nexjus-backend agenda --send          # imprime e envia o e-mail, se o SMTP estiver configurado
nexjus-backend scheduler              # envia todo dia em NEXJUS_AGENDA_HORA
```

A mesma agenda sai em JSON em `GET /agenda?hoje=YYYY-MM-DD&dias=7`.

## Banco e migracoes

As tabelas sao criadas pelo Alembic: `nexjus-backend migrate` (o `serve` ja faz isso). Para usar o
Alembic direto, rode `alembic upgrade head` dentro de `app/` com `NEXJUS_DATABASE_URL` definido.

## Docker com Postgres

```bash
cd app
cp .env.example .env   # troque POSTGRES_PASSWORD e defina NEXJUS_API_TOKEN
docker compose up -d --build
```

O Postgres e a API publicam as portas apenas em `127.0.0.1`. O servico `scheduler` envia o alerta diario.
A imagem roda como usuario sem privilegios e tem `HEALTHCHECK` em `/health`.

## Testes

```bash
python -m pytest     # na raiz do repositorio; tudo offline, sem rede
ruff check .
```
