---
name: document-checklist
description: Monta a lista de documentos para uma peca ou procedimento (defesa ou recurso de multa de transito, peticao inicial civel, contestacao, cumprimento de sentenca), separando o que a lei exige, com o artigo, do que e recomendado, e marcando o que ja consta no processo do NexJus. Use quando o advogado perguntar quais documentos juntar ou pedir um checklist.
---

# Checklist de documentos

## Quando usar

- "Quais documentos preciso para a defesa previa?"
- "Checklist para a inicial desta acao de cobranca."
- "O que falta juntar neste processo?"

## Ferramentas

- `mcp__nexjus__case_movements` e `mcp__nexjus__list_deadlines`: fase do processo e prazo para juntar.

## Passo a passo

1. Identifique o tipo de peca ou procedimento e, se houver, o processo. Pergunte se nao estiver claro.
2. Separe os itens em tres grupos:
   - exigidos por lei, com o artigo (por exemplo, procuracao: CPC art. 287; documentos indispensaveis
     da inicial: CPC art. 320; custas ou pedido de gratuidade: CPC arts. 82 e 99);
   - exigidos pelo orgao ou tribunal (formulario do orgao autuador, regras de peticionamento eletronico):
     marque `[CONFERIR: exigencia do orgao]`, pois variam por orgao;
   - recomendados para a prova dos fatos (fotos, comprovantes, testemunhas).
3. Para transito, inclua no minimo: copia da notificacao da autuacao ou da penalidade, documento do
   veiculo, documento de habilitacao do condutor, procuracao e documento do requerente, e indique quais o
   orgao pede no proprio formulario como `[CONFERIR: exigencia do orgao]`.
4. Se o advogado disse quais documentos ja tem, marque-os. Nao peca a copia dos documentos no chat.
5. Indique o prazo para juntar quando houver (skill `deadline-checker`).

## Formato da resposta

```
Checklist: <tipo de peca> - processo <numero ou "novo">
Exigidos por lei:
[ ] <documento> - <fonte>
Exigidos pelo orgao ou tribunal:
[ ] <documento> - [CONFERIR: exigencia do orgao]
Recomendados:
[ ] <documento> - <para que serve>
Prazo: <data e fonte, se houver>
```

## Limites e LGPD

- Isto apoia o trabalho do advogado; nao e parecer nem conselho juridico definitivo. O advogado decide o
  que juntar.
- Todo item "exigido por lei" traz o artigo. Sem fonte verificavel, mova para outro grupo ou escreva
  `[CONFERIR: ...]`. Nunca invente artigo ou exigencia.
- Nao peca que o usuario cole documentos pessoais no chat e nao repita CPF, CNPJ, RG, telefone, e-mail,
  endereco ou RENAVAM.
- Nunca peca, mostre ou registre chaves de API e tokens; eles ficam no `.env` do servidor MCP.
