---
name: daily-triage
description: Monta a triagem do dia do escritorio com os prazos vencidos, de hoje, urgentes e da semana e os clientes com pendencias, a partir do servidor MCP do NexJus (arquivo local ou backend sincronizado), e sugere a ordem de trabalho. Use quando o advogado pedir a agenda do dia, a triagem, o que vence hoje ou nesta semana.
---

# Triagem diaria de prazos

## Quando usar

- "O que vence hoje?"
- "Monte minha triagem do dia."
- "Quais clientes tem pendencias nesta semana?"

## Ferramentas

- `mcp__nexjus__generate_agenda`: agenda em JSON e texto. `fonte=local` (arquivo do advogado) ou
  `fonte=backend` (agenda sincronizada do backend opcional, quando configurado).
- `mcp__nexjus__deadlines_this_week`: prazos pendentes ate domingo, mais os vencidos.
- `mcp__nexjus__clients_with_pending_items`: clientes com prazos vencidos ou proximos, por urgencia.
- `mcp__nexjus__record_movement`: somente quando o advogado pedir para registrar um andamento.

## Passo a passo

1. Chame `mcp__nexjus__generate_agenda` com `fonte=local`. Use `fonte=backend` apenas se o advogado
   pedir a agenda sincronizada; se o backend falhar, volte para `local` e avise.
2. Chame `mcp__nexjus__deadlines_this_week` e `mcp__nexjus__clients_with_pending_items` (padrao 7 dias).
3. Ordene: vencidos, hoje, urgentes (ate 3 dias) e depois os demais da semana. Dentro de cada grupo,
   pela data de vencimento.
4. Para cada prazo, sugira a proxima acao em uma linha (por exemplo, "protocolar defesa previa",
   "conferir publicacao"). Prazo vencido nao e tratado como perdido: aponte para o advogado verificar
   se houve cumprimento, suspensao ou erro de cadastro.
5. Registro de andamento: so com pedido explicito. Mostre antes o processo, a descricao e o prazo que
   seria criado e espere a confirmacao. Se o servidor estiver em modo somente leitura, informe.

## Formato da resposta

```
Triagem de <data>
Vencidos (<n>): <processo> - <titulo> - venceu em <data> - <acao sugerida>
Hoje (<n>): ...
Urgentes (<n>): ...
Restante da semana (<n>): ...
Clientes com pendencias: <nome abreviado> - <n> prazos - mais proximo em <data>
Fonte: NexJus (<local | backend>), gerado em <data e hora>. Conferir no sistema oficial.
```

## Limites e LGPD

- Isto apoia o trabalho do advogado; nao e parecer nem conselho juridico definitivo. A decisao final e
  do advogado responsavel, que confere cada prazo no sistema oficial.
- Toda afirmacao juridica traz a fonte. Sem fonte verificavel, escreva `[CONFERIR: ...]`. Nunca invente
  prazo, data ou numero de processo.
- Nao repita CPF, CNPJ, RG, telefone, e-mail, endereco ou RENAVAM. Use o nome do cliente como veio do
  servidor MCP (abreviado no modo `minimo`).
- Nunca peca, mostre ou registre chaves de API e tokens (`NEXJUS_API_TOKEN`, chave do DataJud); eles
  ficam no `.env` do servidor MCP.
