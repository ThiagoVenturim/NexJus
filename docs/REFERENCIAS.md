# Referencias e diferencial do acompanhamento_de_np

Projetos e servicos parecidos (open source e privados), o diferencial do nosso e o que melhorar com base neles. Pesquisa de 2026-11-08; verifique cada fonte antes de usar.

## Contexto
O acompanhamento_de_np e uma extensao Chrome MV3 (mais backend opcional, servidor MCP e skills) para apoiar advogados: le paginas que o usuario abriu (Senatran/RENAINF/Detran, PJe/eSAJ/Projudi) e usa a API publica DataJud. Nunca burla captcha.

## Parecidos

### Dados oficiais (base)
- **DataJud (CNJ)**: API publica com metadados de processos desde 2015 (capa, movimentacoes), autenticada por chave publica do CNJ. Boa para historico e jurimetria; limitacoes conhecidas: rate limit baixo, sem webhook, busca por CPF/CNPJ inconsistente.
- **Paineis de estatistica do CNJ**: atualizacao diaria a partir do DataJud.

### Privados / fechados
- **Escavador**, **Judit.io**, **Jusbrasil**, **Digesto**, **Loope/Projuris/Astrea** (gestao de escritorio): monitoramento processual por webhook/alertas em tempo real, busca por parte, jurimetria; servicos pagos.

### Open source / dev
- Bibliotecas e exemplos de consumo do DataJud e de dados do PJe (varios repos de desenvolvedores), sem um produto consolidado open source para advogado.

## Nosso diferencial
- **Open source e local-first**: a extensao le so o que o usuario abriu; dados ficam com ele, nao em um servico de terceiros.
- **Servidor MCP + skills**: o advogado usa o Claude sobre os proprios dados/processos, nao so um painel fechado.
- **Fontes combinadas**: transito (Senatran/RENAINF/Detran) + judicial (PJe/eSAJ/Projudi) + DataJud, com foco no fluxo real de quem acompanha NP.
- **Etica/legalidade**: content scripts so em paginas abertas pelo usuario; nunca burlar captcha; respeitar termos.

## O que melhorar aprendendo com eles
- **Monitoramento continuo com alerta** (Escavador/Judit tem webhook; o DataJud nao): montar polling eficiente dentro do rate limit e avisar mudancas, sem estourar a API.
- **Jurimetria** (tendencias por tribunal/classe/assunto) a partir do historico do DataJud, com graficos (via askdash).
- **Busca por parte (CPF/CNPJ)** onde a fonte permitir, contornando a inconsistencia do DataJud com cache local.
- **Gestao de prazos e tarefas** (como os sistemas de escritorio): integrar prazos processuais ao painel GTD do Nextor.
- **Combinar DataJud (historico) + fonte privada opcional** (se o usuario tiver conta), deixando claro o que e gratis e o que e pago.

## Sources
- https://www.cnj.jus.br/seminario-do-cnj-detalha-paineis-de-estatisticas-processuais-do-judiciario/
- https://portal.trt3.jus.br/internet/transparencia/tecnologia-da-informacao/dados-api/datajud
- https://judit.io/blog/apis-dados-juridicos-integracoes/apis-consulta-monitoramento-processual-2026/
- https://convergenciadigital.com.br/especial/cloud/api-do-cnj-abre-metadados-de-todo-o-poder-judicirio/
