# Instalacao

English version: [INSTALLATION.en.md](INSTALLATION.en.md).

O NexJus tem quatro partes. So a extensao e necessaria; as outras sao opcionais e podem ser instaladas
depois, em qualquer ordem.

| Parte | Pasta | Para que serve | Requisitos |
| --- | --- | --- | --- |
| Extensao Chrome | `extension/` | Cadastros, prazos, alertas, leitura da pagina aberta e DataJud | Node.js 18 ou mais novo, Chrome ou outro navegador Chromium |
| Servidor MCP local | `mcp-server/` | Expor prazos e processos ao Claude (ou outro cliente MCP) | Python 3.11 ou mais novo |
| Skills e agentes | `skills/` | Skills e subagentes do Claude que usam o servidor MCP | Python 3.11 ou mais novo, Claude Code, Claude Desktop ou app web |
| Backend opcional | `app/` | Sincronizar dados entre maquinas, agenda diaria e alerta por e-mail | Python 3.11 ou mais novo; Docker se quiser Postgres |

> Aviso: todo prazo calculado e toda minuta gerada devem ser conferidos pelo advogado no sistema
> oficial do tribunal, do Detran ou do orgao autuador. A ferramenta e apoio, nao substitui essa conferencia.

Os comandos abaixo partem da raiz do repositorio. No Windows use `.venv\Scripts\` no lugar de
`.venv/bin/` e `copy` no lugar de `cp`.

## 1. Obter o codigo

```bash
git clone https://github.com/ThiagoVenturim/NexJus.git
cd NexJus
```

## 2. Extensao Chrome

```bash
cd extension
npm install
npm test             # testes do motor de prazos, CSV e DataJud
npm run build        # gera extension/dist
```

No Chrome:

1. Abra `chrome://extensions` e ative o **Modo do desenvolvedor**.
2. Clique em **Carregar sem compactacao** e escolha a pasta `extension/dist`.
3. Abra o popup da extensao. Os dados ficam em `chrome.storage.local`.

Recomendado: na aba **Seguranca LGPD** do popup, defina uma senha para criptografar os dados (AES-GCM com
chave derivada por PBKDF2). Sem a senha nao ha como recuperar os dados criptografados.

Para consultar o DataJud, informe na aba **Pagina Aberta e DataJud** o numero CNJ e a chave publica da API
do DataJud, divulgada pelo CNJ na documentacao da API Publica.

Para atualizar, rode `git pull` e `npm run build` de novo e clique em **Recarregar** em `chrome://extensions`.

## 3. Servidor MCP local (opcional)

```bash
cd mcp-server
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
```

Monte o arquivo de dados a partir da exportacao CSV da extensao (aba **Cadastros e CSV**, quadro
Importacao e Exportacao CSV). Salve cada exportacao como `clientes.csv`, `veiculos.csv`, `processos.csv` e `prazos.csv` numa pasta e rode:

```bash
.venv/bin/nexjus-mcp import-csv ./exportacao --output ./nexjus-data.json
.venv/bin/nexjus-mcp check
```

Ajuste `NEXJUS_MCP_DATA_FILE` no `.env` para apontar para esse arquivo. A ligacao com o Claude esta em
[USO-COM-CLAUDE.md](USO-COM-CLAUDE.md). Variaveis e ferramentas: [mcp-server/README.md](../mcp-server/README.md).

## 4. Skills e agentes do Claude (opcional)

O instalador usa apenas a biblioteca padrao do Python:

```bash
./skills/install.sh                      # instala em ~/.claude
./skills/install.sh install --project .  # instala em ./.claude (somente este projeto)
```

No Windows (PowerShell):

```powershell
.\skills\install.ps1
```

Detalhes, atualizacao e remocao: [skills/README.md](../skills/README.md).

## 5. Backend (opcional)

Com SQLite, numa maquina so:

```bash
cd app
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
.venv/bin/nexjus-backend serve           # aplica as migracoes e sobe em 127.0.0.1:8000
```

Antes de subir, preencha `NEXJUS_API_TOKEN` no `.env` com um valor aleatorio:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Com Postgres em Docker:

```bash
cd app
cp .env.example .env    # troque POSTGRES_PASSWORD e defina NEXJUS_API_TOKEN
docker compose up -d --build
```

As portas sao publicadas apenas em `127.0.0.1`. Para alcancar o backend de outra maquina, use uma VPN ou um
proxy reverso com HTTPS; nao exponha a porta direto na internet. Alertas por e-mail, agenda e sincronizacao:
[app/README.md](../app/README.md).

A extensao ainda nao envia dados ao backend. O protocolo de sincronizacao (`/sync/push` e `/sync/changes`)
esta pronto e documentado para essa integracao.

## 6. Conferir a instalacao

Na raiz do repositorio, com as dependencias de desenvolvimento instaladas:

```bash
python -m pytest                  # backend, servidor MCP e skills; tudo offline
ruff check .
python scripts/check_no_emoji.py
cd extension && npm test && npm run typecheck
```

## Arquivos de configuracao

- `.env` nunca vai para o Git. Use `app/.env.example` e `mcp-server/.env.example` como modelo; eles trazem
  apenas valores vazios ou de exemplo.
- Tokens, senhas e a chave do DataJud ficam no `.env` ou em variaveis de ambiente, nunca em arquivos
  versionados nem na configuracao compartilhada do cliente MCP.
