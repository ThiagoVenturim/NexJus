import type { FeriadoLocal, Prazo, RegraPrazo, TipoContagem, UF } from "../types/models";

/**
 * Feriados nacionais fixos (MM-DD).
 */
const FERIADOS_NACIONAIS_FIXOS: Record<string, string> = {
  "01-01": "Confraternizacao Universal",
  "04-21": "Tiradentes",
  "05-01": "Dia do Trabalhador",
  "09-07": "Independencia do Brasil",
  "10-12": "Nossa Senhora Aparecida",
  "11-02": "Finados",
  "11-15": "Proclamacao da Republica",
  "11-20": "Dia Nacional de Zumbi e da Consciencia Negra",
  "12-25": "Natal",
};

/**
 * Feriados estaduais principais por UF (MM-DD).
 */
const FERIADOS_ESTADUAIS_POR_UF: Partial<Record<UF, Record<string, string>>> = {
  AC: { "01-23": "Dia do Evangelico", "06-15": "Aniversario do Acre", "09-05": "Dia da Amazonia", "11-17": "Tratado de Petropolis" },
  AL: { "06-24": "Sao Joao", "06-29": "Sao Pedro", "09-16": "Emancipacao Politica de Alagoas" },
  AP: { "03-19": "Dia de Sao Jose", "09-13": "Criacao do Territorio Federal" },
  AM: { "09-05": "Elevacao do Amazonas a Categoria de Provincia", "12-08": "Nossa Senhora da Conceicao" },
  BA: { "07-02": "Independencia da Bahia" },
  CE: { "03-19": "Sao Jose", "03-25": "Data Magna do Ceara" },
  DF: { "11-30": "Dia do Evangelico" },
  ES: { "05-23": "Colonizacao do Solo Espirito-Santense" },
  GO: { "10-24": "Pedra Fundamental de Goiania" },
  MA: { "07-28": "Adesao do Maranhao a Independencia" },
  MT: { "11-20": "Consciencia Negra" },
  MS: { "10-11": "Criacao do Estado de Mato Grosso do Sul" },
  MG: { "04-21": "Data Magna de Minas Gerais" },
  PA: { "08-15": "Adesao do Grao-Para a Independencia" },
  PB: { "08-05": "Fundacao do Estado da Paraiba" },
  PR: { "12-19": "Emancipacao Politica do Parana" },
  PE: { "03-06": "Data Magna de Pernambuco", "06-24": "Sao Joao" },
  PI: { "10-19": "Dia do Piaui" },
  RJ: { "04-23": "Dia de Sao Jorge" },
  RN: { "10-03": "Martires de Cunhau e Uruacu" },
  RS: { "09-20": "Revolucao Farroupilha" },
  RO: { "01-04": "Instalacao do Estado de Rondonia", "06-18": "Dia do Evangelico" },
  RR: { "10-05": "Criacao do Estado de Roraima" },
  SC: { "08-11": "Criacao da Capitania de Santa Catarina" },
  SP: { "07-09": "Revolucao Constitucionalista de 1932" },
  SE: { "07-08": "Emancipacao Politica de Sergipe" },
  TO: { "10-05": "Criacao do Estado do Tocantins" },
};

export function parseISODate(iso: string): Date {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim());
  if (!match) {
    throw new Error(`Data invalida (esperado YYYY-MM-DD): ${iso}`);
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const d = new Date(Date.UTC(year, month - 1, day));
  if (
    d.getUTCFullYear() !== year ||
    d.getUTCMonth() !== month - 1 ||
    d.getUTCDate() !== day
  ) {
    throw new Error(`Data inexistente no calendario: ${iso}`);
  }
  return d;
}

