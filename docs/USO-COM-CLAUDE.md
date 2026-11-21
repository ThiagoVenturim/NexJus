# Uso com o Claude (MCP, skills e agentes)

English version: [CLAUDE.en.md](CLAUDE.en.md).

O Claude conversa com os dados do NexJus por meio do servidor MCP local (`mcp-server/`). As skills e os
agentes (`skills/`) ensinam o Claude a usar esse servidor para prazos, triagem, resumos e minutas, sempre
com fonte e sem expor dados pessoais.

> Aviso: prazos e minutas gerados com o Claude devem ser conferidos pelo advogado no sistema oficial e
> revisados antes de qualquer protocolo ou envio. As respostas apoiam o trabalho; nao sao parecer.

Antes de comecar, siga a [instalacao](INSTALACAO.md) do servidor MCP e das skills, e leia
[LGPD.md](LGPD.md) para saber o que chega ao provedor do modelo.

## 1. Ligar o servidor MCP

O servidor se chama `nexjus` no cliente. As skills esperam esse nome, porque as ferramentas aparecem como
`mcp__nexjus__<ferramenta>`.

### Claude Code

```bash
claude mcp add --transport stdio \
  --env NEXJUS_MCP_DATA_FILE=/caminho/para/nexjus-data.json \
  nexjus -- /caminho/para/mcp-server/.venv/bin/nexjus-mcp serve
```

No Windows o executavel fica em `mcp-server\.venv\Scripts\nexjus-mcp.exe`.

### Claude Desktop

Edite `claude_desktop_config.json` (menu de configuracoes do aplicativo, secao de desenvolvedor) e
reinicie o aplicativo:

```json
{
  "mcpServers": {
    "nexjus": {
      "command": "/caminho/para/mcp-server/.venv/bin/nexjus-mcp",
      "args": ["serve"],
      "env": {
        "NEXJUS_MCP_DATA_FILE": "/caminho/para/nexjus-data.json",
        "NEXJUS_MCP_PRIVACY": "minimo",
        "NEXJUS_MCP_READ_ONLY": "true"
      }
    }
  }
}
```

No Windows, escreva os caminhos com barras duplas, por exemplo
`"C:\\Users\\<usuario>\\NexJus\\mcp-server\\.venv\\Scripts\\nexjus-mcp.exe"`.

Nao coloque `NEXJUS_DATAJUD_API_KEY` nem `NEXJUS_API_TOKEN` nesse arquivo. Deixe-os no `.env` da pasta de
onde o servidor e iniciado ou em variaveis de ambiente do sistema. `nexjus-mcp check` mostra a
configuracao lida sem exibir os segredos.

### O que o servidor oferece

| Ferramenta | Uso |
| --- | --- |
| `calculate_deadline` | Vencimento CPC ou CTB com os dias pulados e o motivo. Regras em [PRAZOS.md](PRAZOS.md). |
| `list_deadlines` | Prazos por status (`vencido`, `hoje`, `urgente`, `no_prazo`, `concluido`), processo ou cliente. |
| `deadlines_this_week` | Pendentes ate domingo, mais os vencidos. |
| `clients_with_pending_items` | Clientes com prazos vencidos ou proximos, por urgencia. |
| `generate_agenda` | Agenda do arquivo local (`fonte=local`) ou do backend (`fonte=backend`). |
| `datajud_lookup_case` | Capa e ultimos movimentos no DataJud (exige `NEXJUS_DATAJUD_API_KEY`). |
| `case_movements` | Movimentos do DataJud ou do registro local. |
| `record_movement` | Grava um andamento e, opcionalmente, o prazo decorrente. Bloqueada com `NEXJUS_MCP_READ_ONLY=true`. |

Recursos: `nexjus://agenda`, `nexjus://prazos/pendentes` e `nexjus://regras`.

## 2. Instalar as skills e os agentes

```bash
./skills/install.sh             # ~/.claude, vale para todos os projetos
nexjus-skills list              # se instalou o pacote com pip install -e ./skills
```

No Claude Code as skills e os agentes ficam disponiveis na proxima sessao. No Claude Desktop ou no app
web, compacte a pasta da skill (por exemplo `deadline-checker/`) num arquivo zip e envie pelas
configuracoes de skills do aplicativo. Os agentes sao exclusivos do Claude Code.

