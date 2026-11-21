---
name: jurisprudence-researcher
description: Organiza a pesquisa de jurisprudencia sobre uma tese - monta os termos de busca para os portais dos tribunais, le os julgados que o advogado colar ou que a busca do cliente trouxer e devolve uma tabela com tribunal, numero, relator, data, tese e trecho, sem citar nada que nao tenha fonte. Use quando o advogado pedir jurisprudencia, precedentes, sumulas ou temas sobre um assunto.
---

# Pesquisa de jurisprudencia com fonte

## Quando usar

- "Busque jurisprudencia do STJ sobre falta de notificacao da autuacao."
- "Organize estes acordaos que colei."
- "Existe sumula ou tema repetitivo sobre isso?"

## Ferramentas

O servidor MCP do NexJus nao pesquisa jurisprudencia. Use o material que o advogado colar ou indicar e,
se o cliente tiver busca na web habilitada, os resultados dela. `mcp__nexjus__datajud_lookup_case` serve
apenas para confirmar classe, tribunal e orgao de um numero CNJ citado.

## Passo a passo

1. Reformule a tese em uma frase e confirme com o advogado o tribunal e o periodo de interesse.
2. Monte os termos de busca: palavras-chave, sinonimos, operadores (E, OU, aspas) e os dispositivos
   legais relacionados. Nunca coloque nome de cliente, numero de documento ou dado do caso na busca.
3. Leia cada julgado do material. Extraia: tribunal, classe e numero, orgao julgador, relator, data de
   julgamento e de publicacao, tese decidida e um trecho literal da ementa que a sustente.
4. Classifique a forca de cada um: sumula vinculante, tema de repercussao geral ou repetitivo, sumula,
   decisao colegiada, decisao monocratica. Aponte divergencias entre julgados.
5. Julgado sem numero, data ou trecho verificavel nao entra na tabela; vai para "Nao confirmados".
   Nunca complete numero, relator ou data de memoria.

## Formato da resposta

```
Tese pesquisada: <frase>
Termos de busca: <strings prontas para colar no portal do tribunal>

| Tribunal | Classe e numero | Relator | Julgamento | Tese | Trecho da ementa |
| --- | --- | --- | --- | --- | --- |

Nao confirmados: <itens sem fonte completa, com o que falta>

## Fontes
- <julgado - onde foi obtido (colado pelo advogado, busca na web com o endereco exibido pelo cliente)>
```

## Limites e LGPD

- Isto apoia a pesquisa do advogado; nao e parecer nem conselho juridico definitivo. O advogado confere o
  inteiro teor no portal do tribunal antes de citar.
- Toda citacao traz a fonte. Sem fonte verificavel, o julgado vai para "Nao confirmados" ou recebe
  `[CONFERIR: ...]`. Nunca invente julgado, numero, relator, data, sumula, tema ou endereco de pagina.
- Termos de busca nunca levam nome, CPF, CNPJ, placa ou outro dado do cliente.
- Nunca peca, mostre ou registre chaves de API e tokens; eles ficam no `.env` do servidor MCP.
