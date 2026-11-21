---
name: traffic-defense-drafter
description: Prepara minuta de defesa previa, recurso a JARI ou recurso ao CETRAN contra auto de infracao de transito, com calculo do prazo CTB pelo servidor MCP do NexJus, checklist dos requisitos do auto e fundamentos com fonte. Use quando o advogado pedir defesa de multa, defesa previa, recurso de multa, JARI ou CETRAN.
---

# Minuta de defesa e recurso de transito

## Quando usar

- "Prepare a defesa previa deste auto de infracao."
- "Minuta de recurso a JARI para a multa do processo X."
- "Ainda da tempo de recorrer ao CETRAN?"

## Ferramentas

- `mcp__nexjus__calculate_deadline` com `ctb_defesa_previa`, `ctb_jari` ou `ctb_cetran`.
- `mcp__nexjus__list_deadlines` e `mcp__nexjus__case_movements` para os dados ja cadastrados do processo.

## Passo a passo

1. Reuna os dados do auto: numero do auto (AIT), orgao autuador, data e local da infracao, enquadramento
   (artigo do CTB e codigo), data da notificacao, fase (autuacao, penalidade, JARI ou CETRAN). Use o que o
   advogado forneceu; o que faltar vira `[CONFERIR: ...]`. Nao invente dados do auto.
2. Calcule o prazo com `mcp__nexjus__calculate_deadline` e escreva a tempestividade com a data obtida.
   Se o prazo ja venceu, diga isso no inicio e pare a minuta ate o advogado decidir.
3. Confira os requisitos do auto (CTB art. 280) e a regularidade das notificacoes. Aponte so os vicios que
   o material mostra. Pontos de partida, a conferir no texto vigente:
   - CTB art. 280: elementos obrigatorios do auto de infracao;
   - CTB art. 281, par. unico, II: arquivamento se a notificacao da autuacao nao for expedida em 30 dias;
   - CTB art. 282: notificacao da penalidade;
   - CTB arts. 285 a 290: recurso a JARI e segunda instancia;
   - STJ, Sumula 312: exigencia das notificacoes da autuacao e da penalidade;
   - resolucoes do CONTRAN aplicaveis ao caso: `[CONFERIR: numero e artigo da resolucao vigente]`.
4. Escreva a minuta na estrutura abaixo, com tom tecnico e objetivo. Cada fundamento com a fonte entre
   parenteses. Jurisprudencia so se o advogado forneceu ou se veio de pesquisa com fonte (skill
   `jurisprudence-researcher`).
5. Liste os documentos a anexar (skill `document-checklist`).

## Formato da resposta

```
<Enderecamento: autoridade de transito ou JARI/CETRAN do orgao autuador>
Auto de infracao: <numero> - Placa: <placa como veio do servidor> - [CONFERIR: dados do requerente]
1. Da tempestividade - prazo calculado ate <data> (motor de prazos NexJus)
2. Dos fatos
3. Do direito - um topico por fundamento, com fonte
4. Dos pedidos - arquivamento do auto ou cancelamento da penalidade; pedidos subsidiarios
<Local, data, advogado, OAB: [CONFERIR]>

## Fontes
- <artigo, sumula ou precedente e de onde veio>

Rascunho gerado com apoio de IA para revisao do advogado responsavel. Conferir prazos, fatos e citacoes nos sistemas oficiais antes de usar.
```

Termine toda minuta com o aviso acima, literalmente. O advogado pode conferir o texto com
`nexjus-skills check minuta.md`.

## Limites e LGPD

- Isto e uma minuta de apoio, nao parecer nem conselho juridico definitivo. A decisao de protocolar e o
  texto final sao do advogado responsavel.
- Toda afirmacao juridica traz a fonte (artigo de lei, resolucao, sumula ou precedente). Sem fonte
  verificavel, escreva `[CONFERIR: ...]`. Nunca invente artigo, resolucao, precedente ou numero.
- Dados pessoais do requerente (CPF, RG, CNH, endereco, telefone, e-mail, RENAVAM) entram como marcadores
  `[CONFERIR: ...]`; o advogado preenche fora do chat.
- Nunca peca, mostre ou registre chaves de API e tokens; eles ficam no `.env` do servidor MCP.
