# Regras de calculo de prazo

English version: [DEADLINES.en.md](DEADLINES.en.md).

O motor de prazos existe em dois lugares com as mesmas regras e os mesmos casos de teste:

- extensao: `extension/src/domain/prazos.ts` (testes em `extension/tests/prazos.test.ts`);
- servidor MCP: `mcp-server/src/nexjus_mcp/prazos.py` (testes em `mcp-server/tests/test_mcp_prazos.py`),
  que tambem devolve a trilha de auditoria com cada dia pulado.

O backend (`app/`) nao calcula prazos. Ele usa a data de vencimento ja calculada para montar a agenda.

> Aviso: o resultado do motor e uma estimativa para conferencia. Todo prazo deve ser conferido pelo
> advogado no sistema oficial do tribunal, do Detran ou do orgao autuador, que prevalece sempre.

## Regras disponiveis

| Regra | Dias padrao | Contagem | Recesso de 20/12 a 20/01 | Fundamento |
| --- | --- | --- | --- | --- |
| `cpc_5` | 5 | dias uteis | suspende | CPC arts. 219, 220 e 224 |
| `cpc_15` | 15 | dias uteis | suspende | CPC arts. 219, 220 e 224 |
| `cpc_custom` | 10 (informe `dias_prazo`) | dias uteis | suspende | CPC arts. 219, 220 e 224 |
| `ctb_defesa_previa` | 30 | dias corridos, prorroga o termo final | nao se aplica | CTB, defesa previa |
| `ctb_jari` | 30 | dias corridos, prorroga o termo final | nao se aplica | CTB, recurso a JARI |
| `ctb_cetran` | 30 | dias corridos, prorroga o termo final | nao se aplica | CTB, recurso ao CETRAN |

No servidor MCP, `dias_prazo` e `contagem` podem ser informados em qualquer regra (de 1 a 3650 dias). Use
isso quando a notificacao de transito trouxer um prazo maior que 30 dias. O recurso `nexjus://regras`
devolve esta tabela em JSON. No popup da extensao aparecem `cpc_15`, `cpc_5` e as tres regras do CTB.

## Como o motor conta

1. O dia da publicacao ou notificacao nao conta (CPC art. 224).
2. O dia 1 e o primeiro dia util seguinte a publicacao ou notificacao, nas duas contagens.
3. Dias uteis (CPC): contam apenas dias uteis forenses (art. 219). Sabado, domingo, feriado e, nas regras
   do CPC, os dias de 20/12 a 20/01 (art. 220) ficam de fora.
4. Dias corridos (CTB): contam todos os dias a partir do dia 1. Se o ultimo dia cair em sabado, domingo ou
   feriado, o vencimento passa para o proximo dia util.
5. O dia do vencimento conta (CPC art. 224).

Um dia e nao util, nesta ordem de verificacao, quando e:

- sabado ou domingo;
- recesso forense de 20/12 a 20/01, somente nas regras do CPC;
- feriado nacional fixo: 01/01, 21/04, 01/05, 07/09, 12/10, 02/11, 15/11, 20/11 e 25/12;
- feriado movel: segunda e terca de Carnaval, Sexta-feira da Paixao e Corpus Christi, calculados a partir
  da Pascoa (algoritmo de Meeus/Jones/Butcher);
- feriado estadual da UF do prazo (tabela `FERIADOS_ESTADUAIS_POR_UF`);
- feriado local cadastrado em `feriadosLocais` para a mesma UF e, se informado, o mesmo municipio
  (comparacao sem diferenciar maiusculas).

## Exemplos

Todos com UF SP. Os tres primeiros casos estao nos testes do servidor MCP; o ultimo foi calculado pelo
mesmo motor.

| Regra | Publicacao ou notificacao | Dia 1 | Vencimento | Observacao |
| --- | --- | --- | --- | --- |
| `cpc_15` | sex 06/03/2026 | seg 09/03/2026 | sex 27/03/2026 | 15 dias uteis |
| `cpc_5` | sex 18/12/2026 | qui 21/01/2027 | qua 27/01/2027 | o recesso adia o dia 1 |
| `cpc_5`, municipio Sao Paulo com feriado local 25/01 | sex 22/01/2027 | ter 26/01/2027 | seg 01/02/2027 | 25/01 pulado como feriado local |
| `ctb_defesa_previa` | qui 05/03/2026 | sex 06/03/2026 | seg 06/04/2026 | o 30o dia (sab 04/04) foi prorrogado |

Resposta resumida de `calculate_deadline` para o ultimo exemplo:

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

## O que o motor nao faz

