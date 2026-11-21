import { carregarDatabase, verificarEstadoCriptografia } from "../storage/storage";
import {
  ALARM_CHECK_PRAZOS,
  atualizarBadgeExtensao,
  registrarAlarmeVerificacaoPrazos,
} from "./alarms";

async function sincronizarAlertasEmBackground(): Promise<void> {
  try {
    const criptografado = await verificarEstadoCriptografia();
    if (criptografado) {
      return;
    }
    const db = await carregarDatabase();
    atualizarBadgeExtensao(db.prazos);
  } catch {
    // Ignora falhas silenciosamente no service worker
  }
}

if (typeof chrome !== "undefined") {
  chrome.runtime?.onInstalled?.addListener(() => {
    registrarAlarmeVerificacaoPrazos(60);
    void sincronizarAlertasEmBackground();
  });

  chrome.alarms?.onAlarm?.addListener((alarm) => {
    if (alarm.name === ALARM_CHECK_PRAZOS) {
      void sincronizarAlertasEmBackground();
    }
  });
}
