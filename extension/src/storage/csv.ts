import type { Cliente, Prazo, Processo, Veiculo } from "../types/models";

const FORMULA_PREFIXES = ["=", "+", "-", "@", "\t", "\r"];

function sanitizeCellForExport(value: string | number | boolean | undefined): string {
  const str = String(value ?? "");
  const safe = FORMULA_PREFIXES.some((prefix) => str.startsWith(prefix)) ? `'${str}` : str;
  if (safe.includes(",") || safe.includes('"') || safe.includes("\n") || safe.includes("\r")) {
    return `"${safe.replace(/"/g, '""')}"`;
  }
  return safe;
}

export function serializarCSV<T extends object>(
  itens: T[],
  colunas: (keyof T & string)[]
): string {
  const header = colunas.join(",");
  const rows = itens.map((item) =>
    colunas
      .map((col) => sanitizeCellForExport(item[col] as string | number | boolean | undefined))
      .join(",")
  );
  return [header, ...rows].join("\n");
}

export function parseLinhasCSV(csvText: string): string[][] {
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentField = "";
  let inQuotes = false;

  const text = csvText.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          currentField += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        currentField += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      currentRow.push(currentField);
      currentField = "";
    } else if (ch === "\n") {
      currentRow.push(currentField);
      if (currentRow.some((cell) => cell.trim() !== "")) {
        rows.push(currentRow);
      }
      currentRow = [];
      currentField = "";
    } else {
      currentField += ch;
    }
  }

  if (currentField !== "" || currentRow.length > 0) {
    currentRow.push(currentField);
    if (currentRow.some((cell) => cell.trim() !== "")) {
      rows.push(currentRow);
    }
  }

  return rows;
}

export function parseObjetosCSV(csvText: string): Record<string, string>[] {
  const rows = parseLinhasCSV(csvText);
  if (rows.length < 2) {
    return [];
  }
  const headers = rows[0].map((h) => h.trim());
  const objetos: Record<string, string>[] = [];
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    const obj: Record<string, string> = {};
    headers.forEach((h, idx) => {
      const val = (row[idx] ?? "").trim();
      obj[h] = val.startsWith("'") && FORMULA_PREFIXES.some((p) => val.slice(1).startsWith(p))
        ? val.slice(1)
        : val;
    });
    objetos.push(obj);
  }
  return objetos;
}

export const COLUNAS_CLIENTES: (keyof Cliente)[] = [
  "id",
  "nome",
  "documento",
  "telefone",
  "email",
  "uf",
  "municipio",
  "criadoEm",
];

export const COLUNAS_VEICULOS: (keyof Veiculo)[] = [
  "id",
  "clienteId",
  "placa",
  "renavam",
  "uf",
  "marcaModelo",
  "criadoEm",
];

export const COLUNAS_PROCESSOS: (keyof Processo)[] = [
  "id",
  "clienteId",
  "veiculoId",
  "numero",
  "tipo",
  "orgaoOuTribunal",
  "fase",
  "uf",
  "municipio",
  "ultimoAndamento",
  "dataUltimaMovimentacao",
  "criadoEm",
];

export const COLUNAS_PRAZOS: (keyof Prazo)[] = [
  "id",
  "processoId",
  "titulo",
  "regra",
  "dataPublicacaoOuNotificacao",
  "diasPrazo",
  "contagem",
  "uf",
  "municipio",
  "dataInicioContagem",
  "dataVencimento",
  "concluido",
  "criadoEm",
];

export function exportarClientesCSV(clientes: Cliente[]): string {
  return serializarCSV(clientes, COLUNAS_CLIENTES);
}

export function importarClientesCSV(csvText: string): Cliente[] {
  return parseObjetosCSV(csvText).map((r, idx) => ({
    id: r.id || `cli-${Date.now()}-${idx}`,
    nome: r.nome || "",
    documento: r.documento || "",
    telefone: r.telefone || "",
    email: r.email || "",
    uf: (r.uf as Cliente["uf"]) || "SP",
    municipio: r.municipio || "",
    criadoEm: r.criadoEm || new Date().toISOString(),
  }));
}

export function exportarVeiculosCSV(veiculos: Veiculo[]): string {
  return serializarCSV(veiculos, COLUNAS_VEICULOS);
}

export function importarVeiculosCSV(csvText: string): Veiculo[] {
  return parseObjetosCSV(csvText).map((r, idx) => ({
    id: r.id || `vei-${Date.now()}-${idx}`,
    clienteId: r.clienteId || "",
    placa: (r.placa || "").toUpperCase(),
    renavam: r.renavam || "",
    uf: (r.uf as Veiculo["uf"]) || "SP",
    marcaModelo: r.marcaModelo || "",
    criadoEm: r.criadoEm || new Date().toISOString(),
  }));
}

export function exportarProcessosCSV(processos: Processo[]): string {
  return serializarCSV(processos, COLUNAS_PROCESSOS);
}

export function importarProcessosCSV(csvText: string): Processo[] {
  return parseObjetosCSV(csvText).map((r, idx) => ({
    id: r.id || `proc-${Date.now()}-${idx}`,
    clienteId: r.clienteId || "",
    veiculoId: r.veiculoId || undefined,
    numero: r.numero || "",
    tipo: r.tipo === "transito" ? "transito" : "judicial",
    orgaoOuTribunal: r.orgaoOuTribunal || "",
    fase: (r.fase as Processo["fase"]) || "conhecimento",
    uf: (r.uf as Processo["uf"]) || "SP",
    municipio: r.municipio || "",
    ultimoAndamento: r.ultimoAndamento || "",
    dataUltimaMovimentacao: r.dataUltimaMovimentacao || "",
    criadoEm: r.criadoEm || new Date().toISOString(),
  }));
}

export function exportarPrazosCSV(prazos: Prazo[]): string {
  return serializarCSV(prazos, COLUNAS_PRAZOS);
}

export function importarPrazosCSV(csvText: string): Prazo[] {
  return parseObjetosCSV(csvText).map((r, idx) => ({
    id: r.id || `prz-${Date.now()}-${idx}`,
    processoId: r.processoId || "",
    titulo: r.titulo || "",
    regra: (r.regra as Prazo["regra"]) || "cpc_15",
    dataPublicacaoOuNotificacao: r.dataPublicacaoOuNotificacao || "",
    diasPrazo: Number(r.diasPrazo) || 15,
    contagem: r.contagem === "corridos" ? "corridos" : "uteis",
    uf: (r.uf as Prazo["uf"]) || "SP",
    municipio: r.municipio || undefined,
    dataInicioContagem: r.dataInicioContagem || "",
    dataVencimento: r.dataVencimento || "",
    concluido: r.concluido === "true" || r.concluido === "1",
    criadoEm: r.criadoEm || new Date().toISOString(),
  }));
}
