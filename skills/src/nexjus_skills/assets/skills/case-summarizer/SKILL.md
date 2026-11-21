---
name: case-summarizer
description: Resume um processo (capa e andamentos do DataJud ou do registro local do NexJus) ou uma peca processual colada pelo advogado, explicando cada andamento em linguagem clara e apontando prazos que podem ter sido abertos. Use quando o advogado pedir para resumir, ler ou explicar um processo, um andamento ou uma peca.
---

# Resumo de processo, andamento e peca

## Quando usar

- "Resuma o processo 0000001-23.2026.8.26.0100."
- "O que significa o ultimo andamento deste processo?"
- "Resuma esta contestacao" (com o texto colado ou um arquivo indicado).

## Ferramentas

- `mcp__nexjus__datajud_lookup_case`: capa do processo (tribunal, classe, orgao julgador) e ultimos movimentos.
- `mcp__nexjus__case_movements`: movimentos do mais recente ao mais antigo (`fonte` `auto`, `datajud` ou `local`).
- `mcp__nexjus__list_deadlines`: prazos ja cadastrados para o processo (parametro `processo`).

## Passo a passo

1. Processo: use o numero CNJ ou o id local. Chame `mcp__nexjus__datajud_lookup_case` e
   `mcp__nexjus__case_movements`. Se o DataJud estiver desligado, use `fonte=local` e diga que o registro
   local guarda apenas o ultimo andamento.
2. Explique cada andamento relevante em uma frase simples (por exemplo, "Conclusos para decisao": o
   processo foi enviado ao juiz para decidir). Indique a data e a origem (DataJud ou registro local).
3. Aponte andamentos que costumam abrir prazo (intimacao, citacao, publicacao de decisao ou sentenca) e
   cruze com `mcp__nexjus__list_deadlines`. Prazo aberto sem cadastro vira um item em "Pontos de atencao";
   para calcular, indique a skill `deadline-checker`. Nao registre nada no processo.
4. Peca colada: identifique partes por polo, pedidos, fundamentos legais citados, provas, valor da causa
   e prazos mencionados. Cite o trecho de origem (pagina, item ou paragrafo) de cada ponto.
5. Separe o que esta no material do que e inferencia sua, e marque a inferencia como tal. Nao preveja o
   resultado do processo.

## Formato da resposta

```
Processo: <numero> - <classe> - <orgao julgador> (fonte: DataJud | registro local)
Situacao atual: <2 a 3 frases>
Andamentos recentes:
- <data> - <andamento> - <explicacao simples>
Prazos cadastrados: <lista ou "nenhum">
Pontos de atencao: <prazos possivelmente abertos, documentos faltando, [CONFERIR: ...]>
```

Para pecas: "Partes", "Pedidos", "Fundamentos citados", "Provas", "Prazos mencionados", cada item com a
referencia do trecho.

## Limites e LGPD

- Isto apoia o trabalho do advogado; nao e parecer nem conselho juridico definitivo. A decisao final e
  do advogado responsavel.
- Toda afirmacao juridica traz a fonte: o andamento, o trecho da peca ou o artigo citado. Sem fonte
  verificavel, escreva `[CONFERIR: ...]`. Nunca invente andamento, data, precedente ou numero.
- Nao repita CPF, CNPJ, RG, telefone, e-mail, endereco ou RENAVAM que aparecam na peca; use `[cpf]`,
  `[telefone]` e marcadores equivalentes. Use o nome do cliente como veio do servidor MCP.
- Nunca peca, mostre ou registre chaves de API e tokens; eles ficam no `.env` do servidor MCP.
