# NexJus Skills (skills e agentes para o Claude)

Skills e subagentes do Claude voltados para advogados brasileiros, integrados ao servidor MCP local do
NexJus (`mcp-server/`) e, por meio dele, ao backend opcional (`app/`). As skills orientam o modelo a usar
as ferramentas do servidor para prazos e andamentos, a citar a fonte de toda afirmacao juridica e a nao
expor dados pessoais.

## Skills

| Skill | O que faz | Ferramentas MCP |
| --- | --- | --- |
| `deadline-checker` | Calcula e explica prazos CPC e CTB, com os dias pulados e o fundamento; avisa sobre prazos em dobro e ritos que o motor nao aplica. | `calculate_deadline`, `list_deadlines` |
| `case-summarizer` | Resume o processo, explica os andamentos e resume pecas coladas, apontando prazos possivelmente abertos. | `datajud_lookup_case`, `case_movements`, `list_deadlines` |
| `daily-triage` | Triagem do dia: vencidos, hoje, urgentes, semana e clientes com pendencias (arquivo local ou backend). | `generate_agenda`, `deadlines_this_week`, `clients_with_pending_items`, `record_movement` (so com confirmacao) |
| `traffic-defense-drafter` | Minuta de defesa previa, recurso a JARI ou ao CETRAN, com o prazo CTB e os requisitos do auto. | `calculate_deadline`, `list_deadlines`, `case_movements` |
| `petition-drafter` | Minuta assistida de peticao simples, manifestacao, inicial ou contestacao, conforme o CPC. | `datajud_lookup_case`, `case_movements`, `list_deadlines`, `calculate_deadline` |
| `client-report` | Relatorio de andamento em linguagem simples para o cliente, revisado pelo advogado antes do envio. | `case_movements`, `datajud_lookup_case`, `list_deadlines`, `clients_with_pending_items` |
| `document-checklist` | Lista de documentos separando o que a lei exige (com o artigo), o que o orgao pede e o recomendado. | `case_movements`, `list_deadlines` |
| `jurisprudence-researcher` | Termos de busca e tabela de julgados com fonte; o que nao tem fonte vai para "Nao confirmados". | `datajud_lookup_case` |

## Agentes (Claude Code)

| Agente | Usa as skills |
| --- | --- |
| `assistente-prazos` | `daily-triage`, `deadline-checker`, `case-summarizer` |
| `redator-minutas` | `traffic-defense-drafter`, `petition-drafter`, `client-report`, `document-checklist` |
| `pesquisador-jurisprudencia` | `jurisprudence-researcher` |

Cada agente declara em `tools` somente as ferramentas de que precisa. Apenas `assistente-prazos` tem
`record_movement`, a unica ferramenta que grava, e so a usa depois de confirmacao do advogado.

## Instalacao

Requer Python 3.11 ou mais novo. O instalador usa apenas a biblioteca padrao, entao roda direto do
codigo-fonte:

```bash
./skills/install.sh                      # instala em ~/.claude
./skills/install.sh install --project .  # instala em ./.claude (somente este projeto)
./skills/install.sh uninstall            # remove o que foi instalado
```

No Windows (PowerShell):

```powershell
.\skills\install.ps1
.\skills\install.ps1 install --project .
```

Ou como pacote:

```bash
pip install -e ./skills
nexjus-skills install            # --project DIR, --target DIR, --only NOME, --dry-run, --force
nexjus-skills list
nexjus-skills validate
```

O instalador grava `skills/<nome>/SKILL.md`, `agents/<nome>.md` e um manifesto `.nexjus-skills.json` com
o hash de cada arquivo. Reinstalar atualiza os arquivos que voce nao editou e preserva os editados
(retorna codigo 1 e lista os preservados); `--force` sobrescreve. `uninstall` remove apenas os arquivos
do manifesto que nao foram alterados.

Depois configure o servidor MCP com o nome `nexjus` no cliente, como em
[mcp-server/README.md](../mcp-server/README.md). No Claude Code, por exemplo:

```bash
claude mcp add --transport stdio --env NEXJUS_MCP_DATA_FILE=/caminho/para/nexjus-data.json nexjus -- /caminho/para/mcp-server/.venv/bin/nexjus-mcp serve
```

As ferramentas aparecem para as skills como `mcp__nexjus__<ferramenta>`. Para usar as skills no Claude
Desktop ou no app web, compacte a pasta da skill (por exemplo `deadline-checker/`) num arquivo zip e
envie pelas configuracoes de skills do aplicativo.

## Conferencia de minutas

`nexjus-skills check` confere um texto gerado antes do uso, sem rede e sem modelo:

```bash
nexjus-skills check minuta.md               # minutas: exige o aviso de revisao
nexjus-skills check --not-draft relatorio.md
```

Aponta CPF, CNPJ, e-mail e telefone visiveis (sem repetir o dado), marcadores `[CONFERIR: ...]`
pendentes, citacoes de jurisprudencia sem secao "Fontes" e minutas sem o aviso de revisao. Retorna 0
quando nao ha nada a apontar e 1 caso contrario. A conferencia nao avalia o merito juridico.

## Regras que toda skill segue

- Apoio ao advogado, nunca parecer ou conselho juridico definitivo; o advogado responsavel decide.
- Toda afirmacao juridica com fonte (lei, sumula, precedente, andamento ou trecho da peca). Sem fonte,
  `[CONFERIR: ...]`. Nada de precedente, numero, data ou endereco inventado.
- Prazos sempre pelo motor do servidor MCP e conferidos no sistema oficial.
- LGPD: CPF, CNPJ, RG, telefone, e-mail, endereco e RENAVAM nao aparecem nas respostas; nomes vem como o
  servidor MCP entrega (abreviados no modo `minimo`). Buscas na web nunca levam dados de clientes.
- Chaves e tokens ficam no `.env` do servidor MCP e nunca aparecem em respostas ou logs.

`nexjus-skills validate` (e os testes) conferem o frontmatter, as secoes obrigatorias, que toda
ferramenta citada existe no servidor MCP e que as skills de minuta trazem o aviso.

## Testes

```bash
python -m pytest     # na raiz do repositorio; tudo offline
ruff check .
```

Os testes rodam cada skill contra o servidor MCP real, montado em memoria com dados ficticios e DataJud
simulado, usando um modelo simulado (`StubModel`) no lugar do Claude. Nenhum teste usa rede ou LLM.