| Skill | Quando usar |
| --- | --- |
| `deadline-checker` | Calcular, conferir ou explicar um prazo. |
| `daily-triage` | Comecar o dia: vencidos, hoje, urgentes e semana. |
| `case-summarizer` | Resumir um processo, seus andamentos ou uma peca colada. |
| `traffic-defense-drafter` | Minuta de defesa previa, recurso a JARI ou ao CETRAN. |
| `petition-drafter` | Minuta de peticao simples, manifestacao, inicial ou contestacao. |
| `client-report` | Relatorio de andamento em linguagem simples para o cliente. |
| `document-checklist` | Documentos exigidos por lei, pedidos pelo orgao e recomendados. |
| `jurisprudence-researcher` | Termos de busca e julgados com fonte. |

| Agente (Claude Code) | Para que serve |
| --- | --- |
| `assistente-prazos` | Triagem, prazos e resumos. Unico com `record_movement`, sempre com confirmacao. |
| `redator-minutas` | Minutas, relatorios ao cliente e listas de documentos. |
| `pesquisador-jurisprudencia` | Pesquisa de jurisprudencia com fonte. |

## 3. Exemplos de pedidos

- "Quais prazos vencem esta semana?" (`daily-triage`, usa `deadlines_this_week` e `generate_agenda`)
- "Publicacao em 06/03/2026, prazo de 15 dias uteis, SP. Quando vence?" (`deadline-checker`)
- "Resuma o processo 0000000-00.0000.0.00.0000 e diga se ha prazo aberto." (`case-summarizer`; troque
  pelo numero real)
- "Monte a defesa previa do auto de infracao do cliente Maria S. O., notificacao de 05/03/2026."
  (`traffic-defense-drafter`)
- "Registre o andamento 'juntada de procuracao' no processo X." (`assistente-prazos` pede confirmacao antes
  de gravar)

O Claude chama as ferramentas e mostra o resultado. Confira as datas pela trilha `dias_pulados`.

## 4. Conferir o que foi gerado

Antes de usar uma minuta ou relatorio:

```bash
nexjus-skills check minuta.md                # minutas: exige o aviso de revisao
nexjus-skills check --not-draft relatorio.md
```

O comando aponta CPF, CNPJ, e-mail e telefone visiveis, marcadores `[CONFERIR: ...]` pendentes, citacoes
de jurisprudencia sem secao "Fontes" e minutas sem o aviso de revisao. Ele nao avalia o merito juridico:
a revisao do advogado continua obrigatoria.

## 5. Regras que as skills seguem

- Toda afirmacao juridica tem fonte (lei, sumula, precedente, andamento ou trecho da peca). Sem fonte,
  aparece `[CONFERIR: ...]`. Nenhum precedente, numero, data ou endereco inventado.
- Prazos sempre pelo motor do servidor MCP. Sem o servidor, a resposta avisa que o calculo foi manual.
- Dados pessoais (CPF, CNPJ, RG, telefone, e-mail, endereco e RENAVAM) nao aparecem nas respostas, e
  buscas na web nunca levam dados de clientes.
- Chaves e tokens nunca aparecem em respostas ou logs.

## Problemas comuns

| Sintoma | Causa provavel |
| --- | --- |
| As ferramentas `mcp__nexjus__*` nao aparecem | O servidor nao foi registrado com o nome `nexjus`, ou o caminho do executavel esta errado. Rode o comando do executavel no terminal para ver o erro. |
| Listas vazias ou processo nao encontrado | `NEXJUS_MCP_DATA_FILE` aponta para outro arquivo (arquivo inexistente e lido como vazio). Rode `nexjus-mcp check`. |
| DataJud desligado | `NEXJUS_DATAJUD_API_KEY` vazio no ambiente do servidor. |
| `record_movement` recusado | `NEXJUS_MCP_READ_ONLY=true`, como no exemplo acima. Desligue apenas se quiser que o Claude grave andamentos. |
| `generate_agenda` com `fonte=backend` falha | `NEXJUS_BACKEND_URL` ou `NEXJUS_API_TOKEN` ausentes, ou o backend fora do ar (`GET /health`). |
