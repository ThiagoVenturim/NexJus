# Installation

Portuguese version (reference): [INSTALACAO.md](INSTALACAO.md).

NexJus has four parts. Only the extension is required; the others are optional and can be installed later,
in any order.

| Part | Folder | Purpose | Requirements |
| --- | --- | --- | --- |
| Chrome extension | `extension/` | Records, deadlines, alerts, reading the open page and DataJud | Node.js 18 or newer, Chrome or another Chromium browser |
| Local MCP server | `mcp-server/` | Expose deadlines and cases to Claude (or another MCP client) | Python 3.11 or newer |
| Skills and agents | `skills/` | Claude skills and subagents that use the MCP server | Python 3.11 or newer, Claude Code, Claude Desktop or the web app |
| Optional backend | `app/` | Sync data between machines, daily agenda and e-mail alerts | Python 3.11 or newer; Docker for Postgres |

> Disclaimer: every computed deadline and every generated draft must be checked by the lawyer against the
> official system of the court, Detran or issuing authority. The tool assists; it does not replace that check.

Commands start from the repository root. On Windows use `.venv\Scripts\` instead of `.venv/bin/` and
`copy` instead of `cp`.

## 1. Get the code

```bash
git clone https://github.com/ThiagoVenturim/NexJus.git
cd NexJus
```

## 2. Chrome extension

```bash
cd extension
npm install
npm test             # deadline engine, CSV and DataJud tests
npm run build        # builds extension/dist
```

In Chrome:

1. Open `chrome://extensions` and turn on **Developer mode**.
2. Click **Load unpacked** and pick the `extension/dist` folder.
3. Open the extension popup. Data is stored in `chrome.storage.local`.

Recommended: in the **Seguranca LGPD** tab of the popup, set a password to encrypt the data (AES-GCM with a
PBKDF2-derived key). Encrypted data cannot be recovered without the password.

To query DataJud, enter the CNJ case number and the public DataJud API key, published by CNJ in the Public
API documentation, in the **Pagina Aberta e DataJud** tab.

To update, run `git pull` and `npm run build` again and click **Reload** in `chrome://extensions`.

## 3. Local MCP server (optional)

```bash
cd mcp-server
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
```

Build the data file from the extension CSV export (tab **Cadastros e CSV**, box Importacao e Exportacao
CSV). Save each export as `clientes.csv`, `veiculos.csv`, `processos.csv` and `prazos.csv` in one folder
and run:

```bash
.venv/bin/nexjus-mcp import-csv ./exportacao --output ./nexjus-data.json
.venv/bin/nexjus-mcp check
```

Point `NEXJUS_MCP_DATA_FILE` in `.env` to that file. Connecting it to Claude is covered in
[CLAUDE.en.md](CLAUDE.en.md). Variables and tools: [mcp-server/README.md](../mcp-server/README.md).

## 4. Claude skills and agents (optional)

The installer uses only the Python standard library:

```bash
./skills/install.sh                      # installs into ~/.claude
./skills/install.sh install --project .  # installs into ./.claude (this project only)
```

On Windows (PowerShell):

```powershell
.\skills\install.ps1
```

Details, updates and removal: [skills/README.md](../skills/README.md).

## 5. Backend (optional)

With SQLite, on a single machine:

```bash
cd app
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
.venv/bin/nexjus-backend serve           # runs migrations and listens on 127.0.0.1:8000
```

Before starting, set `NEXJUS_API_TOKEN` in `.env` to a random value:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

With Postgres in Docker:

```bash
cd app
cp .env.example .env    # change POSTGRES_PASSWORD and set NEXJUS_API_TOKEN
docker compose up -d --build
```

Ports are published on `127.0.0.1` only. To reach the backend from another machine, use a VPN or a reverse
proxy with HTTPS; do not expose the port directly to the internet. E-mail alerts, agenda and sync:
[app/README.md](../app/README.md).

The extension does not send data to the backend yet. The sync protocol (`/sync/push` and `/sync/changes`)
is ready and documented for that integration.

## 6. Check the installation

From the repository root, with the development dependencies installed:

```bash
python -m pytest                  # backend, MCP server and skills; all offline
ruff check .
python scripts/check_no_emoji.py
cd extension && npm test && npm run typecheck
```

## Configuration files

- `.env` never goes into Git. Use `app/.env.example` and `mcp-server/.env.example` as templates; they hold
  only empty or sample values.
- Tokens, passwords and the DataJud key live in `.env` or environment variables, never in versioned files
  or in a shared MCP client configuration.
