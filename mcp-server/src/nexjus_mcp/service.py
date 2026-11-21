"""Regras das ferramentas MCP, independentes do SDK do MCP (testaveis sem cliente nem rede)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from . import privacy
from .backend import BackendClient
from .config import Settings
from .datajud import DataJudClient, formatar_numero_cnj, limpar_digitos, validar_numero_cnj
from .prazos import REGRAS, FeriadoLocal, calcular_prazo, classificar_status, parse_iso_date
from .store import JsonStore

logger = logging.getLogger(__name__)

STATUS_VALIDOS = ("concluido", "vencido", "hoje", "urgente", "no_prazo")
MAX_LIMITE = 500
MAX_DESCRICAO = 2000
AVISO = "Confira todo prazo no sistema oficial do tribunal ou do orgao autuador."


class ToolError(ValueError):
    """Erro de uso de uma ferramenta, com mensagem segura para o cliente MCP."""


def _hoje(valor: str | None, relogio: Callable[[], date]) -> date:
    if valor:
        try:
            return parse_iso_date(valor)
        except ValueError as exc:
            raise ToolError(str(exc)) from None
    return relogio()


def _limite(valor: int, maximo: int = MAX_LIMITE) -> int:
    if valor < 1:
        raise ToolError("limite deve ser maior que zero.")
    return min(valor, maximo)


class NexJusService:
    def __init__(
        self,
        settings: Settings,
        *,
        store: JsonStore | None = None,
        datajud: DataJudClient | None = None,
        backend: BackendClient | None = None,
        relogio: Callable[[], date] = date.today,
    ) -> None:
        self.settings = settings
        self.store = store or JsonStore(settings.data_file)
        api_key = settings.datajud_api_key.get_secret_value() if settings.datajud_api_key else None
        self.datajud = datajud or DataJudClient(api_key, timeout=settings.datajud_timeout)
        token = settings.api_token.get_secret_value() if settings.api_token else None
        self.backend = backend or BackendClient(settings.backend_url, token)
        self.relogio = relogio

    # ----- auxiliares -------------------------------------------------------------------------

    @property
    def modo(self) -> str:
        return self.settings.privacy

    def _feriados_locais(self, db: dict) -> list[FeriadoLocal]:
        out = []
        for item in db.get("feriadosLocais", []):
            if item.get("data") and item.get("uf"):
                out.append(
                    FeriadoLocal(
                        data=str(item["data"]),
                        nome=str(item.get("nome") or "feriado local"),
                        uf=str(item["uf"]),
                        municipio=item.get("municipio") or None,
                    )
                )
        return out

    def _cliente_publico(self, cliente: dict | None) -> dict | None:
        if not cliente:
            return None
        return {
            "id": cliente.get("id", ""),
            "nome": privacy.nome_cliente(cliente.get("nome"), self.modo),
            "uf": cliente.get("uf", ""),
            "municipio": cliente.get("municipio", ""),
        }

    def _processo_publico(self, processo: dict | None, veiculos: dict[str, dict]) -> dict | None:
        if not processo:
            return None
        veiculo = veiculos.get(processo.get("veiculoId") or "")
        return {
            "id": processo.get("id", ""),
            "numero": processo.get("numero", ""),
            "tipo": processo.get("tipo", ""),
            "fase": processo.get("fase", ""),
            "orgao_ou_tribunal": processo.get("orgaoOuTribunal", ""),
            "uf": processo.get("uf", ""),
            "municipio": processo.get("municipio", ""),
            "ultimo_andamento": privacy.redigir_texto(processo.get("ultimoAndamento"), self.modo),
            "data_ultima_movimentacao": processo.get("dataUltimaMovimentacao", ""),
            "placa": privacy.placa(veiculo.get("placa"), self.modo) if veiculo else "",
        }

    def _indices(self, db: dict) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
        clientes = {c.get("id"): c for c in db.get("clientes", []) if c.get("id")}
        processos = {p.get("id"): p for p in db.get("processos", []) if p.get("id")}
        veiculos = {v.get("id"): v for v in db.get("veiculos", []) if v.get("id")}
        return clientes, processos, veiculos

    def _itens_prazo(self, db: dict, hoje: date) -> tuple[list[dict], int]:
        """Todos os prazos com status calculado. Devolve tambem quantos tinham data invalida."""
        clientes, processos, veiculos = self._indices(db)
        itens = []
        invalidos = 0
        for prazo in db.get("prazos", []):
            try:
                venc = parse_iso_date(str(prazo.get("dataVencimento") or ""))
            except ValueError:
                invalidos += 1
                continue
            concluido = bool(prazo.get("concluido"))
            status, dias = classificar_status(venc, hoje, concluido)
            processo = processos.get(prazo.get("processoId") or "")
            cliente = clientes.get(processo.get("clienteId")) if processo else None
            itens.append(
                {
                    "id": prazo.get("id", ""),
                    "titulo": privacy.redigir_texto(prazo.get("titulo"), self.modo),
                    "regra": prazo.get("regra", ""),
                    "contagem": prazo.get("contagem", ""),
                    "dias_prazo": prazo.get("diasPrazo"),
                    "data_publicacao_ou_notificacao": prazo.get("dataPublicacaoOuNotificacao", ""),
                    "data_inicio_contagem": prazo.get("dataInicioContagem", ""),
                    "data_vencimento": venc.isoformat(),
                    "dias_restantes": dias,
                    "status": status,
                    "concluido": concluido,
                    "processo": self._processo_publico(processo, veiculos),
                    "cliente": self._cliente_publico(cliente),
                }
            )
        itens.sort(key=lambda item: (item["data_vencimento"], item["id"]))
        return itens, invalidos

    def _localizar_processo(self, db: dict, referencia: str) -> dict | None:
        ref = (referencia or "").strip()
        if not ref:
            return None
        digitos = limpar_digitos(ref)
        for processo in db.get("processos", []):
            if processo.get("id") == ref:
                return processo
            numero = str(processo.get("numero") or "")
            if numero == ref or (len(digitos) >= 10 and limpar_digitos(numero) == digitos):
                return processo
        return None

    # ----- ferramentas ------------------------------------------------------------------------

    def calculate_deadline(
        self,
        regra: str,
        data_publicacao_ou_notificacao: str,
        uf: str,
        dias_prazo: int | None = None,
        contagem: str | None = None,
        municipio: str | None = None,
    ) -> dict:
        db = self.store.load()
        try:
            resultado = calcular_prazo(
                regra=regra,
                data_publicacao_ou_notificacao=data_publicacao_ou_notificacao,
                uf=uf,
                dias_prazo=dias_prazo,
                contagem=contagem,  # type: ignore[arg-type]
                municipio=municipio,
                feriados_locais=self._feriados_locais(db),
            )
        except ValueError as exc:
            raise ToolError(str(exc)) from None
        return resultado.to_dict()

    def list_deadlines(
        self,
        status: list[str] | None = None,
        processo: str | None = None,
        cliente_id: str | None = None,
        incluir_concluidos: bool = False,
        hoje: str | None = None,
        limite: int = 100,
    ) -> dict:
        referencia = _hoje(hoje, self.relogio)
        filtro = set(status or [])
        desconhecidos = filtro - set(STATUS_VALIDOS)
        if desconhecidos:
            raise ToolError(f"Status invalido: {', '.join(sorted(desconhecidos))}. Use: {', '.join(STATUS_VALIDOS)}")
        if "concluido" in filtro:
            incluir_concluidos = True
        db = self.store.load()
        itens, invalidos = self._itens_prazo(db, referencia)
        alvo_processo = self._localizar_processo(db, processo) if processo else None
        if processo and alvo_processo is None:
            raise ToolError("Processo nao encontrado no arquivo local.")

        selecionados = []
        for item in itens:
            if item["concluido"] and not incluir_concluidos:
                continue
            if filtro and item["status"] not in filtro:
                continue
            if alvo_processo and (item["processo"] or {}).get("id") != alvo_processo.get("id"):
                continue
            if cliente_id and (item["cliente"] or {}).get("id") != cliente_id:
                continue
            selecionados.append(item)
        n = _limite(limite)
        return {
            "hoje": referencia.isoformat(),
            "total": len(selecionados),
            "prazos": selecionados[:n],
            "truncado": len(selecionados) > n,
            "registros_com_data_invalida": invalidos,
            "aviso": AVISO,
        }

    def deadlines_this_week(self, hoje: str | None = None) -> dict:
        """Prazos pendentes de hoje ate domingo desta semana, mais os ja vencidos."""
        referencia = _hoje(hoje, self.relogio)
        inicio_semana = referencia - timedelta(days=referencia.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        itens, invalidos = self._itens_prazo(self.store.load(), referencia)
        pendentes = [i for i in itens if not i["concluido"]]
        vencidos = [i for i in pendentes if i["status"] == "vencido"]
        semana = [i for i in pendentes if referencia.isoformat() <= i["data_vencimento"] <= fim_semana.isoformat()]
        por_dia: dict[str, int] = {}
        for item in semana:
            por_dia[item["data_vencimento"]] = por_dia.get(item["data_vencimento"], 0) + 1
        return {
            "hoje": referencia.isoformat(),
            "semana_inicio": inicio_semana.isoformat(),
            "semana_fim": fim_semana.isoformat(),
            "vencidos": vencidos,
            "esta_semana": semana,
            "quantidade_por_dia": por_dia,
            "registros_com_data_invalida": invalidos,
            "aviso": AVISO,
        }

    def _consultar_datajud(self, numero: str) -> dict | None:
        try:
            return self.datajud.consultar(numero)
        except ValueError as exc:
            raise ToolError(str(exc)) from None
        except RuntimeError as exc:
            raise ToolError(str(exc)) from None

    def datajud_lookup_case(self, numero: str, movimentos: int = 5) -> dict:
        digitos = limpar_digitos(numero)
        if len(digitos) != 20 or not validar_numero_cnj(digitos):
            raise ToolError("Numero CNJ invalido: informe os 20 digitos com digito verificador correto.")
        dados = self._consultar_datajud(digitos)
        db = self.store.load()
        local = self._localizar_processo(db, digitos)
        _, _, veiculos = self._indices(db)
        resposta: dict = {
            "numero": formatar_numero_cnj(digitos),
            "encontrado": dados is not None,
            "processo_local": self._processo_publico(local, veiculos),
            "fonte": "DataJud (API publica do CNJ)",
        }
        if dados is not None:
            n = _limite(movimentos, 100)
            resposta.update(
                {
                    "tribunal": dados["tribunal"],
                    "classe": dados["classe"],
                    "orgao_julgador": dados["orgao_julgador"],
                    "data_ajuizamento": dados["data_ajuizamento"],
                    "data_ultima_atualizacao": dados["data_ultima_atualizacao"],
                    "total_movimentos": len(dados["movimentos"]),
                    "ultimos_movimentos": dados["movimentos"][:n],
                }
            )
        return resposta

    def case_movements(self, processo: str, limite: int = 20, fonte: str = "auto") -> dict:
        if fonte not in ("auto", "datajud", "local"):
            raise ToolError("fonte deve ser 'auto', 'datajud' ou 'local'.")
        n = _limite(limite, MAX_LIMITE)
        db = self.store.load()
        local = self._localizar_processo(db, processo)
        numero = str(local.get("numero") or "") if local else processo
        digitos = limpar_digitos(numero)
        cnj_valido = len(digitos) == 20 and validar_numero_cnj(digitos)

        usar_datajud = fonte == "datajud" or (fonte == "auto" and cnj_valido and self.datajud.configured)
        if usar_datajud:
            if not cnj_valido:
                raise ToolError("O processo nao tem numero CNJ valido para consultar no DataJud.")
            dados = self._consultar_datajud(digitos)
            movimentos = dados["movimentos"] if dados else []
            return {
                "processo": formatar_numero_cnj(digitos),
                "fonte": "datajud",
                "encontrado": dados is not None,
                "total": len(movimentos),
                "movimentos": movimentos[:n],
            }

        if local is None:
            raise ToolError("Processo nao encontrado no arquivo local e DataJud indisponivel para este numero.")
        movimentos = []
        if local.get("ultimoAndamento"):
            movimentos.append(
                {
                    "nome": privacy.redigir_texto(local.get("ultimoAndamento"), self.modo),
                    "data_hora": local.get("dataUltimaMovimentacao", ""),
                    "origem": "registro local",
                }
            )
        return {
            "processo": local.get("numero", ""),
            "fonte": "local",
            "encontrado": True,
            "total": len(movimentos),
            "movimentos": movimentos[:n],
            "observacao": "O arquivo local guarda apenas o ultimo andamento. Configure o DataJud para o historico.",
        }

    def clients_with_pending_items(self, hoje: str | None = None, dias: int = 7) -> dict:
        """Clientes com prazos vencidos ou vencendo nos proximos `dias` dias."""
        if dias < 0 or dias > 365:
            raise ToolError("dias deve estar entre 0 e 365.")
        referencia = _hoje(hoje, self.relogio)
        limite = (referencia + timedelta(days=dias)).isoformat()
        itens, _ = self._itens_prazo(self.store.load(), referencia)
        grupos: dict[str, dict] = {}
        sem_cliente = 0
        for item in itens:
            if item["concluido"] or item["data_vencimento"] > limite:
                continue
            cliente = item["cliente"]
            if not cliente:
                sem_cliente += 1
                continue
            grupo = grupos.setdefault(
                cliente["id"],
                {
                    "cliente": cliente,
                    "vencidos": 0,
                    "hoje": 0,
                    "urgentes": 0,
                    "proximos": 0,
                    "proximo_vencimento": None,
                    "processos": [],
                    "prazos": [],
                },
            )
            chave = {"vencido": "vencidos", "hoje": "hoje", "urgente": "urgentes", "no_prazo": "proximos"}
            grupo[chave[item["status"]]] += 1
            if item["status"] != "vencido" and grupo["proximo_vencimento"] is None:
                grupo["proximo_vencimento"] = item["data_vencimento"]
            numero = (item["processo"] or {}).get("numero")
            if numero and numero not in grupo["processos"]:
                grupo["processos"].append(numero)
            grupo["prazos"].append(
                {
                    "id": item["id"],
                    "titulo": item["titulo"],
                    "data_vencimento": item["data_vencimento"],
                    "status": item["status"],
                }
            )
        clientes = sorted(
            grupos.values(),
            key=lambda g: (-(g["vencidos"] + g["hoje"] + g["urgentes"]), g["proximo_vencimento"] or "9999"),
        )
        return {
            "hoje": referencia.isoformat(),
            "ate": limite,
            "total_clientes": len(clientes),
            "clientes": clientes,
            "prazos_sem_cliente": sem_cliente,
            "privacidade": self.modo,
        }

    def record_movement(
        self,
        processo: str,
        descricao: str,
        data: str | None = None,
        regra_prazo: str | None = None,
        titulo_prazo: str | None = None,
        dias_prazo: int | None = None,
    ) -> dict:
        """Registra o andamento no processo local e, se pedido, cria o prazo decorrente."""
        if self.settings.read_only:
            raise ToolError("Servidor em modo somente leitura (NEXJUS_MCP_READ_ONLY).")
        texto = " ".join((descricao or "").split())
        if not texto:
            raise ToolError("descricao e obrigatoria.")
        if len(texto) > MAX_DESCRICAO:
            raise ToolError(f"descricao deve ter no maximo {MAX_DESCRICAO} caracteres.")
        data_mov = _hoje(data, self.relogio)
        if regra_prazo is not None and regra_prazo not in REGRAS:
            raise ToolError(f"Regra de prazo desconhecida: {regra_prazo}. Use uma de: {', '.join(REGRAS)}")

        def mutate(db: dict) -> dict:
            alvo = self._localizar_processo(db, processo)
            if alvo is None:
                raise ToolError("Processo nao encontrado no arquivo local.")
            anterior = {
                "ultimo_andamento": privacy.redigir_texto(alvo.get("ultimoAndamento"), self.modo),
                "data_ultima_movimentacao": alvo.get("dataUltimaMovimentacao", ""),
            }
            alvo["ultimoAndamento"] = texto
            alvo["dataUltimaMovimentacao"] = data_mov.isoformat()
            resultado: dict = {
                "processo_id": alvo.get("id", ""),
                "numero": alvo.get("numero", ""),
                "anterior": anterior,
                "registrado": {
                    "ultimo_andamento": privacy.redigir_texto(texto, self.modo),
                    "data_ultima_movimentacao": data_mov.isoformat(),
                },
                "prazo_criado": None,
            }
            if regra_prazo:
                uf = str(alvo.get("uf") or "")
                municipio = alvo.get("municipio") or None
                try:
                    calculo = calcular_prazo(
                        regra=regra_prazo,
                        data_publicacao_ou_notificacao=data_mov.isoformat(),
                        uf=uf,
                        dias_prazo=dias_prazo,
                        municipio=municipio,
                        feriados_locais=self._feriados_locais(db),
                    )
                except ValueError as exc:
                    raise ToolError(str(exc)) from None
                novo = {
                    "id": f"prz-mcp-{uuid.uuid4().hex[:12]}",
                    "processoId": alvo.get("id", ""),
                    "titulo": " ".join((titulo_prazo or texto).split())[:200],
                    "regra": regra_prazo,
                    "dataPublicacaoOuNotificacao": calculo.data_publicacao_ou_notificacao,
                    "diasPrazo": calculo.dias_prazo,
                    "contagem": calculo.contagem,
                    "uf": calculo.uf,
                    "dataInicioContagem": calculo.data_inicio_contagem,
                    "dataVencimento": calculo.data_vencimento,
                    "concluido": False,
                    "criadoEm": datetime.now(UTC).isoformat(timespec="seconds"),
                }
                if municipio:
                    novo["municipio"] = municipio
                db.setdefault("prazos", []).append(novo)
                resultado["prazo_criado"] = {"id": novo["id"], "calculo": calculo.to_dict()}
            return resultado

        resultado = self.store.update(mutate)
        logger.info("Andamento registrado no processo %s", resultado["processo_id"])
        return resultado

    def generate_agenda(self, hoje: str | None = None, dias: int = 7, fonte: str = "local") -> dict:
        if dias < 1 or dias > 60:
            raise ToolError("dias deve estar entre 1 e 60.")
        if fonte not in ("local", "backend"):
            raise ToolError("fonte deve ser 'local' ou 'backend'.")
        referencia = _hoje(hoje, self.relogio)
        limite = (referencia + timedelta(days=dias)).isoformat()
        itens, _ = self._itens_prazo(self.store.load(), referencia)
        por_id = {item["id"]: item for item in itens}

        grupos: dict[str, list[dict]] = {"vencido": [], "hoje": [], "urgente": [], "no_prazo": []}
        if fonte == "backend":
            try:
                remota = self.backend.agenda(referencia, dias)
            except RuntimeError as exc:
                raise ToolError(str(exc)) from None
            mapa = {"vencidos": "vencido", "vencendo_hoje": "hoje", "urgentes": "urgente", "proximos": "no_prazo"}
            for campo, status in mapa.items():
                for entrada in remota.get(campo) or []:
                    if not isinstance(entrada, dict):
                        continue
                    local = por_id.get(str(entrada.get("id")))
                    item = (
                        dict(local)
                        if local
                        else {"id": entrada.get("id"), "titulo": "", "processo": None, "cliente": None}
                    )
                    item["data_vencimento"] = str(entrada.get("due_date") or item.get("data_vencimento", ""))
                    item["dias_restantes"] = entrada.get("dias_restantes", item.get("dias_restantes"))
                    item["status"] = status
                    grupos[status].append(item)
        else:
            for item in itens:
                if item["concluido"] or item["data_vencimento"] > limite:
                    continue
                grupos[item["status"]].append(item)

        agenda = {
            "hoje": referencia.isoformat(),
            "dias": dias,
            "fonte": fonte,
            "vencidos": grupos["vencido"],
            "vencendo_hoje": grupos["hoje"],
            "urgentes": grupos["urgente"],
            "proximos": grupos["no_prazo"],
            "total_criticos": len(grupos["vencido"]) + len(grupos["hoje"]) + len(grupos["urgente"]),
        }
        agenda["texto"] = formatar_agenda(agenda)
        return agenda


def _linha(item: dict) -> str:
    processo = (item.get("processo") or {}).get("numero") or "sem processo"
    cliente = (item.get("cliente") or {}).get("nome") or "sem cliente"
    titulo = item.get("titulo") or "prazo"
    return f"- {item.get('data_vencimento', '')} | {titulo} | {processo} | {cliente}"


def formatar_agenda(agenda: dict) -> str:
    linhas = [f"Agenda de prazos de {agenda['hoje']} (proximos {agenda['dias']} dias)", ""]
    secoes = (
        ("Vencidos", "vencidos"),
        ("Vencem hoje", "vencendo_hoje"),
        ("Urgentes (ate 3 dias)", "urgentes"),
        ("Proximos", "proximos"),
    )
    for titulo, campo in secoes:
        itens = agenda[campo]
        linhas.append(f"{titulo}: {len(itens)}")
        linhas.extend(_linha(item) for item in itens)
        linhas.append("")
    linhas.append(AVISO)
    return "\n".join(linhas)
