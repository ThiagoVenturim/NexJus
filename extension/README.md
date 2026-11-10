# NexJus - Extensao Chrome MV3

Extensao Chrome Manifest V3 construida em TypeScript, Vite e React para gestao local de clientes, processos, veiculos, calculo de prazos processuais (CPC e CTB), leitura assistida de paginas abertas pelo usuario e consulta a API publica do DataJud (CNJ).

## Funcionalidades

1. **Cadastro de Clientes, Processos e Veiculos**:
   - Armazenamento local em `chrome.storage.local` com criptografia opcional AES-GCM 256 bits (derivacao PBKDF2 com 100.000 iteracoes e salt aleatorio).
   - Importacao e exportacao CSV (RFC 4180) com protecao contra injecao de formulas em planilhas.
2. **Motor de Prazos (CPC e CTB)**:
   - Contagem em dias uteis para prazos do CPC (arts. 219 e 224), excluindo o dia da publicacao e iniciando no primeiro dia util seguinte.
   - Suspensao automatica durante o recesso forense de 20/12 a 20/01 (CPC art. 220).
   - Feriados nacionais fixos, moveis (Carnaval, Sexta-feira da Paixao e Corpus Christi), estaduais por UF e feriados municipais customizados.
   - Prazos de transito do CTB (Defesa Previa, Recurso JARI e Recurso CETRAN - minimo de 30 dias corridos com prorrogacao automatica para o primeiro dia util seguinte).
3. **Alertas com `chrome.alarms`**:
   - Verificacao periodica dos prazos cadastrados e atualizacao do indicador (badge) da extensao com o total de prazos vencidos, vencendo hoje ou urgentes (ate 3 dias).
4. **Leitura de Paginas Abertas e Consulta DataJud**:
   - Content script que le exclusivamente o DOM da pagina que o proprio usuario abriu (PJe, eSAJ, Projudi, Senatran/RENAINF e Detran).
   - Bloqueio imediato caso haja desafio de CAPTCHA na pagina: a extensao nunca tenta resolver, clicar ou contornar CAPTCHA.
   - Cliente para consulta automatica na API publica do DataJud (`https://api-publica.datajud.cnj.jus.br`) com validacao do digito verificador CNJ (mod 97) e cache local.

## Desenvolvimento e Testes

```bash
cd extension
npm install
npm test
npm run typecheck
npm run build
```

Para carregar no Chrome:
1. Execute `npm run build` dentro de `extension/`.
2. Abra `chrome://extensions`, ative o **Modo do desenvolvedor** e clique em **Carregar sem compactacao** selecionando a pasta `extension/dist`.
