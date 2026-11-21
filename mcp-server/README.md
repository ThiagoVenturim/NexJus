# NexJus MCP (servidor local)

Servidor MCP local que expoe os prazos e processos do NexJus para um cliente MCP, por exemplo o
Claude Desktop ou o Claude Code. Roda na maquina do advogado, em stdio, sem abrir porta de rede.

- Motor de prazos CPC (dias uteis, feriados e recesso de 20/12 a 20/01) e CTB (30 dias corridos com
  prorrogacao), porte fiel do motor da extensao (`extension/src/domain/prazos.ts`), com trilha de auditoria.
- Prazos e processos lidos de um arquivo JSON local no formato da extensao.
- Consulta a API publica do DataJud (CNJ) com validacao do numero CNJ (mod 97).
- Agenda local ou a agenda sincronizada do backend opcional (`app/`).

## Ferramentas

| Ferramenta | O que faz |
| --- | --- |
| `calculate_deadline` | Calcula o vencimento (CPC ou CTB) e devolve os dias pulados com o motivo de cada um. |
| `list_deadlines` | Lista prazos com status `vencido`, `hoje`, `urgente` (ate 3 dias), `no_prazo` ou `concluido`, com filtros por status, processo e cliente. |
| `deadlines_this_week` | Prazos pendentes de hoje ate domingo desta semana, mais os vencidos. |
| `datajud_lookup_case` | Capa do processo no DataJud (tribunal, classe, orgao julgador) e os ultimos movimentos. |
| `case_movements` | Movimentos do processo, do DataJud ou do registro local. |
| `clients_with_pending_items` | Clientes com prazos vencidos ou vencendo nos proximos dias, ordenados por urgencia. |
| `record_movement` | Registra um andamento no processo local e, opcionalmente, cria o prazo decorrente. |
| `generate_agenda` | Agenda em JSON e em texto (fonte `local` ou `backend`). |

Recursos: `nexjus://agenda` (texto), `nexjus://prazos/pendentes` (JSON) e `nexjus://regras` (JSON).

## Instalacao

Requer Python 3.11 ou mais novo.

```bash
cd mcp-server
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
```

No Windows use `.venv\Scripts\` no lugar de `.venv/bin/`.

## Dados

O servidor le o arquivo de `NEXJUS_MCP_DATA_FILE`, um JSON no formato `NexJusDatabase` da extensao
(`clientes`, `veiculos`, `processos`, `prazos`, `feriadosLocais`). Para montar esse arquivo a partir dos
CSV exportados pela extensao (aba Importacao e Exportacao CSV), salve-os como `clientes.csv`,
`veiculos.csv`, `processos.csv` e `prazos.csv` numa pasta e rode:

```bash
nexjus-mcp import-csv ./exportacao --output ./nexjus-data.json
nexjus-mcp check
```

Arquivos criptografados pela extensao nao sao lidos; use a exportacao CSV. `record_movement` grava no
mesmo arquivo de forma atomica. Com `NEXJUS_MCP_READ_ONLY=true` o servidor nao grava nada.

## Configuracao

Tudo vem de variaveis de ambiente ou do arquivo `.env` (fora do Git). Veja `.env.example`.

| Variavel | Uso |
| --- | --- |
| `NEXJUS_MCP_DATA_FILE` | Arquivo JSON local. Padrao `./nexjus-data.json`. |
| `NEXJUS_MCP_PRIVACY` | `minimo` (padrao) ou `completo`. Veja LGPD abaixo. |
| `NEXJUS_MCP_READ_ONLY` | `true` bloqueia `record_movement`. |
| `NEXJUS_DATAJUD_API_KEY` | Chave publica da API do DataJud, publicada pelo CNJ. Sem ela as consultas ao DataJud ficam desligadas. |
| `NEXJUS_DATAJUD_TIMEOUT` | Tempo limite das consultas, em segundos. Padrao 15. |
| `NEXJUS_BACKEND_URL`, `NEXJUS_API_TOKEN` | Backend opcional (`app/`) para `generate_agenda` com `fonte=backend`. |

## Uso com um cliente MCP

Exemplo de configuracao (Claude Desktop, `claude_desktop_config.json`). Ajuste os caminhos:

```json
{
  "mcpServers": {
    "nexjus": {
      "command": "/caminho/para/mcp-server/.venv/bin/nexjus-mcp",
      "args": ["serve"],
      "env": {
        "NEXJUS_MCP_DATA_FILE": "/caminho/para/nexjus-data.json",
        "NEXJUS_MCP_PRIVACY": "minimo"
      }
    }
  }
}
```

Prefira deixar `NEXJUS_DATAJUD_API_KEY` no `.env` da pasta de onde o servidor e iniciado, em vez de
escreve-la na configuracao do cliente.

## Calculo de prazos

Mesmas regras da extensao:

- exclui o dia do comeco e inclui o do vencimento (CPC art. 224);
- o dia 1 e o primeiro dia util seguinte a publicacao ou notificacao;
- CPC (`cpc_5`, `cpc_15`, `cpc_custom`): conta so dias uteis forenses (art. 219) e suspende de 20/12 a 20/01 (art. 220);
- CTB (`ctb_defesa_previa`, `ctb_jari`, `ctb_cetran`): 30 dias corridos, prorrogando o termo final que cair
  em sabado, domingo ou feriado;
- feriados nacionais fixos, moveis (Carnaval, Sexta-feira da Paixao, Corpus Christi), estaduais por UF e
  os feriados locais do arquivo de dados.

A resposta traz `dias_pulados` (data, motivo e fase: inicio, contagem ou prorrogacao) para conferencia.
Todo prazo deve ser conferido no sistema oficial do tribunal ou do orgao autuador.

## LGPD

- Documento (CPF/CNPJ), telefone, e-mail e RENAVAM nunca saem do servidor, em nenhum modo.
- No modo `minimo` o nome do cliente vira primeiro nome e iniciais, a placa fica mascarada e CPF, CNPJ,
  e-mail e telefone em textos livres (titulos de prazo, andamentos) viram marcadores. Numeros de processo
  sao mantidos.
- No modo `completo` nome e placa saem inteiros.
- Segredos ficam em variaveis de ambiente ou `.env` e nunca aparecem em logs, erros ou respostas.
- Logs vao para stderr e registram apenas identificadores internos e codigos HTTP.

## Testes

```bash
python -m pytest     # na raiz do repositorio; tudo offline, DataJud e backend simulados
ruff check .
```
