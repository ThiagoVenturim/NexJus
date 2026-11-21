import { lerPaginaAberta } from "./pageReader";

if (typeof chrome !== "undefined" && chrome.runtime?.onMessage) {
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message && message.type === "NEXJUS_READ_CURRENT_PAGE") {
      const resultado = lerPaginaAberta(document, window.location.href);
      sendResponse(resultado);
      return true;
    }
    return false;
  });
}
