# Deadline calculation rules

Portuguese version (reference): [PRAZOS.md](PRAZOS.md).

The deadline engine exists in two places with the same rules and the same test cases:

- extension: `extension/src/domain/prazos.ts` (tests in `extension/tests/prazos.test.ts`);
- MCP server: `mcp-server/src/nexjus_mcp/prazos.py` (tests in `mcp-server/tests/test_mcp_prazos.py`),
  which also returns an audit trail with every skipped day.

The backend (`app/`) does not compute deadlines. It uses the due date already computed to build the agenda.

> Disclaimer: the engine output is an estimate to be checked. Every deadline must be checked by the lawyer
> against the official system of the court, Detran or issuing authority, which always prevails.

## Available rules

| Rule | Default days | Counting | Recess 20 Dec to 20 Jan | Legal basis |
| --- | --- | --- | --- | --- |
| `cpc_5` | 5 | business days | suspends | CPC arts. 219, 220 and 224 |
| `cpc_15` | 15 | business days | suspends | CPC arts. 219, 220 and 224 |
| `cpc_custom` | 10 (pass `dias_prazo`) | business days | suspends | CPC arts. 219, 220 and 224 |
| `ctb_defesa_previa` | 30 | calendar days, last day extended | not applied | CTB, prior defence |
| `ctb_jari` | 30 | calendar days, last day extended | not applied | CTB, JARI appeal |
| `ctb_cetran` | 30 | calendar days, last day extended | not applied | CTB, CETRAN appeal |

In the MCP server, `dias_prazo` and `contagem` can be passed for any rule (1 to 3650 days). Use this when a
traffic notice sets a period longer than 30 days. The `nexjus://regras` resource returns this table as JSON.
The extension popup offers `cpc_15`, `cpc_5` and the three CTB rules.

## How the engine counts

1. The publication or notification day does not count (CPC art. 224).
2. Day 1 is the first business day after publication or notification, for both counting types.
3. Business days (CPC): only court business days count (art. 219). Saturdays, Sundays, holidays and, for
   CPC rules, 20 Dec to 20 Jan (art. 220) are skipped.
4. Calendar days (CTB): every day counts from day 1. If the last day falls on a Saturday, Sunday or
   holiday, the due date moves to the next business day.
5. The due date itself counts (CPC art. 224).

A day is not a business day, checked in this order, when it is:

- a Saturday or Sunday;
- within the court recess of 20 Dec to 20 Jan, for CPC rules only;
- a fixed national holiday: 01/01, 21/04, 01/05, 07/09, 12/10, 02/11, 15/11, 20/11 and 25/12 (DD/MM);
- a movable holiday: Carnival Monday and Tuesday, Good Friday and Corpus Christi, computed from Easter
  (Meeus/Jones/Butcher algorithm);
- a state holiday of the deadline's UF (table `FERIADOS_ESTADUAIS_POR_UF`);
- a local holiday in `feriadosLocais` for the same UF and, when given, the same municipality
  (case-insensitive match).

## Examples

All with UF SP. The first three cases are in the MCP server tests; the last one was computed by the same
engine.

| Rule | Publication or notification | Day 1 | Due date | Note |
| --- | --- | --- | --- | --- |
| `cpc_15` | Fri 2026-03-06 | Mon 2026-03-09 | Fri 2026-03-27 | 15 business days |
| `cpc_5` | Fri 2026-12-18 | Thu 2027-01-21 | Wed 2027-01-27 | the recess delays day 1 |
| `cpc_5`, municipality Sao Paulo with local holiday 25 Jan | Fri 2027-01-22 | Tue 2027-01-26 | Mon 2027-02-01 | 25 Jan skipped as local holiday |
| `ctb_defesa_previa` | Thu 2026-03-05 | Fri 2026-03-06 | Mon 2026-04-06 | day 30 (Sat 2026-04-04) extended |

The `calculate_deadline` response for the last example, shortened:

