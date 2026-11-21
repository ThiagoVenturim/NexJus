# Using NexJus with Claude (MCP, skills and agents)

Portuguese version (reference): [USO-COM-CLAUDE.md](USO-COM-CLAUDE.md).

Claude works with NexJus data through the local MCP server (`mcp-server/`). The skills and agents
(`skills/`) teach Claude to use that server for deadlines, triage, summaries and drafts, always with
sources and without exposing personal data.

> Disclaimer: deadlines and drafts produced with Claude must be checked by the lawyer against the official
> system and reviewed before any filing or sending. The answers assist the work; they are not legal opinions.

First follow the [installation](INSTALLATION.en.md) of the MCP server and the skills, and read
[PRIVACY.en.md](PRIVACY.en.md) to know what reaches the model provider.

## 1. Connect the MCP server

The server is named `nexjus` in the client. The skills expect that name, because the tools appear as
`mcp__nexjus__<tool>`.

### Claude Code

```bash
claude mcp add --transport stdio \
  --env NEXJUS_MCP_DATA_FILE=/path/to/nexjus-data.json \
  nexjus -- /path/to/mcp-server/.venv/bin/nexjus-mcp serve
```

On Windows the executable is `mcp-server\.venv\Scripts\nexjus-mcp.exe`.

### Claude Desktop

Edit `claude_desktop_config.json` (app settings, developer section) and restart the app:

```json
{
  "mcpServers": {
    "nexjus": {
      "command": "/path/to/mcp-server/.venv/bin/nexjus-mcp",
      "args": ["serve"],
      "env": {
        "NEXJUS_MCP_DATA_FILE": "/path/to/nexjus-data.json",
        "NEXJUS_MCP_PRIVACY": "minimo",
        "NEXJUS_MCP_READ_ONLY": "true"
      }
    }
  }
}
```

On Windows, escape backslashes in paths, for example
`"C:\\Users\\<user>\\NexJus\\mcp-server\\.venv\\Scripts\\nexjus-mcp.exe"`.

Do not put `NEXJUS_DATAJUD_API_KEY` or `NEXJUS_API_TOKEN` in that file. Keep them in the `.env` of the
folder the server starts from, or in system environment variables. `nexjus-mcp check` prints the loaded
configuration without showing secrets.

### What the server offers

| Tool | Use |
| --- | --- |
| `calculate_deadline` | CPC or CTB due date with the skipped days and the reason for each. Rules in [DEADLINES.en.md](DEADLINES.en.md). |
| `list_deadlines` | Deadlines by status (`vencido`, `hoje`, `urgente`, `no_prazo`, `concluido`), case or client. |
| `deadlines_this_week` | Pending until Sunday, plus overdue ones. |
| `clients_with_pending_items` | Clients with overdue or upcoming deadlines, by urgency. |
| `generate_agenda` | Agenda from the local file (`fonte=local`) or the backend (`fonte=backend`). |
| `datajud_lookup_case` | Case header and latest movements from DataJud (needs `NEXJUS_DATAJUD_API_KEY`). |
| `case_movements` | Movements from DataJud or the local record. |
| `record_movement` | Records a case movement and, optionally, the resulting deadline. Blocked with `NEXJUS_MCP_READ_ONLY=true`. |

Resources: `nexjus://agenda`, `nexjus://prazos/pendentes` and `nexjus://regras`.

## 2. Install the skills and agents

```bash
./skills/install.sh             # ~/.claude, for every project
nexjus-skills list              # if you installed the package with pip install -e ./skills
```

In Claude Code the skills and agents are available in the next session. In Claude Desktop or the web app,
zip the skill folder (for example `deadline-checker/`) and upload it in the app's skills settings. Agents
are Claude Code only.

| Skill | When to use |
| --- | --- |
| `deadline-checker` | Compute, check or explain a deadline. |
| `daily-triage` | Start the day: overdue, today, urgent and this week. |
| `case-summarizer` | Summarise a case, its movements or a pasted filing. |
| `traffic-defense-drafter` | Draft a prior defence, JARI or CETRAN appeal. |
| `petition-drafter` | Draft a simple petition, response, complaint or answer. |
| `client-report` | Plain-language progress report for the client. |
| `document-checklist` | Documents required by law, requested by the authority and recommended. |
| `jurisprudence-researcher` | Search terms and sourced case law. |

| Agent (Claude Code) | Purpose |
| --- | --- |
| `assistente-prazos` | Triage, deadlines and summaries. The only one with `record_movement`, always after confirmation. |
| `redator-minutas` | Drafts, client reports and document checklists. |
| `pesquisador-jurisprudencia` | Sourced case-law research. |

## 3. Example requests

The skills are written in Portuguese. Typical requests:

- "Quais prazos vencem esta semana?" (`daily-triage`, uses `deadlines_this_week` and `generate_agenda`)
- "Publicacao em 06/03/2026, prazo de 15 dias uteis, SP. Quando vence?" (`deadline-checker`)
- "Resuma o processo 0000000-00.0000.0.00.0000 e diga se ha prazo aberto." (`case-summarizer`; use the real
  number)
- "Monte a defesa previa do auto de infracao do cliente Maria S. O., notificacao de 05/03/2026."
  (`traffic-defense-drafter`)
- "Registre o andamento 'juntada de procuracao' no processo X." (`assistente-prazos` asks for confirmation
  before writing)

Claude calls the tools and shows the result. Check the dates against the `dias_pulados` trail.

## 4. Check what was generated

Before using a draft or report:

```bash
nexjus-skills check minuta.md                # drafts: requires the review notice
nexjus-skills check --not-draft relatorio.md
```

The command flags visible CPF, CNPJ, e-mail and phone, pending `[CONFERIR: ...]` markers, case-law
citations without a "Fontes" section and drafts without the review notice. It does not assess legal
merit: the lawyer's review is still required.

## 5. Rules the skills follow

- Every legal statement has a source (statute, binding precedent, case law, case movement or an excerpt of
  the filing). Without a source it shows `[CONFERIR: ...]`. No invented precedent, number, date or address.
- Deadlines always come from the MCP server engine. Without the server, the answer says the calculation
  was manual.
- Personal data (CPF, CNPJ, RG, phone, e-mail, address and RENAVAM) does not appear in answers, and web
  searches never include client data.
- Keys and tokens never appear in answers or logs.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `mcp__nexjus__*` tools do not show up | The server was not registered as `nexjus`, or the executable path is wrong. Run the executable in a terminal to see the error. |
| Empty lists or case not found | `NEXJUS_MCP_DATA_FILE` points to another file (a missing file reads as empty). Run `nexjus-mcp check`. |
| DataJud disabled | `NEXJUS_DATAJUD_API_KEY` is empty in the server environment. |
| `record_movement` refused | `NEXJUS_MCP_READ_ONLY=true`, as in the example above. Turn it off only if Claude should record movements. |
| `generate_agenda` with `fonte=backend` fails | `NEXJUS_BACKEND_URL` or `NEXJUS_API_TOKEN` missing, or the backend is down (`GET /health`). |
