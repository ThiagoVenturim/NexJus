# LGPD and privacy

Portuguese version (reference): [LGPD.md](LGPD.md).

NexJus handles client data of law offices: names, CPF or CNPJ, phone, e-mail, licence plate, RENAVAM and
case numbers. The project follows three rules:

1. Data stays on the lawyer's computer by default.
2. Nothing leaves the machine without an explicit user action, and what leaves is the minimum needed.
3. The lawyer remains responsible for processing client data (the controller, in LGPD terms). The tool
   helps comply with the law but does not replace the office's own policies.

> Disclaimer: deadlines and drafts produced by the tool must be checked by the lawyer against the official
> system. This document describes how the software behaves; it is not a legal opinion on LGPD.

## Where data is stored

| Part | Storage | Notes |
| --- | --- | --- |
| Extension | Browser `chrome.storage.local` | Optional password encryption (AES-GCM 256, PBKDF2-derived key with 100,000 iterations and a random salt). |
| MCP server | Local JSON file (`NEXJUS_MCP_DATA_FILE`) | Built from the CSV export. It does not read the extension's encrypted store. |
| Optional backend | Local SQLite or Postgres | Each record's `payload` is stored as opaque text. Ports published on `127.0.0.1` only. |
| Skills | `SKILL.md` and agent files in `~/.claude` or `./.claude` | No client data; instructions only. |

## What can leave the machine

| Destination | When | What is sent |
| --- | --- | --- |
| DataJud public API (CNJ) | When the user looks up a case | The CNJ number and the public API key. No client data. |
| AI model provider (for example Claude) | When the user talks to the model with the MCP server | Only MCP tool responses, already minimised (see below), and whatever the user types. |
| Office backend | When sync is turned on | Records with an opaque `payload`. The extension does not sync yet; the protocol is ready in the backend. |
| SMTP server | Daily alert, if `NEXJUS_SMTP_HOST` is set | Counts, dates and the internal deadline id. No names, documents or case numbers. |

The extension page reader runs only in the tab the user opened and only on its DOM (PJe, eSAJ, Projudi,
Senatran/RENAINF and Detran). If the page shows a CAPTCHA, reading stops: the extension never tries to
solve, click or bypass a CAPTCHA, and it does not log in or navigate on its own.

## Anonymisation and data minimisation

### MCP server

- CPF or CNPJ, phone, e-mail and RENAVAM never leave the server, in any mode.
- `minimo` mode (default, `NEXJUS_MCP_PRIVACY=minimo`): the client name becomes first name plus initials
  ("Maria Silva Oliveira" becomes "Maria S. O."), the plate is masked ("ABC1D23" becomes "ABC***3") and
  CPF, CNPJ, e-mail and phone found in free text, such as deadline titles and case movements, become the
  markers `[cpf]`, `[cnpj]`, `[e-mail]` and `[telefone]`. Case numbers are kept because the work needs
  them and they are already public in DataJud.
- `completo` mode: name and plate are returned in full; the fields in the first bullet are still withheld.
- `NEXJUS_MCP_READ_ONLY=true` stops the model from writing movements or deadlines to the file.
- Logs go to stderr and record only internal ids and HTTP status codes.

### Skills and agents

- The skills tell the model not to display CPF, CNPJ, RG, phone, e-mail, address or RENAVAM and never to
  include client data in web searches.
- `nexjus-skills check file.md` checks a generated text before use, offline and without a model: it flags
  visible CPF, CNPJ, e-mail and phone (without repeating the value), pending `[CONFERIR: ...]` markers and
  drafts missing the review notice.

### Backend

- The server does not interpret the `payload`. Sending it already encrypted by the client is recommended,
  so the server never sees client data.
- Error messages and logs never repeat the payload. The database URL is shown with the password masked.
- Deleted records lose their payload on the server; only the deletion marker remains.

## Local model

The MCP server runs over stdio, opens no network port and is not tied to a specific model. To keep all
data on the machine, connect it to an MCP client that uses a locally run model. In that case:

- the server configuration is the same (`nexjus-mcp serve` and the `.env` variables);
- keep `NEXJUS_MCP_PRIVACY=minimo` even with a local model, because clients usually write chat history
  to disk;
- the skills were written and tested for Claude; with another model, review answers more carefully and
  run `nexjus-skills check` on drafts.

With Claude or another cloud model, tool responses go to the model provider. Check the terms of use and the
data retention policy of your plan before using it with client data.

## Data subject rights

- Access and portability: the extension **Cadastros e CSV** tab exports clients, vehicles, cases and
  deadlines as CSV.
- Correction and deletion: edit or delete the record in the extension. For the MCP server, rebuild the
  JSON file from a new export. In the backend, deletion removes the payload.
- Copies made outside the tool (saved drafts, AI client history, e-mails) are the office's responsibility
  and must follow the same deletion routine.

## Office checklist

- [ ] Encryption password set in the extension.
- [ ] `.env` outside Git and readable only by the user.
- [ ] `NEXJUS_MCP_PRIVACY=minimo` and, if the model does not need to write, `NEXJUS_MCP_READ_ONLY=true`.
- [ ] AI provider terms reviewed, or a local model in use.
- [ ] Backend, if used, reachable only through a VPN or HTTPS, with a random `NEXJUS_API_TOKEN`.
- [ ] Drafts and reports checked with `nexjus-skills check` and reviewed by the lawyer before sending.
