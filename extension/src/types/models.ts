export type UF =
  | "AC" | "AL" | "AP" | "AM" | "BA" | "CE" | "DF" | "ES" | "GO"
  | "MA" | "MT" | "MS" | "MG" | "PA" | "PB" | "PR" | "PE" | "PI"
  | "RJ" | "RN" | "RS" | "RO" | "RR" | "SC" | "SP" | "SE" | "TO";

export interface Cliente {
  id: string;
  nome: string;
  documento: string;
  telefone: string;
  email: string;
  uf: UF;
  municipio: string;
  criadoEm: string;
}

export interface Veiculo {
  id: string;
  clienteId: string;
  placa: string;
  renavam: string;
  uf: UF;
  marcaModelo: string;
  criadoEm: string;
}

export type TipoProcesso = "judicial" | "transito";

export type FaseProcesso =
  | "conhecimento"
  | "recurso"
  | "execucao"
  | "autuacao"
  | "defesa_previa"
  | "jari"
  | "cetran";

export interface Processo {
  id: string;
  clienteId: string;
  veiculoId?: string;
  numero: string;
  tipo: TipoProcesso;
  orgaoOuTribunal: string;
  fase: FaseProcesso;
  uf: UF;
  municipio: string;
  ultimoAndamento: string;
  dataUltimaMovimentacao: string;
  criadoEm: string;
}

export type RegraPrazo =
  | "cpc_5"
  | "cpc_15"
  | "cpc_custom"
  | "ctb_defesa_previa"
  | "ctb_jari"
  | "ctb_cetran";

export type TipoContagem = "uteis" | "corridos";

export interface FeriadoLocal {
  data: string; // YYYY-MM-DD ou MM-DD
  nome: string;
  uf: UF;
  municipio?: string;
}

export interface Prazo {
  id: string;
  processoId: string;
  titulo: string;
  regra: RegraPrazo;
  dataPublicacaoOuNotificacao: string; // YYYY-MM-DD
  diasPrazo: number;
  contagem: TipoContagem;
  uf: UF;
  municipio?: string;
  dataInicioContagem: string; // YYYY-MM-DD
  dataVencimento: string; // YYYY-MM-DD
  concluido: boolean;
  criadoEm: string;
}

export interface NexJusDatabase {
  clientes: Cliente[];
  veiculos: Veiculo[];
  processos: Processo[];
  prazos: Prazo[];
  feriadosLocais: FeriadoLocal[];
  datajudApiKey?: string;
}

export type PortalOrigem = "pje" | "esaj" | "projudi" | "senatran" | "detran" | "desconhecido";

export interface LeituraPaginaResultado {
  status: "ok" | "captcha_blocked" | "unsupported";
  portal: PortalOrigem;
  url: string;
  mensagem: string;
  dados?: {
    numeroProcesso?: string;
    ait?: string;
    placa?: string;
    renavam?: string;
    orgaoOuTribunal?: string;
    classeOuInfracao?: string;
    partes?: string[];
    ultimoAndamento?: string;
    dataUltimaMovimentacao?: string;
  };
}

export interface DataJudMovimento {
  codigo: number;
  nome: string;
  dataHora: string;
}

export interface DataJudProcesso {
  numeroProcesso: string;
  tribunal: string;
  classeNome: string;
  orgaoJulgadorNome: string;
  dataAjuizamento: string;
  dataHoraUltimaAtualizacao: string;
  movimentos: DataJudMovimento[];
}
