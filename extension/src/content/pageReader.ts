import type { LeituraPaginaResultado, PortalOrigem } from "../types/models";

const CAPTCHA_SELECTORS = [
  ".g-recaptcha",
  ".h-captcha",
  ".cf-turnstile",
  "iframe[src*='recaptcha']",
  "iframe[src*='hcaptcha']",
  "iframe[src*='turnstile']",
  "img[src*='captcha' i]",
  "img[id*='captcha' i]",
  "input[name*='captcha' i]",
  "input[id*='captcha' i]",
  "[data-sitekey]",
  "#desafio-captcha",
  ".captcha-container",
];

const CNJ_REGEX = /\b(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b/;
const PLACA_REGEX = /\b([A-Z]{3}-?\d[A-Z0-9]\d{2})\b/i;
const RENAVAM_REGEX = /\bRENAVAM[:\s]*(\d{9,11})\b/i;
const AIT_REGEX = /\b(?:AIT|Auto de Infracao|Notificacao)[:\s#-]*([A-Z0-9-]{5,20})\b/i;

/**
 * Detecta se a pagina aberta pelo usuario exibe desafio de CAPTCHA ou verificacao anti-bot.
 * A extensao NUNCA tenta resolver, clicar ou contornar CAPTCHAs; apenas interrompe a leitura
 * e orienta o usuario a concluir a verificacao manualmente na aba do navegador.
 */
export function detectarCaptchaNaPagina(doc: Document): boolean {
  for (const selector of CAPTCHA_SELECTORS) {
    if (doc.querySelector(selector)) {
      return true;
    }
  }
  return false;
}

export function identificarPortal(url: string, doc: Document): PortalOrigem {
  const lower = url.toLowerCase();
  const bodyText = (doc.body?.textContent ?? "").toLowerCase();

  if (lower.includes("pje.") || lower.includes("/pje") || doc.querySelector("[id*='pje' i], meta[content*='PJe']")) {
    return "pje";
  }
  if (lower.includes("esaj.") || lower.includes("/esaj") || lower.includes("/cpopg") || doc.querySelector("#numeroProcesso, .unj-entity-header")) {
    return "esaj";
  }
  if (lower.includes("projudi") || bodyText.includes("sistema projudi")) {
    return "projudi";
  }
  if (lower.includes("senatran") || lower.includes("renainf") || bodyText.includes("senatran") || bodyText.includes("renainf")) {
    return "senatran";
  }
  if (lower.includes("detran") || bodyText.includes("detran")) {
    return "detran";
  }
  return "desconhecido";
}

function extrairTextoSeletor(doc: Document, selectors: string[]): string | undefined {
  for (const sel of selectors) {
    const el = doc.querySelector(sel);
    const txt = el?.textContent?.trim();
    if (txt) {
      return txt.replace(/\s+/g, " ");
    }
  }
  return undefined;
}

/**
 * Le apenas o DOM da pagina atualmente aberta pelo usuario no navegador.
 * Nunca faz scraping em background nem contorna CAPTCHA.
 */
export function lerPaginaAberta(doc: Document, url: string): LeituraPaginaResultado {
  const portal = identificarPortal(url, doc);

  if (detectarCaptchaNaPagina(doc)) {
    return {
      status: "captcha_blocked",
      portal,
      url,
      mensagem:
        "Captcha detectado na pagina aberta. Por seguranca e conformidade, o NexJus nunca contorna captcha. Resolva o desafio manualmente no navegador e tente novamente.",
    };
  }

  const fullText = (doc.body?.textContent ?? "").replace(/\s+/g, " ");

  if (portal === "pje" || portal === "esaj" || portal === "projudi") {
    const numeroNoDom = extrairTextoSeletor(doc, [
      "#numeroProcesso",
      ".numero-processo",
      "[data-testid='numero-processo']",
      "#fPP\\:numeroProcesso",
    ]);
    const cnjMatch = (numeroNoDom ?? fullText).match(CNJ_REGEX);
    const numeroProcesso = cnjMatch ? cnjMatch[1] : numeroNoDom;

    const classeOuInfracao = extrairTextoSeletor(doc, [
      "#classeProcesso",
      ".classe-processual",
      "[data-testid='classe-judicial']",
    ]);
    const orgaoOuTribunal = extrairTextoSeletor(doc, [
      "#orgaoJulgadorProcesso",
      "#varaProcesso",
      ".orgao-julgador",
    ]) ?? portal.toUpperCase();
    const ultimoAndamento = extrairTextoSeletor(doc, [
      "#tabelaUltimasMovimentacoes tr:first-child .descricaoMovimentacao",
      ".movimentacao-item:first-child .descricao",
      ".ultimo-andamento",
    ]);
    const dataUltimaMovimentacao = extrairTextoSeletor(doc, [
      "#tabelaUltimasMovimentacoes tr:first-child .dataMovimentacao",
      ".movimentacao-item:first-child .data",
      ".data-ultimo-andamento",
    ]);

    const partesNodes = Array.from(
      doc.querySelectorAll("#tablePartesPrincipais .nomeParteEAdvogado, .parte-nome")
    )
      .map((el) => el.textContent?.trim() ?? "")
      .filter(Boolean);

    return {
      status: "ok",
      portal,
      url,
      mensagem: `Dados lidos da pagina aberta (${portal.toUpperCase()}). Confira no sistema oficial antes de salvar.`,
      dados: {
        numeroProcesso,
        orgaoOuTribunal,
        classeOuInfracao,
        partes: partesNodes.length > 0 ? partesNodes : undefined,
        ultimoAndamento,
        dataUltimaMovimentacao,
      },
    };
  }

  if (portal === "senatran" || portal === "detran") {
    const placaDom = extrairTextoSeletor(doc, [
      "[data-campo='placa']",
      "#placaVeiculo",
      ".placa-veiculo",
    ]);
    const placaMatch = (placaDom ?? fullText).match(PLACA_REGEX);
    const placa = placaMatch ? placaMatch[1].toUpperCase().replace("-", "") : placaDom;

    const renavamDom = extrairTextoSeletor(doc, [
      "[data-campo='renavam']",
      "#renavamVeiculo",
      ".renavam-veiculo",
    ]);
    const renavamMatch = fullText.match(RENAVAM_REGEX);
    const renavam = renavamDom ?? (renavamMatch ? renavamMatch[1] : undefined);

    const aitDom = extrairTextoSeletor(doc, [
      "[data-campo='ait']",
      "#numeroAutoInfracao",
      ".numero-ait",
    ]);
    const aitMatch = fullText.match(AIT_REGEX);
    const ait = aitDom ?? (aitMatch ? aitMatch[1] : undefined);

    const orgaoOuTribunal = extrairTextoSeletor(doc, [
      "[data-campo='orgaoAutuador']",
      "#orgaoAutuador",
      ".orgao-autuador",
    ]) ?? portal.toUpperCase();

    const classeOuInfracao = extrairTextoSeletor(doc, [
      "[data-campo='enquadramento']",
      "#descricaoInfracao",
      ".descricao-infracao",
    ]);

    const ultimoAndamento = extrairTextoSeletor(doc, [
      "[data-campo='situacao']",
      "#situacaoInfracao",
      ".situacao-multa",
    ]);

    const dataUltimaMovimentacao = extrairTextoSeletor(doc, [
      "[data-campo='dataNotificacao']",
      "#dataNotificacao",
      ".data-notificacao",
    ]);

    return {
      status: "ok",
      portal,
      url,
      mensagem: `Dados de transito lidos da pagina aberta (${portal.toUpperCase()}).`,
      dados: {
        ait,
        numeroProcesso: ait,
        placa,
        renavam,
        orgaoOuTribunal,
        classeOuInfracao,
        ultimoAndamento,
        dataUltimaMovimentacao,
      },
    };
  }

  // Fallback para qualquer pagina aberta pelo usuario que contenha numero CNJ ou placa
  const cnjMatch = fullText.match(CNJ_REGEX);
  const placaMatch = fullText.match(PLACA_REGEX);
  if (cnjMatch || placaMatch) {
    return {
      status: "ok",
      portal: "desconhecido",
      url,
      mensagem: "Dados identificados na pagina aberta pelo usuario.",
      dados: {
        numeroProcesso: cnjMatch ? cnjMatch[1] : undefined,
        placa: placaMatch ? placaMatch[1].toUpperCase().replace("-", "") : undefined,
      },
    };
  }

  return {
    status: "unsupported",
    portal: "desconhecido",
    url,
    mensagem: "Nenhum portal juridico/transito suportado foi identificado na aba atual.",
  };
}