export function formatISODate(date: Date): string {
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function addDaysUTC(date: Date, days: number): Date {
  const next = new Date(date.getTime());
  next.setUTCDate(next.getUTCDate() + days);
  return next;
}

/**
 * Algoritmo de Meeus/Jones/Butcher para Domingo de Pascoa em UTC.
 */
export function calcularPascoaUTC(year: number): Date {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(Date.UTC(year, month - 1, day));
}

/**
 * Feriados moveis nacionais e forenses (Segunda e Terca de Carnaval, Sexta-Feira Santa, Corpus Christi).
 */
export function obterFeriadosMoveisAno(year: number): Record<string, string> {
  const pascoa = calcularPascoaUTC(year);
  const segundaCarnaval = formatISODate(addDaysUTC(pascoa, -48));
  const tercaCarnaval = formatISODate(addDaysUTC(pascoa, -47));
  const sextaSanta = formatISODate(addDaysUTC(pascoa, -2));
  const corpusChristi = formatISODate(addDaysUTC(pascoa, 60));

  return {
    [segundaCarnaval]: "Segunda-feira de Carnaval",
    [tercaCarnaval]: "Terca-feira de Carnaval",
    [sextaSanta]: "Sexta-feira da Paixao",
    [corpusChristi]: "Corpus Christi",
  };
}

/**
 * Verifica se a data cai no recesso forense do CPC art. 220 (20/12 a 20/01, inclusive).
 */
export function isRecessoForenseCPC(date: Date): boolean {
  const month = date.getUTCMonth() + 1; // 1..12
  const day = date.getUTCDate();
  if (month === 12 && day >= 20) {
    return true;
  }
  if (month === 1 && day <= 20) {
    return true;
  }
  return false;
}

export function isFimDeSemana(date: Date): boolean {
  const dow = date.getUTCDay();
  return dow === 0 || dow === 6;
}

function normalizarMunicipio(m?: string): string {
  return (m ?? "").trim().toLowerCase();
}

export function isFeriado(
  date: Date,
  uf: UF,
  municipio?: string,
  feriadosLocais: FeriadoLocal[] = []
): boolean {
  const iso = formatISODate(date);
  const mmdd = iso.slice(5);
  const year = date.getUTCFullYear();

  if (FERIADOS_NACIONAIS_FIXOS[mmdd]) {
    return true;
  }

  const moveis = obterFeriadosMoveisAno(year);
  if (moveis[iso]) {
    return true;
  }

  const estaduais = FERIADOS_ESTADUAIS_POR_UF[uf];
  if (estaduais && estaduais[mmdd]) {
    return true;
  }

  const muniTarget = normalizarMunicipio(municipio);
  for (const fl of feriadosLocais) {
    if (fl.uf !== uf) {
      continue;
    }
    const flMuni = normalizarMunicipio(fl.municipio);
    if (flMuni && flMuni !== muniTarget) {
      continue;
    }
    if (fl.data === iso || fl.data === mmdd) {
      return true;
    }
  }

  return false;
}

export interface OpcoesCalculoPrazo {
  regra: RegraPrazo;
  dataPublicacaoOuNotificacao: string; // YYYY-MM-DD
  diasPrazo?: number;
  contagem?: TipoContagem;
  uf: UF;
  municipio?: string;
  feriadosLocais?: FeriadoLocal[];
}

export interface ResultadoCalculoPrazo {
  regra: RegraPrazo;
  diasPrazo: number;
  contagem: TipoContagem;
  consideraRecessoCPC: boolean;
  dataPublicacaoOuNotificacao: string;
  dataInicioContagem: string;
  dataVencimento: string;
}

export function parametrosPadraoRegra(regra: RegraPrazo): {
  diasPrazo: number;
  contagem: TipoContagem;
  consideraRecessoCPC: boolean;
} {
  switch (regra) {
    case "cpc_5":
      return { diasPrazo: 5, contagem: "uteis", consideraRecessoCPC: true };
    case "cpc_15":
      return { diasPrazo: 15, contagem: "uteis", consideraRecessoCPC: true };
    case "cpc_custom":
      return { diasPrazo: 10, contagem: "uteis", consideraRecessoCPC: true };
    case "ctb_defesa_previa":
      return { diasPrazo: 30, contagem: "corridos", consideraRecessoCPC: false };
    case "ctb_jari":
      return { diasPrazo: 30, contagem: "corridos", consideraRecessoCPC: false };
    case "ctb_cetran":
      return { diasPrazo: 30, contagem: "corridos", consideraRecessoCPC: false };
  }
}

export function isDiaUtilForense(
  date: Date,
  uf: UF,
  municipio: string | undefined,
  feriadosLocais: FeriadoLocal[],
  consideraRecessoCPC: boolean
): boolean {
  if (isFimDeSemana(date)) {
    return false;
  }
  if (consideraRecessoCPC && isRecessoForenseCPC(date)) {
    return false;
  }
  if (isFeriado(date, uf, municipio, feriadosLocais)) {
    return false;
  }
  return true;
}

/**
 * Calcula o prazo processual judicial (CPC arts. 219, 220 e 224) ou administrativo de transito (CTB).
 * - Exclui o dia do comeco e inclui o do vencimento.
 * - O inicio da contagem ocorre no primeiro dia util seguinte a data de publicacao/notificacao.
 * - Na contagem em dias uteis (CPC), contam-se apenas dias uteis forenses (suspendendo de 20/12 a 20/01).
 * - Na contagem em dias corridos (CTB Defesa Previa, JARI, CETRAN - minimo de 30 dias),
 *   inicia-se no primeiro dia util seguinte e, se o vencimento cair em fim de semana ou feriado,
 *   prorroga-se para o primeiro dia util subsequente.
 */
export function calcularPrazo(opcoes: OpcoesCalculoPrazo): ResultadoCalculoPrazo {
  const padrao = parametrosPadraoRegra(opcoes.regra);
  const diasPrazo = opcoes.diasPrazo ?? padrao.diasPrazo;
  if (!Number.isInteger(diasPrazo) || diasPrazo <= 0) {
    throw new Error("A quantidade de dias do prazo deve ser um inteiro positivo.");
  }

  const contagem = opcoes.contagem ?? padrao.contagem;
  const consideraRecessoCPC = padrao.consideraRecessoCPC;
  const feriadosLocais = opcoes.feriadosLocais ?? [];
  const dataBase = parseISODate(opcoes.dataPublicacaoOuNotificacao);

  // Encontra o primeiro dia util seguinte ao dia da publicacao/notificacao (dia 1 da contagem)
  let cursor = addDaysUTC(dataBase, 1);
  while (!isDiaUtilForense(cursor, opcoes.uf, opcoes.municipio, feriadosLocais, consideraRecessoCPC)) {
    cursor = addDaysUTC(cursor, 1);
  }
  const dataInicioContagem = formatISODate(cursor);

  if (contagem === "uteis") {
    let restantes = diasPrazo - 1;
    while (restantes > 0) {
      cursor = addDaysUTC(cursor, 1);
      if (isDiaUtilForense(cursor, opcoes.uf, opcoes.municipio, feriadosLocais, consideraRecessoCPC)) {
        restantes -= 1;
      }
    }
  } else {
    // Contagem em dias corridos (ex.: CTB 30 dias a partir do inicio da contagem), prorrogando o termo final se nao for util
    cursor = addDaysUTC(cursor, diasPrazo - 1);
    while (!isDiaUtilForense(cursor, opcoes.uf, opcoes.municipio, feriadosLocais, consideraRecessoCPC)) {
      cursor = addDaysUTC(cursor, 1);
    }
  }

  return {
    regra: opcoes.regra,
    diasPrazo,
    contagem,
    consideraRecessoCPC,
    dataPublicacaoOuNotificacao: formatISODate(dataBase),
    dataInicioContagem,
    dataVencimento: formatISODate(cursor),
  };
}

export type StatusAlertaPrazo = "concluido" | "vencido" | "hoje" | "urgente" | "no_prazo";

export function classificarStatusPrazo(prazo: Pick<Prazo, "dataVencimento" | "concluido">, hojeISO: string): {
  status: StatusAlertaPrazo;
  diasRestantes: number;
} {
  const hoje = parseISODate(hojeISO);
  const venc = parseISODate(prazo.dataVencimento);
  const diffMs = venc.getTime() - hoje.getTime();
  const diasRestantes = Math.round(diffMs / (1000 * 60 * 60 * 24));

  if (prazo.concluido) {
    return { status: "concluido", diasRestantes };
  }
  if (diasRestantes < 0) {
    return { status: "vencido", diasRestantes };
  }
  if (diasRestantes === 0) {
    return { status: "hoje", diasRestantes: 0 };
  }
  if (diasRestantes <= 3) {
    return { status: "urgente", diasRestantes };
  }
  return { status: "no_prazo", diasRestantes };
}
