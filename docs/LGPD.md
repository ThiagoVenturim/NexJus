# LGPD e privacidade

English version: [PRIVACY.en.md](PRIVACY.en.md).

O NexJus lida com dados de clientes de escritorio de advocacia: nomes, CPF ou CNPJ, telefone, e-mail,
placa, RENAVAM e numeros de processo. O projeto parte de tres regras:

1. Os dados ficam no computador do advogado por padrao.
2. Nada sai da maquina sem uma acao explicita do usuario, e o que sai e o minimo necessario.
3. O advogado continua responsavel pelo tratamento dos dados dos clientes (ele e o controlador, na
   linguagem da LGPD). A ferramenta ajuda a cumprir a lei, mas nao substitui as politicas do escritorio.

> Aviso: prazos e minutas gerados pela ferramenta devem ser conferidos pelo advogado no sistema oficial.
> Este documento descreve o comportamento do software; nao e parecer juridico sobre LGPD.

## Onde os dados ficam

| Parte | Onde guarda | Observacoes |
| --- | --- | --- |
| Extensao | `chrome.storage.local` do navegador | Criptografia opcional com senha (AES-GCM 256, chave derivada por PBKDF2 com 100.000 iteracoes e salt aleatorio). |
| Servidor MCP | Arquivo JSON local (`NEXJUS_MCP_DATA_FILE`) | Montado a partir da exportacao CSV. Nao le o arquivo criptografado da extensao. |
| Backend opcional | SQLite local ou Postgres | O `payload` de cada registro e guardado como texto opaco. Portas publicadas so em `127.0.0.1`. |
| Skills | Arquivos `SKILL.md` e de agentes em `~/.claude` ou `./.claude` | Nao guardam dados de clientes; so instrucoes. |

## O que pode sair da maquina

| Destino | Quando | O que vai |
| --- | --- | --- |
| API publica do DataJud (CNJ) | Quando o usuario consulta um processo | O numero CNJ e a chave publica da API. Nenhum dado do cliente. |
| Provedor do modelo de IA (por exemplo o Claude) | Quando o usuario conversa com o modelo usando o servidor MCP | Somente as respostas das ferramentas MCP, ja minimizadas (veja abaixo), e o que o proprio usuario digitar. |
| Backend do escritorio | Quando a sincronizacao estiver ligada | Registros com `payload` opaco. A extensao ainda nao sincroniza; o protocolo esta pronto no backend. |
| Servidor SMTP | Alerta diario, se `NEXJUS_SMTP_HOST` estiver definido | Contagens, datas e o identificador interno do prazo. Sem nomes, documentos ou numeros de processo. |

A leitura de pagina da extensao roda apenas na aba que o usuario abriu e no DOM dela (PJe, eSAJ, Projudi,
Senatran/RENAINF e Detran). Se houver CAPTCHA na pagina, a leitura para: a extensao nunca tenta resolver,
clicar ou contornar CAPTCHA, e nao faz login nem navega sozinha.

## Anonimizacao e minimizacao

### Servidor MCP

- CPF ou CNPJ, telefone, e-mail e RENAVAM nunca saem do servidor, em nenhum modo.
- Modo `minimo` (padrao, `NEXJUS_MCP_PRIVACY=minimo`): o nome do cliente vira primeiro nome e iniciais
  ("Maria Silva Oliveira" vira "Maria S. O."), a placa sai mascarada ("ABC1D23" vira "ABC***3") e CPF, CNPJ, e-mail e telefone que
  aparecem em textos livres, como titulos de prazo e andamentos, viram os marcadores `[cpf]`, `[cnpj]`,
  `[e-mail]` e `[telefone]`. Numeros de processo sao
  mantidos, porque sao necessarios para o trabalho e ja sao publicos no DataJud.
- Modo `completo`: nome e placa saem inteiros; os campos da primeira linha continuam fora.
- `NEXJUS_MCP_READ_ONLY=true` impede que o modelo grave andamentos ou prazos no arquivo.
- Logs vao para stderr e registram apenas identificadores internos e codigos HTTP.

### Skills e agentes

- As skills instruem o modelo a nao exibir CPF, CNPJ, RG, telefone, e-mail, endereco e RENAVAM e a nunca
  levar dados de clientes para buscas na web.
- `nexjus-skills check arquivo.md` confere um texto gerado antes do uso, sem rede e sem modelo: aponta CPF,
  CNPJ, e-mail e telefone visiveis (sem repetir o dado), marcadores `[CONFERIR: ...]` pendentes e minutas
  sem o aviso de revisao.

### Backend

- O servidor nao interpreta o `payload`. Recomenda-se envia-lo ja criptografado no cliente, para que o
  servidor nunca veja dados de clientes.
- Mensagens de erro e logs nunca repetem o payload. A URL do banco aparece com a senha mascarada.
- Registros excluidos perdem o payload no servidor; fica apenas o marcador de exclusao.

## Modelo local

O servidor MCP roda em stdio, sem abrir porta de rede, e nao depende de um modelo especifico. Para que
nenhum dado saia da maquina, conecte-o a um cliente MCP que use um modelo executado localmente. Nesse caso:

- a configuracao do servidor e a mesma (`nexjus-mcp serve` e as variaveis do `.env`);
- mantenha `NEXJUS_MCP_PRIVACY=minimo` mesmo com modelo local, porque historicos de conversa costumam
  ser gravados em disco pelo cliente;
- as skills foram escritas e testadas para o Claude; com outro modelo, confira com mais cuidado as
  respostas e use `nexjus-skills check` nas minutas.

Com o Claude ou outro modelo em nuvem, as respostas das ferramentas vao para o provedor do modelo.
Verifique os termos de uso e a politica de retencao de dados do plano contratado antes de usar com dados
de clientes.

## Direitos do titular

- Acesso e portabilidade: a aba **Cadastros e CSV** da extensao exporta clientes, veiculos, processos e
  prazos em CSV.
- Correcao e eliminacao: edite ou exclua o registro na extensao. No servidor MCP, o arquivo JSON pode ser
  regerado a partir de uma nova exportacao. No backend, a exclusao apaga o payload.
- Copias geradas fora da ferramenta (minutas salvas, historicos do cliente de IA, e-mails) ficam por conta
  do escritorio e precisam entrar na mesma rotina de eliminacao.

## Lista de conferencia do escritorio

- [ ] Senha de criptografia definida na extensao.
- [ ] `.env` fora do Git e com permissao de leitura apenas para o usuario.
- [ ] `NEXJUS_MCP_PRIVACY=minimo` e, se o modelo nao precisar gravar, `NEXJUS_MCP_READ_ONLY=true`.
- [ ] Termos do provedor do modelo de IA revisados, ou uso de modelo local.
- [ ] Backend, se usado, acessivel apenas por VPN ou HTTPS, com `NEXJUS_API_TOKEN` aleatorio.
- [ ] Minutas e relatorios conferidos com `nexjus-skills check` e revisados pelo advogado antes do envio.
