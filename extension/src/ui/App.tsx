import React, { useEffect, useState } from "react";
import { atualizarBadgeExtensao, resumirAlertasPrazos } from "../background/alarms";
import { calcularPrazo, classificarStatusPrazo, formatISODate } from "../domain/prazos";
import { consultarProcessoDataJud } from "../services/datajud";
import {
  exportarClientesCSV,
  exportarPrazosCSV,
  exportarProcessosCSV,
  exportarVeiculosCSV,
  importarClientesCSV,
} from "../storage/csv";
import {
  carregarDatabase,
  criarDatabaseVazio,
  salvarDatabase,
  verificarEstadoCriptografia,
} from "../storage/storage";
import type {
  Cliente,
  DataJudProcesso,
  LeituraPaginaResultado,
  NexJusDatabase,
  Prazo,
  Processo,
  RegraPrazo,
  UF,
  Veiculo,
} from "../types/models";

type AbaAtiva = "prazos" | "cadastros" | "fontes" | "seguranca";

const UFS: UF[] = [
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
  "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
  "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
];

export function App(): React.ReactElement {
  const [aba, setAba] = useState<AbaAtiva>("prazos");
  const [db, setDb] = useState<NexJusDatabase>(criarDatabaseVazio);
  const [criptografado, setCriptografado] = useState(false);
  const [bloqueado, setBloqueado] = useState(false);
  const [senhaSessao, setSenhaSessao] = useState("");
  const [mensagemStatus, setMensagemStatus] = useState<string>("");

  // Formulario de prazo
  const [tituloPrazo, setTituloPrazo] = useState("");
  const [regraPrazo, setRegraPrazo] = useState<RegraPrazo>("cpc_15");
  const [dataPubPrazo, setDataPubPrazo] = useState(formatISODate(new Date()));
  const [ufPrazo, setUfPrazo] = useState<UF>("SP");

  // Formulario de cliente
  const [nomeCliente, setNomeCliente] = useState("");
  const [docCliente, setDocCliente] = useState("");
  const [ufCliente, setUfCliente] = useState<UF>("SP");

  // Formulario de veiculo
  const [placaVeiculo, setPlacaVeiculo] = useState("");
  const [renavamVeiculo, setRenavamVeiculo] = useState("");

  // Formulario de processo
  const [numeroProcesso, setNumeroProcesso] = useState("");
  const [orgaoProcesso, setOrgaoProcesso] = useState("TJSP");

  // Fontes (Pagina aberta + DataJud)
  const [leituraPagina, setLeituraPagina] = useState<LeituraPaginaResultado | null>(null);
  const [numeroDataJud, setNumeroDataJud] = useState("");
  const [chaveDataJud, setChaveDataJud] = useState("");
  const [resultadoDataJud, setResultadoDataJud] = useState<DataJudProcesso | null>(null);

  // CSV
  const [csvSaida, setCsvSaida] = useState("");

  useEffect(() => {
    void (async () => {
      const isEnc = await verificarEstadoCriptografia();
      setCriptografado(isEnc);
      if (isEnc) {
        setBloqueado(true);
        return;
      }
      const loaded = await carregarDatabase();
      setDb(loaded);
      setChaveDataJud(loaded.datajudApiKey ?? "");
      atualizarBadgeExtensao(loaded.prazos);
    })();
  }, []);

  async function persistir(novoDb: NexJusDatabase, senhaOverride?: string): Promise<void> {
    setDb(novoDb);
    const senhaAtiva = senhaOverride !== undefined ? senhaOverride : criptografado ? senhaSessao : undefined;
    await salvarDatabase(novoDb, { criptografarComSenha: senhaAtiva || undefined });
    atualizarBadgeExtensao(novoDb.prazos);
  }

  async function handleDesbloquear(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    try {
      const loaded = await carregarDatabase(senhaSessao);
      setDb(loaded);
      setChaveDataJud(loaded.datajudApiKey ?? "");
      setBloqueado(false);
      setMensagemStatus("Armazenamento local desbloqueado.");
    } catch (err) {
      setMensagemStatus((err as Error).message);
    }
  }

  async function handleAdicionarPrazo(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    if (!tituloPrazo.trim()) {
      return;
    }
    const calc = calcularPrazo({
      regra: regraPrazo,
      dataPublicacaoOuNotificacao: dataPubPrazo,
      uf: ufPrazo,
      feriadosLocais: db.feriadosLocais,
    });
    const novo: Prazo = {
      id: `prz-${Date.now()}`,
      processoId: db.processos[0]?.id ?? "",
      titulo: tituloPrazo.trim(),
      regra: regraPrazo,
      dataPublicacaoOuNotificacao: calc.dataPublicacaoOuNotificacao,
      diasPrazo: calc.diasPrazo,
      contagem: calc.contagem,
      uf: ufPrazo,
      dataInicioContagem: calc.dataInicioContagem,
      dataVencimento: calc.dataVencimento,
      concluido: false,
      criadoEm: new Date().toISOString(),
    };
    await persistir({ ...db, prazos: [novo, ...db.prazos] });
    setTituloPrazo("");
    setMensagemStatus(`Prazo calculado: vencimento em ${novo.dataVencimento}.`);
  }

  async function handleAlternarPrazoConcluido(id: string): Promise<void> {
    const atualizados = db.prazos.map((p) =>
      p.id === id ? { ...p, concluido: !p.concluido } : p
    );
    await persistir({ ...db, prazos: atualizados });
  }

  async function handleAdicionarCliente(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    if (!nomeCliente.trim()) {
      return;
    }
    const novo: Cliente = {
      id: `cli-${Date.now()}`,
      nome: nomeCliente.trim(),
      documento: docCliente.trim(),
      telefone: "",
      email: "",
      uf: ufCliente,
      municipio: "",
      criadoEm: new Date().toISOString(),
    };
    await persistir({ ...db, clientes: [...db.clientes, novo] });
    setNomeCliente("");
    setDocCliente("");
  }

  async function handleAdicionarVeiculo(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    if (!placaVeiculo.trim()) {
      return;
    }
    const novo: Veiculo = {
      id: `vei-${Date.now()}`,
      clienteId: db.clientes[0]?.id ?? "",
      placa: placaVeiculo.trim().toUpperCase(),
      renavam: renavamVeiculo.trim(),
      uf: "SP",
      marcaModelo: "",
      criadoEm: new Date().toISOString(),
    };
    await persistir({ ...db, veiculos: [...db.veiculos, novo] });
    setPlacaVeiculo("");
    setRenavamVeiculo("");
  }

  async function handleAdicionarProcesso(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    if (!numeroProcesso.trim()) {
      return;
    }
    const novo: Processo = {
      id: `proc-${Date.now()}`,
      clienteId: db.clientes[0]?.id ?? "",
      numero: numeroProcesso.trim(),
      tipo: "judicial",
      orgaoOuTribunal: orgaoProcesso.trim() || "TJSP",
      fase: "conhecimento",
      uf: "SP",
      municipio: "",
      ultimoAndamento: "",
      dataUltimaMovimentacao: formatISODate(new Date()),
      criadoEm: new Date().toISOString(),
    };
    await persistir({ ...db, processos: [...db.processos, novo] });
    setNumeroProcesso("");
  }

  function handleLerPaginaAberta(): void {
    if (typeof chrome !== "undefined" && chrome.tabs?.query) {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const tabId = tabs[0]?.id;
        if (!tabId) {
          setMensagemStatus("Nenhuma aba ativa identificada.");
          return;
        }
        chrome.tabs.sendMessage(tabId, { type: "NEXJUS_READ_CURRENT_PAGE" }, (res: LeituraPaginaResultado) => {
          if (chrome.runtime.lastError || !res) {
            setMensagemStatus("A pagina atual nao possui leitor ativo ou precisa ser recarregada.");
            return;
          }
          setLeituraPagina(res);
          setMensagemStatus(res.mensagem);
        });
      });
    } else {
      setMensagemStatus("Leitura de aba disponivel apenas dentro do navegador Chrome.");
    }
  }

  async function handleConsultarDataJud(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    try {
      const proc = await consultarProcessoDataJud(numeroDataJud, chaveDataJud);
      setResultadoDataJud(proc);
      setMensagemStatus(proc ? "Consulta DataJud concluida." : "Processo nao encontrado no DataJud.");
    } catch (err) {
      setMensagemStatus((err as Error).message);
    }
  }

  const hojeISO = formatISODate(new Date());
  const resumoAlertas = resumirAlertasPrazos(db.prazos, hojeISO);

  if (bloqueado) {
    return (
      <div className="nexjus-shell">
        <header className="nexjus-header">
          <h1>NexJus</h1>
          <span className="nexjus-subtitle">Dados locais criptografados (LGPD)</span>
        </header>
        <form className="nexjus-card" onSubmit={(e) => void handleDesbloquear(e)}>
          <h2>Desbloquear banco local</h2>
          <div className="nexjus-form-row">
            <input
              type="password"
              placeholder="Senha de criptografia"
              value={senhaSessao}
              onChange={(e) => setSenhaSessao(e.target.value)}
            />
            <button type="submit" className="nexjus-btn">
              Desbloquear
            </button>
          </div>
          {mensagemStatus && <p>{mensagemStatus}</p>}
        </form>
      </div>
    );
  }

  return (
    <div className="nexjus-shell">
      <header className="nexjus-header">
        <h1>NexJus</h1>
        <span className="nexjus-subtitle">
          Alertas criticos: {resumoAlertas.totalCriticos}
        </span>
      </header>

      <nav className="nexjus-tabs" aria-label="Secoes principais">
        <button
          type="button"
          className={`nexjus-tab ${aba === "prazos" ? "active" : ""}`}
          onClick={() => setAba("prazos")}
        >
          Prazos ({db.prazos.length})
        </button>
        <button
          type="button"
          className={`nexjus-tab ${aba === "cadastros" ? "active" : ""}`}
          onClick={() => setAba("cadastros")}
        >
          Cadastros e CSV
        </button>
        <button
          type="button"
          className={`nexjus-tab ${aba === "fontes" ? "active" : ""}`}
          onClick={() => setAba("fontes")}
        >
          Pagina Aberta e DataJud
        </button>
        <button
          type="button"
          className={`nexjus-tab ${aba === "seguranca" ? "active" : ""}`}
          onClick={() => setAba("seguranca")}
        >
          Seguranca LGPD
        </button>
      </nav>

      {mensagemStatus && (
        <div className="nexjus-card" role="status">
          {mensagemStatus}
        </div>
      )}

      {aba === "prazos" && (
        <>
          <form className="nexjus-card" onSubmit={(e) => void handleAdicionarPrazo(e)}>
            <h2>Novo Prazo Processual (CPC / CTB)</h2>
            <div className="nexjus-form-row">
              <input
                type="text"
                placeholder="Descricao (ex: Contestacao, Defesa Previa)"
                value={tituloPrazo}
                onChange={(e) => setTituloPrazo(e.target.value)}
              />
            </div>
            <div className="nexjus-form-row">
              <select
                aria-label="Regra do prazo"
                value={regraPrazo}
                onChange={(e) => setRegraPrazo(e.target.value as RegraPrazo)}
              >
                <option value="cpc_15">CPC - 15 dias uteis (Contestacao/Apelacao)</option>
                <option value="cpc_5">CPC - 5 dias uteis (Embargos de Declaracao)</option>
                <option value="ctb_defesa_previa">CTB - Defesa Previa (30 dias)</option>
                <option value="ctb_jari">CTB - Recurso JARI (30 dias)</option>
                <option value="ctb_cetran">CTB - Recurso CETRAN (30 dias)</option>
              </select>
              <input
                type="date"
                aria-label="Data de publicacao ou notificacao"
                value={dataPubPrazo}
                onChange={(e) => setDataPubPrazo(e.target.value)}
              />
              <select
                aria-label="UF do prazo"
                value={ufPrazo}
                onChange={(e) => setUfPrazo(e.target.value as UF)}
              >
                {UFS.map((sigla) => (
                  <option key={sigla} value={sigla}>
                    {sigla}
                  </option>
                ))}
              </select>
              <button type="submit" className="nexjus-btn">
                Calcular e Salvar
              </button>
            </div>
          </form>

          <div className="nexjus-card">
            <h2>Prazos Cadastrados</h2>
            <ul className="nexjus-list">
              {db.prazos.map((p) => {
                const info = classificarStatusPrazo(p, hojeISO);
                return (
                  <li key={p.id}>
                    <div>
                      <strong>{p.titulo}</strong> ({p.uf}) - Vence: {p.dataVencimento}
                    </div>
                    <div>
                      <span className={`badge ${info.status}`}>
                        [{info.status.toUpperCase()}]
                      </span>{" "}
                      <button
                        type="button"
                        className="nexjus-btn secondary"
                        onClick={() => void handleAlternarPrazoConcluido(p.id)}
                      >
                        {p.concluido ? "Reabrir" : "Concluir"}
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </>
      )}

      {aba === "cadastros" && (
        <>
          <form className="nexjus-card" onSubmit={(e) => void handleAdicionarCliente(e)}>
            <h2>Clientes ({db.clientes.length})</h2>
            <div className="nexjus-form-row">
              <input
                type="text"
                placeholder="Nome do cliente"
                value={nomeCliente}
                onChange={(e) => setNomeCliente(e.target.value)}
              />
              <input
                type="text"
                placeholder="CPF ou CNPJ"
                value={docCliente}
                onChange={(e) => setDocCliente(e.target.value)}
              />
              <select value={ufCliente} onChange={(e) => setUfCliente(e.target.value as UF)}>
                {UFS.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
              <button type="submit" className="nexjus-btn">
                Adicionar Cliente
              </button>
            </div>
          </form>

          <form className="nexjus-card" onSubmit={(e) => void handleAdicionarVeiculo(e)}>
            <h2>Veiculos ({db.veiculos.length})</h2>
            <div className="nexjus-form-row">
              <input
                type="text"
                placeholder="Placa (ex: ABC1D23)"
                value={placaVeiculo}
                onChange={(e) => setPlacaVeiculo(e.target.value)}
              />
              <input
                type="text"
                placeholder="RENAVAM"
                value={renavamVeiculo}
                onChange={(e) => setRenavamVeiculo(e.target.value)}
              />
              <button type="submit" className="nexjus-btn">
                Adicionar Veiculo
              </button>
            </div>
          </form>

          <form className="nexjus-card" onSubmit={(e) => void handleAdicionarProcesso(e)}>
            <h2>Processos ({db.processos.length})</h2>
            <div className="nexjus-form-row">
              <input
                type="text"
                placeholder="Numero CNJ ou AIT"
                value={numeroProcesso}
                onChange={(e) => setNumeroProcesso(e.target.value)}
              />
              <input
                type="text"
                placeholder="Tribunal ou Orgao"
                value={orgaoProcesso}
                onChange={(e) => setOrgaoProcesso(e.target.value)}
              />
              <button type="submit" className="nexjus-btn">
                Adicionar Processo
              </button>
            </div>
          </form>

          <div className="nexjus-card">
            <h2>Importacao e Exportacao CSV</h2>
            <div className="nexjus-form-row">
              <button
                type="button"
                className="nexjus-btn secondary"
                onClick={() => setCsvSaida(exportarClientesCSV(db.clientes))}
              >
                Exportar Clientes CSV
              </button>
              <button
                type="button"
                className="nexjus-btn secondary"
                onClick={() => setCsvSaida(exportarVeiculosCSV(db.veiculos))}
              >
                Exportar Veiculos CSV
              </button>
              <button
                type="button"
                className="nexjus-btn secondary"
                onClick={() => setCsvSaida(exportarProcessosCSV(db.processos))}
              >
                Exportar Processos CSV
              </button>
              <button
                type="button"
                className="nexjus-btn secondary"
                onClick={() => setCsvSaida(exportarPrazosCSV(db.prazos))}
              >
                Exportar Prazos CSV
              </button>
              <button
                type="button"
                className="nexjus-btn"
                onClick={() => {
                  const novos = importarClientesCSV(csvSaida);
                  void persistir({ ...db, clientes: [...db.clientes, ...novos] });
                }}
              >
                Importar Clientes do CSV
              </button>
            </div>
            <textarea
              rows={4}
              style={{ width: "100%", fontFamily: "monospace", fontSize: "11px" }}
              value={csvSaida}
              onChange={(e) => setCsvSaida(e.target.value)}
              placeholder="Conteudo CSV para exportar ou importar"
            />
          </div>
        </>
      )}

      {aba === "fontes" && (
        <>
          <div className="nexjus-card">
            <h2>Leitura da Pagina Aberta (PJe, eSAJ, Projudi, Senatran, Detran)</h2>
            <p>
              Le somente a pagina aberta pelo usuario na aba atual. Nunca contorna captcha.
            </p>
            <button type="button" className="nexjus-btn" onClick={handleLerPaginaAberta}>
              Ler Pagina Atual
            </button>
            {leituraPagina?.dados && (
              <pre style={{ fontSize: "11px", overflowX: "auto" }}>
                {JSON.stringify(leituraPagina.dados, null, 2)}
              </pre>
            )}
          </div>

          <form className="nexjus-card" onSubmit={(e) => void handleConsultarDataJud(e)}>
            <h2>Consulta Publica DataJud (CNJ)</h2>
            <div className="nexjus-form-row">
              <input
                type="text"
                placeholder="Numero CNJ (20 digitos)"
                value={numeroDataJud}
                onChange={(e) => setNumeroDataJud(e.target.value)}
              />
              <input
                type="password"
                placeholder="Chave publica DataJud"
                value={chaveDataJud}
                onChange={(e) => setChaveDataJud(e.target.value)}
              />
              <button type="submit" className="nexjus-btn">
                Consultar DataJud
              </button>
            </div>
            {resultadoDataJud && (
              <div>
                <strong>{resultadoDataJud.classeNome}</strong> - {resultadoDataJud.orgaoJulgadorNome}
              </div>
            )}
          </form>
        </>
      )}

      {aba === "seguranca" && (
        <div className="nexjus-card">
          <h2>Criptografia Opcional em chrome.storage.local (AES-GCM 256)</h2>
          <div className="nexjus-form-row">
            <input
              type="password"
              placeholder="Definir senha (min. 4 caracteres)"
              value={senhaSessao}
              onChange={(e) => setSenhaSessao(e.target.value)}
            />
            <button
              type="button"
              className="nexjus-btn"
              onClick={() => {
                setCriptografado(true);
                void persistir(db, senhaSessao);
                setMensagemStatus("Criptografia AES-GCM ativada para os dados locais.");
              }}
            >
              Ativar Criptografia
            </button>
            <button
              type="button"
              className="nexjus-btn secondary"
              onClick={() => {
                setCriptografado(false);
                setSenhaSessao("");
                void persistir(db, "");
                setMensagemStatus("Criptografia desativada.");
              }}
            >
              Desativar
            </button>
          </div>
        </div>
      )}

      <footer className="nexjus-notice">
        Aviso: Todo prazo calculado deve ser conferido pelo advogado no sistema oficial. Dados mantidos localmente (LGPD).
      </footer>
    </div>
  );
}
