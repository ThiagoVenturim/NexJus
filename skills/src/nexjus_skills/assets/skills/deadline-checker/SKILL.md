---
name: deadline-checker
description: Calcula e explica prazos processuais CPC (dias uteis, recesso de 20/12 a 20/01) e prazos de defesa e recurso de transito CTB usando o motor de prazos do servidor MCP do NexJus, com a trilha dos dias pulados e o fundamento legal. Use quando o advogado pedir para calcular, conferir ou explicar um prazo, ou perguntar quando vence um prazo.
---

# Calculo e explicacao de prazos

## Quando usar

- "Quando vence o prazo de 15 dias desta intimacao publicada em 03/03?"
- "Confira se o vencimento que anotei para a defesa previa esta certo."
- "Por que o prazo pulou estes dias?"

## Ferramentas

- `mcp__nexjus__calculate_deadline`: calcula o vencimento e devolve `dias_pulados` (data, motivo e fase).
- `mcp__nexjus__list_deadlines`: prazos ja cadastrados, para conferir um prazo existente pelo processo.
- Recurso `nexjus://regras`: regras suportadas, dias padrao e fundamento de cada uma.

## Passo a passo

1. Identifique a regra: `cpc_5`, `cpc_15`, `cpc_custom` (informe `dias_prazo`), `ctb_defesa_previa`,
   `ctb_jari` ou `ctb_cetran`. Se o pedido nao deixar claro, pergunte antes de calcular.
2. Confirme a data de inicio: para intimacao pelo Diario de Justica eletronico, a data de publicacao e o
   primeiro dia util seguinte ao da disponibilizacao (Lei 11.419/2006, art. 4, par. 3). Para CTB, a data
   da notificacao. Pergunte a UF e, se houver, o municipio (feriados locais).
3. Chame `mcp__nexjus__calculate_deadline`. Nunca calcule o vencimento de cabeca quando a ferramenta
   estiver disponivel. Sem o servidor MCP, diga que o calculo nao foi feito pela ferramenta e marque o
   resultado com `[CONFERIR: calculo manual]`.
4. Explique o resultado: dia do comeco excluido e do vencimento incluido (CPC art. 224), dias uteis
   (CPC art. 219), suspensao de 20/12 a 20/01 (CPC art. 220) ou contagem corrida com prorrogacao (CTB).
   Liste cada dia pulado com o motivo que a ferramenta devolveu.
5. Se o advogado trouxe uma data propria e ela diverge, mostre as duas e aponte o dia que explica a
   diferenca. Nao diga qual esta certa sem a trilha da ferramenta.
6. Avise sobre regras que o motor nao aplica e que podem mudar o prazo:
   - prazo em dobro: Ministerio Publico (CPC art. 180), Fazenda Publica (CPC art. 183), Defensoria
     (CPC art. 186), litisconsortes com procuradores diferentes em autos fisicos (CPC art. 229);
   - Juizados Especiais (Lei 9.099/1995, art. 12-A), processo do trabalho (CLT art. 775) e processo
     penal (CPP art. 798), que tem regras proprias;
   - suspensoes por portaria do tribunal, indisponibilidade do sistema e feriados locais nao cadastrados.

## Formato da resposta

```
Vencimento: <data> (<dia da semana>)
Regra: <regra> - <fundamento devolvido pela ferramenta>
Inicio da contagem: <data>
Dias pulados: <data - motivo>, ...
Pontos a conferir: <regras especiais ou [CONFERIR: ...]>
Fonte: motor de prazos do NexJus (calculate_deadline). Conferir no sistema oficial do tribunal ou orgao.
```

## Limites e LGPD

- Isto apoia o trabalho do advogado; nao e parecer nem conselho juridico definitivo. A decisao final e
  do advogado responsavel, que confere o prazo no sistema oficial.
- Toda afirmacao juridica traz a fonte (artigo de lei, sumula ou precedente). Sem fonte verificavel,
  escreva `[CONFERIR: ...]`. Nunca invente artigo, precedente, numero de processo ou data.
- Nao repita CPF, CNPJ, RG, telefone, e-mail, endereco ou RENAVAM. Use o nome do cliente como veio do
  servidor MCP (abreviado no modo `minimo`).
- Nunca peca, mostre ou registre chaves de API e tokens; eles ficam no `.env` do servidor MCP.