```json
{
  "regra": "ctb_defesa_previa",
  "dias_prazo": 30,
  "contagem": "corridos",
  "data_inicio_contagem": "2026-03-06",
  "data_vencimento": "2026-04-06",
  "prorrogado": true,
  "dias_pulados": [
    {"data": "2026-04-04", "motivo": "sabado", "fase": "prorrogacao"},
    {"data": "2026-04-05", "motivo": "domingo", "fase": "prorrogacao"}
  ],
  "fundamento": "CTB: defesa previa, 30 dias corridos com prorrogacao para dia util",
  "aviso": "Confira o prazo no sistema oficial do tribunal ou do orgao autuador."
}
```

## What the engine does not do

Check these by hand, because the engine does not apply:

- doubled periods (public treasury, public prosecutors, public defenders, co-parties with different
  counsel in paper records);
- suspensions by court order, system outages or court closures;
- court- or district-specific holidays that are not registered as local holidays;
- procedures with their own rules (small claims courts, criminal, labour), periods in hours or months;
- the publication date: the engine starts from the date given. For notices in the electronic court
  gazette, publication is the first business day after release (Law 11.419/2006, art. 4, par. 3). Check
  that date before computing;
- traffic periods other than 30 days: the notice prevails.

The `deadline-checker` skill reminds the lawyer of these points when it explains a calculation.

## Adding a court, district or Detran

### Court or district holiday

For a court or municipal holiday, without code changes, add an item to `feriadosLocais`:

```json
{"data": "01-25", "nome": "Aniversario de Sao Paulo", "uf": "SP", "municipio": "Sao Paulo"}
```

- `data` as `MM-DD` repeats every year; as `YYYY-MM-DD` it applies to that year only (use it for one-off
  closures or suspensions).
- Without `municipio`, the holiday applies to the whole UF.
- For the MCP server, edit the `NEXJUS_MCP_DATA_FILE` file and run `nexjus-mcp check`. The backend also
  syncs the `feriadosLocais` entity.
- In the extension the field exists in the data model and the engine reads it, but there is no screen to
  enter it yet.

### Fixed state holiday

Add the date to the `FERIADOS_ESTADUAIS_POR_UF` table of both engines, with the same name:

1. `extension/src/domain/prazos.ts`;
2. `mcp-server/src/nexjus_mcp/prazos.py`;
3. one test case in `extension/tests/prazos.test.ts` and the same case in `mcp-server/tests/test_mcp_prazos.py`.

Cite the state law in the pull request.

### New deadline rule (for example, a Detran-specific period)

1. Extension: add the rule to the `RegraPrazo` type in `extension/src/types/models.ts`, to
   `parametrosPadraoRegra` (`extension/src/domain/prazos.ts`) and, if it should show in the popup, to the
   selector options in `extension/src/ui/App.tsx`.
2. MCP server: add the rule to `RegraPrazo` and `REGRAS`, to `parametros_padrao` and to `FUNDAMENTO` in
   `mcp-server/src/nexjus_mcp/prazos.py`, and to the `Regra` type in `mcp-server/src/nexjus_mcp/server.py`.
3. Skills: list the rule in the `deadline-checker` skill
   (`skills/src/nexjus_skills/assets/skills/deadline-checker/SKILL.md`).
4. Tests: the same case, with the same dates, in the extension and MCP server tests.

The legal basis must be in the `FUNDAMENTO` text and in the pull request.

### Court in the DataJud lookup

The DataJud endpoint comes from the `J.TR` segment of the CNJ number. For a missing court, add the pair
`"J.TR": "api_publica_<alias>"` to `MAPA_ENDPOINTS_DATAJUD` in both places:

- `extension/src/services/datajud.ts`;
- `mcp-server/src/nexjus_mcp/datajud.py`.

Use the alias exactly as listed in the official DataJud Public API documentation and add a case to
`extension/tests/fontes_datajud.test.ts` and `mcp-server/tests/test_mcp_datajud_store.py`.

### Detran or court portal in the page reader

1. Add the domain to `content_scripts.matches` in `extension/public/manifest.json`. `*.jus.br` domains are
   already included; Detran domains are added one by one.
2. If the portal needs its own selectors, adjust `identificarPortal` and `lerPaginaAberta` in
   `extension/src/content/pageReader.ts`.
3. Keep the reading rules: only the page the user opened, no automatic login, no autonomous navigation,
   and stop when there is a CAPTCHA (`detectarCaptchaNaPagina`).
