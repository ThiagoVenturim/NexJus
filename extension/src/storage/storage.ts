import type { NexJusDatabase } from "../types/models";
import { decryptText, type EncryptedPayload, encryptText } from "./crypto";

export const STORAGE_KEY = "nexjus_db_v1";

export type EnvelopeArmazenado =
  | { encrypted: false; database: NexJusDatabase }
  | { encrypted: true; payload: EncryptedPayload };

export function criarDatabaseVazio(): NexJusDatabase {
  return {
    clientes: [],
    veiculos: [],
    processos: [],
    prazos: [],
    feriadosLocais: [],
  };
}

const memoryFallback = new Map<string, unknown>();

async function lerStorageBruto(key: string): Promise<unknown> {
  if (typeof chrome !== "undefined" && chrome.storage?.local) {
    const result = await chrome.storage.local.get(key);
    return result[key];
  }
  return memoryFallback.get(key);
}

async function gravarStorageBruto(key: string, value: unknown): Promise<void> {
  if (typeof chrome !== "undefined" && chrome.storage?.local) {
    await chrome.storage.local.set({ [key]: value });
    return;
  }
  memoryFallback.set(key, value);
}

export function limparStorageFallbackMemoria(): void {
  memoryFallback.clear();
}

export async function verificarEstadoCriptografia(): Promise<boolean> {
  const raw = (await lerStorageBruto(STORAGE_KEY)) as EnvelopeArmazenado | undefined;
  return Boolean(raw && raw.encrypted);
}

export async function carregarDatabase(passphrase?: string): Promise<NexJusDatabase> {
  const raw = (await lerStorageBruto(STORAGE_KEY)) as EnvelopeArmazenado | undefined;
  if (!raw) {
    return criarDatabaseVazio();
  }
  if (raw.encrypted) {
    if (!passphrase) {
      throw new Error("Os dados locais estao criptografados. Informe a senha para desbloquear.");
    }
    const json = await decryptText(raw.payload, passphrase);
    const parsed = JSON.parse(json) as Partial<NexJusDatabase>;
    return {
      clientes: parsed.clientes ?? [],
      veiculos: parsed.veiculos ?? [],
      processos: parsed.processos ?? [],
      prazos: parsed.prazos ?? [],
      feriadosLocais: parsed.feriadosLocais ?? [],
      datajudApiKey: parsed.datajudApiKey,
    };
  }
  return {
    clientes: raw.database.clientes ?? [],
    veiculos: raw.database.veiculos ?? [],
    processos: raw.database.processos ?? [],
    prazos: raw.database.prazos ?? [],
    feriadosLocais: raw.database.feriadosLocais ?? [],
    datajudApiKey: raw.database.datajudApiKey,
  };
}

export async function salvarDatabase(
  database: NexJusDatabase,
  opcoes?: { criptografarComSenha?: string }
): Promise<void> {
  const senha = opcoes?.criptografarComSenha?.trim();
  if (senha) {
    const payload = await encryptText(JSON.stringify(database), senha);
    const envelope: EnvelopeArmazenado = { encrypted: true, payload };
    await gravarStorageBruto(STORAGE_KEY, envelope);
    return;
  }
  const envelope: EnvelopeArmazenado = { encrypted: false, database };
  await gravarStorageBruto(STORAGE_KEY, envelope);
}
