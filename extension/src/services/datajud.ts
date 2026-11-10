import type { DataJudMovimento, DataJudProcesso } from "../types/models";

const DATAJUD_BASE_URL = "https://api-publica.datajud.cnj.jus.br";

/**
 * Mapa de segmento J.TR do numero unico CNJ para o alias de endpoint da API Publica do DataJud.
 */
const MAPA_ENDPOINTS_DATAJUD: Record<string, string> = {
  // Justica Federal (J=4)
  "4.01": "api_publica_trf1",
  "4.02": "api_publica_trf2",
  "4.03": "api_publica_trf3",
  "4.04": "api_publica_trf4",
  "4.05": "api_publica_trf5",
  "4.06": "api_publica_trf6",
  // Justica do Trabalho (J=5) - principais
  "5.01": "api_publica_trt1",
  "5.02": "api_publica_trt2",
  "5.03": "api_publica_trt3",
  "5.04": "api_publica_trt4",
  "5.15": "api_publica_trt15",
  // Justica Estadual (J=8)
  "8.01": "api_publica_tjac",
  "8.02": "api_publica_tjal",
  "8.03": "api_publica_tjap",
  "8.04": "api_publica_tjam",
  "8.05": "api_publica_tjba",
  "8.06": "api_publica_tjce",
  "8.07": "api_publica_tjdft",
  "8.08": "api_publica_tjes",
  "8.09": "api_publica_tjgo",
  "8.10": "api_publica_tjma",
  "8.11": "api_publica_tjmt",
  "8.12": "api_publica_tjms",
  "8.13": "api_publica_tjmg",
  "8.14": "api_publica_tjpa",
  "8.15": "api_publica_tjpb",
  "8.16": "api_publica_tjpr",
  "8.17": "api_publica_tjpe",
  "8.18": "api_publica_tjpi",
  "8.19": "api_publica_tjrj",
  "8.20": "api_publica_tjrn",
  "8.21": "api_publica_tjrs",
  "8.22": "api_publica_tjro",
  "8.23": "api_publica_tjrr",
  "8.24": "api_publica_tjsc",
  "8.25": "api_publica_tjse",
  "8.26": "api_publica_tjsp",
  "8.27": "api_publica_tjto",
};

export function limparDigitosCNJ(numero: string): string {
  return numero.replace(/\D/g, "");
}

export function calcularDigitoVerificadorCNJ(
  nnnnnnn: string,
  aaaa: string,
  jtr: string,
  oooo: string
): string {
  const base = BigInt(`${nnnnnnn}${aaaa}${jtr}${oooo}00`);
  const dv = 98n - (base % 97n);
  return dv.toString().padStart(2, "0");
}

/**
 * Valida a numeracao unica de 20 digitos do CNJ (Resolucao CNJ 65/2008), incluindo digito verificador mod 97.
 */
export function validarNumeroCNJ(numero: string): boolean {
  const digitos = limparDigitosCNJ(numero);
  if (digitos.length !== 20) {
    return false;
  }
  const nnnnnnn = digitos.slice(0, 7);
  const dd = digitos.slice(7, 9);
  const aaaa = digitos.slice(9, 13);
  const jtr = digitos.slice(13, 16);
  const oooo = digitos.slice(16, 20);

  const inteiro = BigInt(`${nnnnnnn}${aaaa}${jtr}${oooo}${dd}`);
  return inteiro % 97n === 1n;
}

export function resolverEndpointDataJudPorNumeroCNJ(numero: string): string {
  const digitos = limparDigitosCNJ(numero);
  if (digitos.length !== 20) {
    throw new Error("Numero de processo CNJ deve conter 20 digitos.");
  }
  const j = digitos.slice(13, 14);
  const tr = digitos.slice(14, 16);
  const chave = `${j}.${tr}`;
  const alias = MAPA_ENDPOINTS_DATAJUD[chave];
  if (!alias) {
    throw new Error(`Tribunal nao mapeado para o segmento CNJ ${chave}.`);
  }
  return `${DATAJUD_BASE_URL}/${alias}/_search`;
}

export interface DataJudHitSource {
  numeroProcesso?: string;
  tribunal?: string;
  dataAjuizamento?: string;
  dataHoraUltimaAtualizacao?: string;
  classe?: { codigo?: number; nome?: string };
  orgaoJulgador?: { codigo?: number; nome?: string };
  movimentos?: Array<{ codigo?: number; nome?: string; dataHora?: string }>;
}

export function normalizarRespostaDataJud(payload: unknown): DataJudProcesso | null {
  const root = payload as {
    hits?: { hits?: Array<{ _source?: DataJudHitSource }> };
  } | null;
  const source = root?.hits?.hits?.[0]?._source;
  if (!source || !source.numeroProcesso) {
    return null;
  }

  const movimentos: DataJudMovimento[] = (source.movimentos ?? [])
    .map((m) => ({
      codigo: m.codigo ?? 0,
      nome: m.nome ?? "Movimentacao",
      dataHora: m.dataHora ?? "",
    }))
    .sort((a, b) => b.dataHora.localeCompare(a.dataHora));

  return {
    numeroProcesso: source.numeroProcesso,
    tribunal: source.tribunal ?? "",
    classeNome: source.classe?.nome ?? "",
    orgaoJulgadorNome: source.orgaoJulgador?.nome ?? "",
    dataAjuizamento: source.dataAjuizamento ?? "",
    dataHoraUltimaAtualizacao: source.dataHoraUltimaAtualizacao ?? "",
    movimentos,
  };
}

const cacheConsultas = new Map<string, DataJudProcesso>();

export function limparCacheDataJud(): void {
  cacheConsultas.clear();
}

export async function consultarProcessoDataJud(
  numeroCNJ: string,
  apiKey: string,
  fetchImpl: typeof fetch = fetch
): Promise<DataJudProcesso | null> {
  const digitos = limparDigitosCNJ(numeroCNJ);
  if (digitos.length !== 20) {
    throw new Error("Numero de processo CNJ deve conter 20 digitos.");
  }
  if (!apiKey || !apiKey.trim()) {
    throw new Error("Chave da API publica DataJud nao informada.");
  }

  const cached = cacheConsultas.get(digitos);
  if (cached) {
    return cached;
  }

  const endpoint = resolverEndpointDataJudPorNumeroCNJ(digitos);
  const response = await fetchImpl(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `ApiKey ${apiKey.trim()}`,
    },
    body: JSON.stringify({
      size: 1,
      query: {
        match: {
          numeroProcesso: digitos,
        },
      },
    }),
  });

  if (!response.ok) {
    throw new Error(`Erro ao consultar DataJud (HTTP ${response.status}).`);
  }

  const json = (await response.json()) as unknown;
  const normalizado = normalizarRespostaDataJud(json);
  if (normalizado) {
    cacheConsultas.set(digitos, normalizado);
  }
  return normalizado;
}
