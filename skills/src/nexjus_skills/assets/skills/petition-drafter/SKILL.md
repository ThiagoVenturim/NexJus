---
name: petition-drafter
description: Prepara minuta assistida de peticao (peticao simples, manifestacao, inicial civel ou contestacao) a partir dos fatos e documentos fornecidos e dos dados do processo no servidor MCP do NexJus, seguindo os requisitos do CPC e marcando tudo que o advogado precisa conferir. Use quando o advogado pedir uma minuta, rascunho ou modelo de peticao.
---

# Minuta assistida de peticao

## Quando usar

- "Faca uma minuta de manifestacao sobre o laudo."
- "Rascunho de contestacao com base nestes fatos."
- "Peticao simples juntando o comprovante de custas."

## Ferramentas

- `mcp__nexjus__datajud_lookup_case` e `mcp__nexjus__case_movements`: classe, orgao julgador e andamentos.
- `mcp__nexjus__list_deadlines` e `mcp__nexjus__calculate_deadline`: prazo da peca.

## Passo a passo

1. Pergunte o tipo de peca, o objetivo e os fatos, se nao vierem no pedido. Use apenas fatos fornecidos
   pelo advogado, os documentos indicados e os dados das ferramentas.
2. Busque o processo (numero CNJ ou id local) para enderecamento e contexto. Calcule o prazo da peca e
   abra a minuta pela tempestividade quando houver prazo.
3. Siga os requisitos legais do tipo de peca:
   - inicial: CPC art. 319 (juizo, partes, fatos e fundamentos, pedido, valor da causa, provas, opcao
     pela audiencia de conciliacao) e art. 320 (documentos indispensaveis);
   - contestacao: CPC art. 335 (prazo), art. 336 (toda a materia de defesa) e art. 337 (preliminares);
   - peticao simples e manifestacao: enderecamento, referencia ao processo, pedido objetivo.
4. Fundamente cada tese com fonte entre parenteses. Jurisprudencia so se veio do advogado ou de pesquisa
   com fonte (skill `jurisprudence-researcher`). Sem fonte, `[CONFERIR: ...]`.
5. Liste no final as premissas que voce assumiu e os pontos que dependem de decisao do advogado.

## Formato da resposta

```
<Enderecamento>
Processo n. <numero>
<Qualificacao: [CONFERIR: dados das partes]>
Tempestividade (se houver prazo): ate <data> (motor de prazos NexJus)
I - Dos fatos
II - Do direito (um topico por tese, com fonte)
III - Dos pedidos
<Local, data, advogado, OAB: [CONFERIR]>

## Fontes
- <artigo, sumula ou precedente e de onde veio>

## Premissas e pontos a decidir
- ...

Rascunho gerado com apoio de IA para revisao do advogado responsavel. Conferir prazos, fatos e citacoes nos sistemas oficiais antes de usar.
```

Termine toda minuta com o aviso acima, literalmente. O advogado pode conferir o texto com
`nexjus-skills check minuta.md`.

## Limites e LGPD

- Isto e uma minuta de apoio, nao parecer nem conselho juridico definitivo. A estrategia, as teses e o
  texto final sao do advogado responsavel.
- Toda afirmacao juridica traz a fonte (artigo de lei, sumula ou precedente). Sem fonte verificavel,
  escreva `[CONFERIR: ...]`. Nunca invente artigo, precedente, numero de processo, fato ou data.
- Dados pessoais das partes (CPF, CNPJ, RG, endereco, telefone, e-mail) entram como marcadores
  `[CONFERIR: ...]`; o advogado preenche fora do chat.
- Nunca peca, mostre ou registre chaves de API e tokens; eles ficam no `.env` do servidor MCP.