Confira manualmente, porque o motor nao aplica:

- prazo em dobro (Fazenda Publica, Ministerio Publico, Defensoria Publica, litisconsortes com procuradores
  diferentes em autos fisicos);
- suspensoes por portaria do tribunal, indisponibilidade do sistema ou fechamento do forum;
- feriados forenses proprios de cada tribunal ou comarca que nao estejam cadastrados como feriado local;
- ritos com regra propria (Juizados Especiais, processo penal, trabalhista), contagem em horas ou meses;
- data de publicacao: o motor parte da data informada. Na intimacao pelo Diario de Justica eletronico, a
  data de publicacao e o primeiro dia util seguinte ao da disponibilizacao (Lei 11.419/2006, art. 4,
  par. 3). Confira essa data antes de calcular;
- prazo de transito diferente de 30 dias: vale o que consta da notificacao.

A skill `deadline-checker` lembra o advogado desses pontos ao explicar o calculo.

## Como adicionar um tribunal, comarca ou Detran

### Feriado de tribunal ou de comarca

Para um feriado forense ou municipal, sem mudar codigo, cadastre um item em `feriadosLocais`:

```json
{"data": "01-25", "nome": "Aniversario de Sao Paulo", "uf": "SP", "municipio": "Sao Paulo"}
```

- `data` em `MM-DD` repete todo ano; em `YYYY-MM-DD` vale so naquele ano (use para pontos facultativos
  ou suspensoes de um ano).
- Sem `municipio`, o feriado vale para a UF inteira.
- No servidor MCP, edite o arquivo de `NEXJUS_MCP_DATA_FILE` e rode `nexjus-mcp check`. O backend tambem
  sincroniza a entidade `feriadosLocais`.
- Na extensao o campo existe no modelo de dados e e lido pelo motor, mas ainda nao ha tela para cadastra-lo.

### Feriado estadual fixo

Inclua a data na tabela `FERIADOS_ESTADUAIS_POR_UF` dos dois motores, com o mesmo nome:

1. `extension/src/domain/prazos.ts`;
2. `mcp-server/src/nexjus_mcp/prazos.py`;
3. um caso de teste em `extension/tests/prazos.test.ts` e o mesmo caso em `mcp-server/tests/test_mcp_prazos.py`.

Cite a lei estadual no pull request.

### Nova regra de prazo (por exemplo, um prazo especifico de Detran)

1. Extensao: acrescente a regra ao tipo `RegraPrazo` em `extension/src/types/models.ts`, aos parametros em
   `parametrosPadraoRegra` (`extension/src/domain/prazos.ts`) e, se for aparecer no popup, as opcoes do
   seletor em `extension/src/ui/App.tsx`.
2. Servidor MCP: acrescente a regra a `RegraPrazo` e `REGRAS`, a `parametros_padrao` e a `FUNDAMENTO` em
   `mcp-server/src/nexjus_mcp/prazos.py`, e ao tipo `Regra` em `mcp-server/src/nexjus_mcp/server.py`.
3. Skills: inclua a regra na lista da skill `deadline-checker`
   (`skills/src/nexjus_skills/assets/skills/deadline-checker/SKILL.md`).
4. Testes: o mesmo caso, com as mesmas datas, nos testes da extensao e do servidor MCP.

O fundamento legal precisa estar no texto de `FUNDAMENTO` e no pull request.

### Tribunal na consulta ao DataJud

O endpoint do DataJud sai do segmento `J.TR` do numero CNJ. Para um tribunal que falte, acrescente o par
`"J.TR": "api_publica_<sigla>"` em `MAPA_ENDPOINTS_DATAJUD` nos dois lugares:

- `extension/src/services/datajud.ts`;
- `mcp-server/src/nexjus_mcp/datajud.py`.

Use o alias exatamente como aparece na documentacao oficial da API Publica do DataJud e acrescente um caso
em `extension/tests/fontes_datajud.test.ts` e em `mcp-server/tests/test_mcp_datajud_store.py`.

### Portal de Detran ou de tribunal na leitura de pagina

1. Acrescente o dominio a `content_scripts.matches` em `extension/public/manifest.json`. Os dominios
   `*.jus.br` ja estao incluidos; os Detrans entram um a um.
2. Se o portal precisar de seletores proprios, ajuste `identificarPortal` e `lerPaginaAberta` em
   `extension/src/content/pageReader.ts`.
3. Mantenha as regras da leitura: so a pagina que o usuario abriu, sem login automatico, sem navegar
   sozinho e parando quando houver CAPTCHA (`detectarCaptchaNaPagina`).
