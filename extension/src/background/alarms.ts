import { classificarStatusPrazo, formatISODate } from "../domain/prazos";
import type { Prazo } from "../types/models";

export const ALARM_CHECK_PRAZOS = "nexjus-check-prazos";

export interface ResumoAlertasPrazos {
  vencidos: Prazo[];
  vencendoHoje: Prazo[];
  urgentes: Prazo[];
  totalCriticos: number;
}

export function resumirAlertasPrazos(prazos: Prazo[], hojeISO: string): ResumoAlertasPrazos {
  const vencidos: Prazo[] = [];
  const vencendoHoje: Prazo[] = [];
  const urgentes: Prazo[] = [];

  for (const prazo of prazos) {
    const { status } = classificarStatusPrazo(prazo, hojeISO);
    if (status === "vencido") {
      vencidos.push(prazo);
    } else if (status === "hoje") {
      vencendoHoje.push(prazo);
    } else if (status === "urgente") {
      urgentes.push(prazo);
    }
  }

  return {
    vencidos,
    vencendoHoje,
    urgentes,
    totalCriticos: vencidos.length + vencendoHoje.length + urgentes.length,
  };
}

export function registrarAlarmeVerificacaoPrazos(periodInMinutes = 60): void {
  if (typeof chrome !== "undefined" && chrome.alarms?.create) {
    chrome.alarms.create(ALARM_CHECK_PRAZOS, {
      delayInMinutes: 1,
      periodInMinutes,
    });
  }
}

export function atualizarBadgeExtensao(prazos: Prazo[], hojeISO = formatISODate(new Date())): ResumoAlertasPrazos {
  const resumo = resumirAlertasPrazos(prazos, hojeISO);
  if (typeof chrome !== "undefined" && chrome.action?.setBadgeText) {
    const text = resumo.totalCriticos > 0 ? String(resumo.totalCriticos) : "";
    void chrome.action.setBadgeText({ text });
    if (chrome.action.setBadgeBackgroundColor) {
      const color = resumo.vencidos.length > 0 || resumo.vencendoHoje.length > 0 ? "#B91C1C" : "#D97706";
      void chrome.action.setBadgeBackgroundColor({ color });
    }
  }
  return resumo;
}
