# Acompanhamento de NP

An everyday tool for Brazilian lawyers: a Chrome extension for clients, cases and vehicles, a deadline
engine (CPC, traffic code, holidays and court recess), DataJud lookups, a local MCP server and Claude
agents and skills.

Status: under construction.

## Disclaimer

Every computed deadline and every generated draft must be checked by the lawyer against the official
system. This tool does not replace the court, Detran or the issuing authority.

## Local MCP server

`mcp-server/` holds a local MCP server (stdio) that exposes deadlines and cases to an MCP client such as
Claude: CPC/traffic code deadline calculation with an audit trail, deadline lists, agenda, clients with
pending items, recording case movements and DataJud lookups. See [mcp-server/README.md](mcp-server/README.md).

Portuguese documentation comes first: [README.md](README.md).
