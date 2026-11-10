import { describe, expect, it, vi } from "vitest";
import {
   ALARM_CHECK_PRAZOS,
  atualizarBadgeExtensao,
  registrarAlarmeVerificacaoPrazos,
  resumirAlertasPrazos,
} from "../src/background/alarms";
import {
  calcularPascoaUTC,
  calcularPrazo,
  classificarStatusPrazo,
  formatISODate,
  isFeriado,
  isRecessoForenseCPC,
  parseISODate,
} from "../src/domain/prazos";
import type { Prazo } from "../src/types/models";

describe("Motor de prazos CPC e CTB", () => {
  it("calcula corretamente o Domingo de Pascoa e feriados moveis (Carnaval, Sexta Santa, Corpus Christi)", () => {
    expect(formatISODate(calcularPascoaUTC(2026))).toBe("2026-04-05");
    // Em 2026: Carnaval 16 e 17/02, Sexta Santa 03/04, Corpus Christi 04/06
    expect(isFeriado(parseISODate("2026-02-16"), "SP")).toBe(true);
    expect(isFeriado(parseISODate("2026-02-17"), "SP")).toBe(true);
    expect(isFeriado(parseISODate("2026-04-03"), "SP")).toBe(true);
    expect(isFeriado(parseISODate("2026-06-04"), "SP")).toBe(true);
  });

  it("respeita feriados estaduais por UF e feriados municipais customizados", () => {
    // 09/07 e feriado em SP, mas nao no RJ
    expect(isFeriado(parseISODate("2026-07-09"), "SP")).toBe(true);
    expect(isFeriado(parseISODate("2026-07-09"), "RJ")).toBe(false);
    // 23/04 (Sao Jorge) e feriado no RJ
    expect(isFeriado(parseISODate("2026-04-23"), "RJ")).toBe(true);

    // Feriado municipal de Sao Paulo (25/01 - Aniversario da Cidade)
    const locais = [{ data: "01-25", nome: "Aniversario de Sao Paulo", uf: "SP" as const, municipio: "Sao Paulo" }];
    expect(isFeriado(parseISODate("2026-01-25"), "SP", "Sao Paulo", locais)).toBe(true);
    expect(isFeriado(parseISODate("2026-01-25"), "SP", "Campinas", locais)).toBe(false);
  });

  it("calcula prazo CPC de 5 e 15 dias uteis pulando fins de semana e feriados", () => {
    // Publicacao na sexta-feira 2026-03-06 -> inicio na segunda 2026-03-09 -> 5 dias uteis = sexta 2026-03-13
    const res5 = calcularPrazo({
      regra: "cpc_5",
      dataPublicacaoOuNotificacao: "2026-03-06",
      uf: "SP",
    });
    expect(res5.dataInicioContagem).toBe("2026-03-09");
    expect(res5.dataVencimento).toBe("2026-03-13");

    // 15 dias uteis a partir de publicacao em 2026-03-06 (sem feriados em marco/2026) -> 2026-03-27
    const res15 = calcularPrazo({
      regra: "cpc_15",
      dataPublicacaoOuNotificacao: "2026-03-06",
      uf: "SP",
    });
    expect(res15.dataInicioContagem).toBe("2026-03-09");
    expect(res15.dataVencimento).toBe("2026-03-27");
  });

  it("suspende prazos do CPC durante o recesso forense de 20/12 a 20/01 (art. 220 CPC)", () => {
    expect(isRecessoForenseCPC(parseISODate("2026-12-19"))).toBe(false);
    expect(isRecessoForenseCPC(parseISODate("2026-12-20"))).toBe(true);
    expect(isRecessoForenseCPC(parseISODate("2027-01-20"))).toBe(true);
    expect(isRecessoForenseCPC(parseISODate("2027-01-21"))).toBe(false);

    // Publicacao em 18/12/2026 (sexta-feira):
    // 19/12 e sabado, 20/12 a 20/01/2027 e recesso forense.
    // O dia 1 da contagem deve ser quinta-feira 21/01/2027.
    // Para 5 dias uteis: 21/01 (1), 22/01 (2), 25/01 (3), 26/01 (4), 27/01 (5).
    const resRecesso = calcularPrazo({
      regra: "cpc_5",
      dataPublicacaoOuNotificacao: "2026-12-18",
      uf: "SP",
    });
    expect(resRecesso.dataInicioContagem).toBe("2027-01-21");
    expect(resRecesso.dataVencimento).toBe("2027-01-27");
  });

  it("calcula prazos do CTB (Defesa Previa, JARI e CETRAN) de 30 dias corridos com prorrogacao para dia util", () => {
    // Notificacao em 2026-03-02 (segunda) -> inicio em 2026-03-03 (terca)
    // 30 dias corridos: 03/03 + 29 dias = 01/04/2026 (quarta-feira, dia util)
    const defesa = calcularPrazo({
      regra: "ctb_defesa_previa",
      dataPublicacaoOuNotificacao: "2026-03-02",
      uf: "SP",
    });
    expect(defesa.contagem).toBe("corridos");
    expect(defesa.diasPrazo).toBe(30);
    expect(defesa.dataInicioContagem).toBe("2026-03-03");
    expect(defesa.dataVencimento).toBe("2026-04-01");

    // Se o 30o dia cair no fim de semana ou Sexta-feira Santa (03/04/2026), prorroga para segunda 06/04/2026
    const jari = calcularPrazo({
      regra: "ctb_jari",
      dataPublicacaoOuNotificacao: "2026-03-04",
      uf: "SP",
    });
    expect(jari.dataInicioContagem).toBe("2026-03-05");
    // 05/03 + 29 dias = 03/04/2026 (Sexta-feira da Paixao) -> prorroga para segunda 06/04/2026
    expect(jari.dataVencimento).toBe("2026-04-06");
  });

  it("classifica status de alertas e integra com chrome.alarms e badge", () => {
    const basePrazo: Omit<Prazo, "id" | "dataVencimento" | "concluido"> = {
      processoId: "p1",
      titulo: "Contestacao",
      regra: "cpc_15",
      dataPublicacaoOuNotificacao: "2026-03-01",
      diasPrazo: 15,
      contagem: "uteis",
      uf: "SP",
      dataInicioContagem: "2026-03-02",
      criadoEm: "2026-03-01",
    };

    const prazos: Prazo[] = [
      { ...basePrazo, id: "1", dataVencimento: "2026-03-10", concluido: false },
      { ...basePrazo, id: "2", dataVencimento: "2026-03-12", concluido: false },
      { ...basePrazo, id: "3", dataVencimento: "2026-03-14", concluido: false },
      { ...basePrazo, id: "4", dataVencimento: "2026-03-25", concluido: false },
      { ...basePrazo, id: "5", dataVencimento: "2026-03-10", concluido: true },
    ];

    expect(classificarStatusPrazo(prazos[0], "2026-03-12").status).toBe("vencido");
    expect(classificarStatusPrazo(prazos[1], "2026-03-12").status).toBe("hoje");
    expect(classificarStatusPrazo(prazos[2], "2026-03-12").status).toBe("urgente");
    expect(classificarStatusPrazo(prazos[3], "2026-03-12").status).toBe("no_prazo");
    expect(classificarStatusPrazo(prazos[4], "2026-03-12").status).toBe("concluido");

    const createAlarmSpy = vi.fn();
    const setBadgeTextSpy = vi.fn();
    const setBadgeBgSpy = vi.fn();
    vi.stubGlobal("chrome", {
      alarms: { create: createAlarmSpy },
      action: { setBadgeText: setBadgeTextSpy, setBadgeBackgroundColor: setBadgeBgSpy },
    });

    registrarAlarmeVerificacaoPrazos(30);
    expect(createAlarmSpy).toHaveBeenCalledWith(ALARM_CHECK_PRAZOS, {
      delayInMinutes: 1,
      periodInMinutes: 30,
    });

    const resumo = atualizarBadgeExtensao(prazos, "2026-03-12");
    expect(resumo.totalCriticos).toBe(3);
    expect(resumirAlertasPrazos(prazos, "2026-03-12").vencidos).toHaveLength(1);
    expect(setBadgeTextSpy).toHaveBeenCalledWith({ text: "3" });
    vi.unstubAllGlobals();
  });
});
