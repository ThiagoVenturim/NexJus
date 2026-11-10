import { beforeEach, describe, expect, it, vi } from "vitest";
import { detectarCaptchaNaPagina, lerPaginaAberta } from "../src/content/pageReader";
import {
  calcularDigitoVerificadorCNJ,
  consultarProcessoDataJud,
  limparCacheDataJud,
  resolverEndpointDataJudPorNumeroCNJ,
  validarNumeroCNJ,
} from "../src/services/datajud";

describe("Leitura de paginas abertas pelo usuario (sem burlar captcha) e consulta DataJud", () => {
  beforeEach(() => {
    limparCacheDataJud();
  });

  it("interrompe imediatamente a leitura quando detecta CAPTCHA na pagina aberta", () => {
    const parser = new DOMParser();
    const docComRecaptcha = parser.parseFromString(
      `<html><body>
        <div id="numeroProcesso">1000001-55.2026.8.26.0100</div>
        <div class="g-recaptcha" data-sitekey="abc"></div>
      </body></html>`,
      "text/html"
    );

    expect(detectarCaptchaNaPagina(docComRecaptcha)).toBe(true);
    const res = lerPaginaAberta(docComRecaptcha, "https://esaj.tjsp.jus.br/cpopg/show.do");
    expect(res.status).toBe("captcha_blocked");
    expect(res.dados).toBeUndefined();
    expect(res.mensagem).toMatch(/nunca contorna captcha/i);
  });

  it("extrai dados de processo judicial em paginas PJe, eSAJ e Projudi sem captcha", () => {
    const parser = new DOMParser();
    const docEsaj = parser.parseFromString(
      `<html><body>
        <span id="numeroProcesso">0000001-25.2026.8.26.0100</span>
        <span id="classeProcesso">Procedimento Comum Civel</span>
        <span id="varaProcesso">1a Vara Civel</span>
        <table id="tabelaUltimasMovimentacoes">
          <tr>
            <td class="dataMovimentacao">09/11/2026</td>
            <td class="descricaoMovimentacao">Juntada de Peticao</td>
          </tr>
        </table>
      </body></html>`,
      "text/html"
    );

    const res = lerPaginaAberta(docEsaj, "https://esaj.tjsp.jus.br/cpopg/show.do");
    expect(res.status).toBe("ok");
    expect(res.portal).toBe("esaj");
    expect(res.dados?.numeroProcesso).toBe("0000001-25.2026.8.26.0100");
    expect(res.dados?.classeOuInfracao).toBe("Procedimento Comum Civel");
    expect(res.dados?.ultimoAndamento).toBe("Juntada de Peticao");
  });

  it("extrai dados de infracao em paginas Senatran/RENAINF e Detran abertas pelo usuario", () => {
    const parser = new DOMParser();
    const docSenatran = parser.parseFromString(
      `<html><body>
        <h1>Portal de Servicos Senatran - RENAINF</h1>
        <div id="placaVeiculo">BRA2E19</div>
        <div id="renavamVeiculo">12345678901</div>
        <div id="numeroAutoInfracao">E012345678</div>
        <div id="orgaoAutuador">DER-SP</div>
        <div id="situacaoInfracao">Notificacao de Autuacao Emitida</div>
      </body></html>`,
      "text/html"
    );

    const res = lerPaginaAberta(
      docSenatran,
      "https://portalservicos.senatran.serpro.gov.br/#/infracoes"
    );
    expect(res.status).toBe("ok");
    expect(res.portal).toBe("senatran");
    expect(res.dados?.placa).toBe("BRA2E19");
    expect(res.dados?.renavam).toBe("12345678901");
    expect(res.dados?.ait).toBe("E012345678");
    expect(res.dados?.orgaoOuTribunal).toBe("DER-SP");
  });

  it("valida numeracao CNJ, resolve endpoint por tribunal e consulta API publica DataJud offline", async () => {
    const dv = calcularDigitoVerificadorCNJ("0000001", "2026", "826", "0100");
    const numeroValido = `0000001-${dv}.2026.8.26.0100`;
    expect(validarNumeroCNJ(numeroValido)).toBe(true);
    expect(validarNumeroCNJ("0000001-99.2026.8.26.0100")).toBe(false);

    expect(resolverEndpointDataJudPorNumeroCNJ(numeroValido)).toBe(
      "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search"
    );

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        hits: {
          hits: [
            {
              _source: {
                numeroProcesso: "00000015620268260100",
                tribunal: "TJSP",
                dataAjuizamento: "2026-02-10T12:00:00.000Z",
                dataHoraUltimaAtualizacao: "2026-11-01T15:30:00.000Z",
                classe: { codigo: 7, nome: "Procedimento Comum Civel" },
                orgaoJulgador: { codigo: 100, nome: "1a Vara Civel" },
                movimentos: [
                  { codigo: 26, nome: "Distribuicao", dataHora: "2026-02-10T12:05:00.000Z" },
                  { codigo: 85, nome: "Peticao Juntada", dataHora: "2026-11-01T14:00:00.000Z" },
                ],
              },
            },
          ],
        },
      }),
    });

    const proc = await consultarProcessoDataJud(
      numeroValido,
      "chave-publica-cnj-teste",
      fetchMock as unknown as typeof fetch
    );
    expect(proc).not.toBeNull();
    expect(proc?.tribunal).toBe("TJSP");
    expect(proc?.classeNome).toBe("Procedimento Comum Civel");
    expect(proc?.movimentos[0].nome).toBe("Peticao Juntada");
    expect(fetchMock).toHaveBeenCalledTimes(1);

    // Segunda consulta usa cache local para respeitar rate-limit do DataJud
    const procCache = await consultarProcessoDataJud(
      numeroValido,
      "chave-publica-cnj-teste",
      fetchMock as unknown as typeof fetch
    );
    expect(procCache?.numeroProcesso).toBe("00000015620268260100");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
