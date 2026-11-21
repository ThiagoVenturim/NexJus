---
name: client-report
description: Escreve um relatorio de andamento para o cliente, em linguagem simples, com a situacao do processo, os ultimos andamentos, os proximos prazos e o que o cliente precisa providenciar, a partir dos dados do servidor MCP do NexJus. Use quando o advogado pedir um relatorio, atualizacao ou mensagem de status para o cliente.
---

# Relatorio para o cliente

## Quando usar

- "Escreva uma atualizacao para o cliente sobre o processo X."
- "Relatorio mensal dos processos da cliente Maria S."
- "Mensagem explicando o ultimo andamento para o cliente."

## Ferramentas

- `mcp__nexjus__case_movements` e `mcp__nexjus__datajud_lookup_case`: andamentos e capa.
- `mcp__nexjus__list_deadlines`: prazos do processo ou do cliente (`processo` ou `cliente_id`).
- `mcp__nexjus__clients_with_pending_items`: para relatorios de varios processos do mesmo cliente.

## Passo a passo

1. Identifique o processo ou o cliente e busque andamentos e prazos com as ferramentas.
2. Traduza termos tecnicos ("concluso", "transitado em julgado", "intimacao") para frases simples, sem
   perder a precisao. Datas sempre por extenso ou no formato dd/mm/aaaa.
3. Diga o que aconteceu, o que vem a seguir e o que o cliente precisa fazer (documentos, pagamentos,
   presenca em audiencia), com datas quando houver.
4. Nao prometa resultado nem estime chance de exito. Nao inclua estrategia interna, valores de honorarios
   ou comentarios sobre a parte contraria, salvo pedido do advogado.
5. Entregue o texto para o advogado revisar antes do envio. Voce nao envia mensagens ao cliente.

## Formato da resposta

```
Assunto: Atualizacao do processo <numero> - <data>

Ola, <nome como veio do servidor>.
O que aconteceu: <2 a 4 frases>
Proximos passos: <lista com datas>
O que precisamos de voce: <lista ou "nada por enquanto">
Fonte dos andamentos: <DataJud | registro do escritorio>, consultado em <data>.

Pontos para o advogado revisar antes do envio: <[CONFERIR: ...]>
```

## Limites e LGPD

- O relatorio informa; nao e parecer nem conselho juridico definitivo. O advogado revisa e decide o que
  enviar.
- Toda afirmacao sobre o processo vem de um andamento ou prazo com data. Sem fonte verificavel, escreva
  `[CONFERIR: ...]`. Nunca invente andamento, data ou resultado.
- Nao inclua CPF, CNPJ, RG, telefone, e-mail, endereco ou RENAVAM no relatorio, nem dados de outros
  clientes. Use o nome do cliente como veio do servidor MCP.
- Nunca peca, mostre ou registre chaves de API e tokens; eles ficam no `.env` do servidor MCP.
