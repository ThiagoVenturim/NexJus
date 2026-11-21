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

English version: [README.en.md](README.en.md).
