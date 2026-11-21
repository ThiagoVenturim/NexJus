# Acompanhamento de NP

Ferramenta do dia a dia para advogados brasileiros: extensao para Chrome com cadastro de clientes,
processos e veiculos, motor de prazos (CPC, CTB, feriados e recesso forense), consultas ao DataJud,
servidor MCP local e agentes/skills para o Claude.

Status: em construcao.

## Aviso

Todo prazo calculado e toda minuta gerada devem ser conferidos pelo advogado no sistema oficial.
Esta ferramenta nao substitui a consulta ao tribunal, ao Detran ou ao orgao autuador.

## LGPD

Os dados ficam no computador do usuario por padrao. Nenhum dado de cliente e enviado a terceiros
sem acao explicita do usuario.

## Backend opcional

A pasta `app/` traz um servidor FastAPI opcional para sincronizar os dados entre maquinas, montar a
agenda diaria de prazos e enviar alertas por e-mail. Veja [app/README.md](app/README.md).

## Servidor MCP local

A pasta `mcp-server/` traz um servidor MCP local (stdio) que expoe prazos e processos a um cliente MCP,
como o Claude: calculo de prazos CPC/CTB com trilha de auditoria, listagens de prazos, agenda, clientes
com pendencias, registro de andamentos e consultas ao DataJud. Veja [mcp-server/README.md](mcp-server/README.md).

English version: [README.en.md](README.en.md).
