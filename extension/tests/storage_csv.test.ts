import { beforeEach, describe, expect, it } from "vitest";
import {
  exportarClientesCSV,
  exportarPrazosCSV,
  exportarProcessosCSV,
  exportarVeiculosCSV,
  importarClientesCSV,
  importarPrazosCSV,
  importarProcessosCSV,
  importarVeiculosCSV,
} from "../src/storage/csv";
import {
  carregarDatabase,
  criarDatabaseVazio,
  limparStorageFallbackMemoria,
  salvarDatabase,
  verificarEstadoCriptografia,
} from "../src/storage/storage";

describe("Storage local com criptografia opcional e importacao/exportacao CSV", () => {
  beforeEach(() => {
    limparStorageFallbackMemoria();
  });

  it("salva e carrega o banco sem criptografia por padrao", async () => {
    const db = criarDatabaseVazio();
    db.clientes.push({
      id: "cli-1",
      nome: "Maria Oliveira",
      documento: "000.000.000-00",
      telefone: "11999990000",
      email: "maria@example.com",
      uf: "SP",
      municipio: "Sao Paulo",
      criadoEm: "2026-03-01T00:00:00.000Z",
    });

    await salvarDatabase(db);
    expect(await verificarEstadoCriptografia()).toBe(false);

    const carregado = await carregarDatabase();
    expect(carregado.clientes).toHaveLength(1);
    expect(carregado.clientes[0].nome).toBe("Maria Oliveira");
  });

  it("criptografa com AES-GCM (PBKDF2) quando senha e informada e rejeita senha incorreta", async () => {
    const db = criarDatabaseVazio();
    db.veiculos.push({
      id: "vei-1",
      clienteId: "cli-1",
      placa: "BRA2E19",
      renavam: "12345678901",
      uf: "SP",
      marcaModelo: "Sedan",
      criadoEm: "2026-03-01T00:00:00.000Z",
    });

    await salvarDatabase(db, { criptografarComSenha: "senha-forte-advogado" });
    expect(await verificarEstadoCriptografia()).toBe(true);

    await expect(carregarDatabase()).rejects.toThrow(/criptografados/i);
    await expect(carregarDatabase("senha-errada")).rejects.toThrow(/Falha ao descriptografar/i);

    const desbloqueado = await carregarDatabase("senha-forte-advogado");
    expect(desbloqueado.veiculos).toHaveLength(1);
    expect(desbloqueado.veiculos[0].placa).toBe("BRA2E19");
  });

  it("exporta e importa CSV de clientes, veiculos, processos e prazos prevenindo formula injection", () => {
    const clientesCsv = exportarClientesCSV([
      {
        id: "c1",
        nome: "Escritorio, Associados",
        documento: "=1+1",
        telefone: "1133334444",
        email: "contato@example.com",
        uf: "SP",
        municipio: "Sao Paulo",
        criadoEm: "2026-03-01",
      },
    ]);
    expect(clientesCsv).toContain("'=1+1");
    const clientesImportados = importarClientesCSV(clientesCsv);
    expect(clientesImportados).toHaveLength(1);
    expect(clientesImportados[0].nome).toBe("Escritorio, Associados");
    expect(clientesImportados[0].documento).toBe("=1+1");

    const veiculosCsv = exportarVeiculosCSV([
      {
        id: "v1",
        clienteId: "c1",
        placa: "ABC1D23",
        renavam: "98765432100",
        uf: "RJ",
        marcaModelo: "Compacto",
        criadoEm: "2026-03-01",
      },
    ]);
    expect(importarVeiculosCSV(veiculosCsv)[0].placa).toBe("ABC1D23");

    const processosCsv = exportarProcessosCSV([
      {
        id: "p1",
        clienteId: "c1",
        veiculoId: "v1",
        numero: "0000001-25.2026.8.26.0100",
        tipo: "judicial",
        orgaoOuTribunal: "TJSP",
        fase: "conhecimento",
        uf: "SP",
        municipio: "Sao Paulo",
        ultimoAndamento: "Distribuido",
        dataUltimaMovimentacao: "2026-03-01",
        criadoEm: "2026-03-01",
      },
    ]);
    expect(importarProcessosCSV(processosCsv)[0].numero).toBe("0000001-25.2026.8.26.0100");

    const prazosCsv = exportarPrazosCSV([
      {
        id: "pr1",
        processoId: "p1",
        titulo: "Contestacao",
        regra: "cpc_15",
        dataPublicacaoOuNotificacao: "2026-03-06",
        diasPrazo: 15,
        contagem: "uteis",
        uf: "SP",
        dataInicioContagem: "2026-03-09",
        dataVencimento: "2026-03-27",
        concluido: true,
        criadoEm: "2026-03-06",
      },
    ]);
    const prazosImportados = importarPrazosCSV(prazosCsv);
    expect(prazosImportados[0].concluido).toBe(true);
    expect(prazosImportados[0].diasPrazo).toBe(15);
  });
});
