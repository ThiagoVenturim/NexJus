# Acompanhamento de NP

An everyday tool for Brazilian lawyers: a Chrome extension for clients, cases and vehicles, a deadline
engine (CPC, traffic code, holidays and court recess), DataJud lookups, a local MCP server and Claude
agents and skills.

Status: under construction.

## Documentation

- [Installation](docs/INSTALLATION.en.md): extension, MCP server, skills and optional backend.
- [LGPD and privacy](docs/PRIVACY.en.md): where data lives, what leaves the machine, anonymisation and local models.
- [Deadline rules](docs/DEADLINES.en.md): how the engine counts CPC and CTB periods and how to add a court, district or Detran.
- [Using with Claude](docs/CLAUDE.en.md): MCP server, skills, agents and example requests.

## Disclaimer

Every computed deadline and every generated draft must be checked by the lawyer against the official
system. This tool does not replace the court, Detran or the issuing authority.

## LGPD

Data stays on the user's computer by default. No client data is sent to third parties without an explicit
user action. Details in [docs/PRIVACY.en.md](docs/PRIVACY.en.md).

## Optional backend

`app/` holds an optional FastAPI server to sync data between machines, build the daily deadline agenda and
send e-mail alerts. See [app/README.md](app/README.md).

## Local MCP server

`mcp-server/` holds a local MCP server (stdio) that exposes deadlines and cases to an MCP client such as
Claude: CPC/traffic code deadline calculation with an audit trail, deadline lists, agenda, clients with
pending items, recording case movements and DataJud lookups. See [mcp-server/README.md](mcp-server/README.md).

## Claude skills and agents

`skills/` holds Claude skills and subagents for day-to-day legal work (deadlines, daily triage, case and
filing summaries, traffic defense and petition drafts, client reports, document checklists and sourced
case-law research), wired to the MCP server, plus an installer. See [skills/README.md](skills/README.md).

Portuguese documentation comes first: [README.md](README.md).
