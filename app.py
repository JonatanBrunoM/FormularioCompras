import streamlit as st
import ui_components as ui
import requests
import pandas as pd
import smtplib
import os
import datetime
import time
import base64
import json
import extra_streamlit_components as stx
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from streamlit_gsheets import GSheetsConnection
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from cryptography.fernet import Fernet, InvalidToken
import io
import uuid

if "form_count" not in st.session_state:
    st.session_state["form_count"] = 0
    
# ==============================================================================
# 1. Configuração upload de arquivos
# ==============================================================================
def obter_credenciais_google():
    credentials = st.session_state.get(
        "google_credentials"
    )

    if credentials is None:
        return None

    try:
        if credentials.expired:
            if credentials.refresh_token:
                credentials.refresh(Request())

                st.session_state[
                    "google_credentials"
                ] = credentials

            else:
                return None

        if not credentials.valid:
            return None

        return credentials

    except Exception as erro:
        print(
            "Erro ao renovar credenciais Google:",
            erro,
        )

        return None

def upload_para_google_drive(arquivo_streamlit, pasta_id=None):
    """
    Faz o upload de um arquivo do Streamlit para uma pasta específica do Google Drive.
    Usa os tokens de autenticação salvos na sessão do usuário.
    """
    try:
        credentials = obter_credenciais_google()

        if credentials is None:
            st.error(
                "Sua autorização do Google expirou. "
                "Saia do sistema e entre novamente."
            )

            return None

        service = build(
            "drive",
            "v3",
            credentials=credentials,
        )
        
        file_metadata = {'name': arquivo_streamlit.name}
        if pasta_id:
            file_metadata['parents'] = [pasta_id]
            
        arquivo_bytes = io.BytesIO(arquivo_streamlit.getvalue())
        media = MediaIoBaseUpload(arquivo_bytes, mimetype=arquivo_streamlit.type, resumable=True)
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Erro ao fazer upload para o Drive: {e}")
        return None

# ==============================================================================
# 2. Configuração front-end da página                
# ==============================================================================
st.set_page_config(
    page_title="Solicitação de Padronização de Produtos Químicos - CAPROQ",
    page_icon="logomini.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

ui.load_global_css()

# ==============================================================================
# 3. Definição de Alçadas, Conexão e Validação de Usuários (Via Google Sheets)
# ==============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

# ------------------------------------------------------------------------------
# Estrutura de dados para revisão de pareceres e reabertura de homologações
# ------------------------------------------------------------------------------
WORKSHEET_ALTERACOES_PARECERES = "Alteracoes_Pareceres"
WORKSHEET_HISTORICO_HOMOLOGACOES = "Historico_Homologacoes"

STATUS_ALTERACAO_PENDENTE = "Pendente"
STATUS_ALTERACAO_CONFIRMADA = "Confirmada"
STATUS_ALTERACAO_RECUSADA = "Recusada"
STATUS_ALTERACAO_CANCELADA = "Cancelada"

STATUS_REVISAO_NAO_APLICAVEL = "Não aplicável"
STATUS_REVISAO_REABERTO = "Reaberto"
STATUS_REVISAO_AGUARDANDO_ALTERACAO = "Aguardando alteração"
STATUS_REVISAO_ALTERACAO_EM_ANALISE = "Alteração em análise"
STATUS_REVISAO_ALTERACAO_CONFIRMADA = "Alteração confirmada"
STATUS_REVISAO_RETORNADO_HOMOLOGACAO = "Retornado à homologação"

COLUNAS_ALTERACOES_PARECERES = [
    "ID_Alteracao",
    "ID_Chamado",
    "Alcada",
    "Coluna_Parecer",
    "Decisao_Anterior",
    "Parecer_Anterior",
    "Decisao_Solicitada",
    "Parecer_Solicitado",
    "Justificativa_Alteracao",
    "Solicitante_Nome",
    "Solicitante_Email",
    "Data_Solicitacao",
    "Status_Alteracao",
    "Admin_Responsavel",
    "Admin_Email",
    "Data_Analise",
    "Motivo_Recusa",
    "Origem_Reabertura",
    "ID_Reabertura",
]

COLUNAS_HISTORICO_HOMOLOGACOES = [
    "ID_Historico",
    "ID_Chamado",
    "Versao_Homologacao",
    "Status_Final",
    "Parecer_Final_Admin",
    "Consideracoes_Finais",
    "Admin_Nome",
    "Admin_Email",
    "Data_Homologacao",
    "Motivo_Reabertura",
    "Alcada_Reaberta",
    "Data_Reabertura",
    "Admin_Reabertura",
    "Email_Admin_Reabertura",
    "Situacao_Registro",
]

COLUNAS_REVISAO_CHAMADO = {
    "Chamado_Reaberto": "NÃO",
    "ID_Reabertura_Atual": "",
    "Motivo_Reabertura": "",
    "Alcada_Reaberta": "",
    "Admin_Reabertura": "",
    "Email_Admin_Reabertura": "",
    "Data_Reabertura": "",
    "Status_Revisao": STATUS_REVISAO_NAO_APLICAVEL,
    "Quantidade_Reaberturas": 0,
    "Retornou_Homologacao_Apos_Revisao": "NÃO",
}


def _data_hora_registro() -> str:
    """Retorna data e hora em padrão estável para registros de auditoria."""
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def gerar_id_registro(prefixo: str) -> str:
    """Gera identificador único e legível para alterações e homologações."""
    prefixo_limpo = str(prefixo).strip().upper().replace(" ", "_")
    instante = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    sufixo = uuid.uuid4().hex[:8].upper()
    return f"{prefixo_limpo}-{instante}-{sufixo}"


def garantir_colunas_dataframe(
    df: pd.DataFrame,
    colunas: list[str],
) -> pd.DataFrame:
    """Devolve uma cópia com todas as colunas exigidas, na ordem definida."""
    resultado = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()

    for coluna in colunas:
        if coluna not in resultado.columns:
            resultado[coluna] = ""

    colunas_extras = [
        coluna for coluna in resultado.columns
        if coluna not in colunas
    ]
    return resultado[colunas + colunas_extras]


def garantir_colunas_revisao_chamado(df: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta os campos de controle sem alterar os registros existentes."""
    resultado = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()

    for coluna, valor_padrao in COLUNAS_REVISAO_CHAMADO.items():
        if coluna not in resultado.columns:
            resultado[coluna] = valor_padrao
        else:
            resultado[coluna] = resultado[coluna].where(
                resultado[coluna].notna(),
                valor_padrao,
            )

    if "Quantidade_Reaberturas" in resultado.columns:
        resultado["Quantidade_Reaberturas"] = pd.to_numeric(
            resultado["Quantidade_Reaberturas"],
            errors="coerce",
        ).fillna(0).astype(int)

    return resultado


def _carregar_worksheet_controlada(
    worksheet: str,
    colunas: list[str],
    cache_key: str,
    timestamp_key: str,
    forcar_atualizacao: bool = False,
) -> pd.DataFrame:
    """Lê uma aba de controle com cache e devolve sempre o schema completo."""
    agora = time.time()
    cache_valido = (
        cache_key in st.session_state
        and not forcar_atualizacao
        and (agora - st.session_state.get(timestamp_key, 0)) < 60
    )

    if cache_valido:
        return garantir_colunas_dataframe(
            st.session_state[cache_key],
            colunas,
        )

    try:
        df = conn.read(worksheet=worksheet, ttl=0)
        df = df.dropna(how="all")
        df = garantir_colunas_dataframe(df, colunas)
        st.session_state[cache_key] = df.copy()
        st.session_state[timestamp_key] = agora
        return df
    except Exception as erro:
        if cache_key in st.session_state:
            return garantir_colunas_dataframe(
                st.session_state[cache_key],
                colunas,
            )

        # A interface das etapas seguintes exibirá uma orientação específica.
        # Nesta etapa estrutural, retornamos o schema vazio sem interromper o app.
        print(f"Não foi possível ler a aba {worksheet}: {erro}")
        return pd.DataFrame(columns=colunas)


def _salvar_worksheet_controlada(
    worksheet: str,
    df: pd.DataFrame,
    colunas: list[str],
    cache_key: str,
    timestamp_key: str,
) -> bool:
    """Persiste uma aba de controle e sincroniza o cache local."""
    dados = garantir_colunas_dataframe(df, colunas)

    try:
        conn.update(worksheet=worksheet, data=dados)
        st.session_state[cache_key] = dados.copy()
        st.session_state[timestamp_key] = time.time()
        return True
    except Exception as erro:
        st.error(
            f"Não foi possível atualizar a aba '{worksheet}': {erro}"
        )
        return False


def carregar_alteracoes_pareceres(
    forcar_atualizacao: bool = False,
) -> pd.DataFrame:
    return _carregar_worksheet_controlada(
        worksheet=WORKSHEET_ALTERACOES_PARECERES,
        colunas=COLUNAS_ALTERACOES_PARECERES,
        cache_key="df_alteracoes_pareceres_cache",
        timestamp_key="df_alteracoes_pareceres_cache_timestamp",
        forcar_atualizacao=forcar_atualizacao,
    )


def salvar_alteracoes_pareceres(df: pd.DataFrame) -> bool:
    return _salvar_worksheet_controlada(
        worksheet=WORKSHEET_ALTERACOES_PARECERES,
        df=df,
        colunas=COLUNAS_ALTERACOES_PARECERES,
        cache_key="df_alteracoes_pareceres_cache",
        timestamp_key="df_alteracoes_pareceres_cache_timestamp",
    )


def carregar_historico_homologacoes(
    forcar_atualizacao: bool = False,
) -> pd.DataFrame:
    return _carregar_worksheet_controlada(
        worksheet=WORKSHEET_HISTORICO_HOMOLOGACOES,
        colunas=COLUNAS_HISTORICO_HOMOLOGACOES,
        cache_key="df_historico_homologacoes_cache",
        timestamp_key="df_historico_homologacoes_cache_timestamp",
        forcar_atualizacao=forcar_atualizacao,
    )


def salvar_historico_homologacoes(df: pd.DataFrame) -> bool:
    return _salvar_worksheet_controlada(
        worksheet=WORKSHEET_HISTORICO_HOMOLOGACOES,
        df=df,
        colunas=COLUNAS_HISTORICO_HOMOLOGACOES,
        cache_key="df_historico_homologacoes_cache",
        timestamp_key="df_historico_homologacoes_cache_timestamp",
    )


def existe_alteracao_pendente(
    id_chamado,
    alcada: str,
    df_alteracoes: pd.DataFrame | None = None,
) -> bool:
    """Impede mais de uma solicitação pendente para chamado e alçada."""
    dados = (
        carregar_alteracoes_pareceres()
        if df_alteracoes is None
        else garantir_colunas_dataframe(
            df_alteracoes,
            COLUNAS_ALTERACOES_PARECERES,
        )
    )

    if dados.empty:
        return False

    ids = pd.to_numeric(dados["ID_Chamado"], errors="coerce")
    alvo = pd.to_numeric(pd.Series([id_chamado]), errors="coerce").iloc[0]
    alcadas = dados["Alcada"].astype(str).str.strip().str.lower()
    statuses = dados["Status_Alteracao"].astype(str).str.strip().str.lower()

    mascara = (
        ids.eq(alvo)
        & alcadas.eq(str(alcada).strip().lower())
        & statuses.eq(STATUS_ALTERACAO_PENDENTE.lower())
    )
    return bool(mascara.any())


def proxima_versao_homologacao(
    id_chamado,
    df_historico: pd.DataFrame | None = None,
) -> int:
    """Calcula a próxima versão administrativa sem sobrescrever o histórico."""
    dados = (
        carregar_historico_homologacoes()
        if df_historico is None
        else garantir_colunas_dataframe(
            df_historico,
            COLUNAS_HISTORICO_HOMOLOGACOES,
        )
    )

    if dados.empty:
        return 1

    ids = pd.to_numeric(dados["ID_Chamado"], errors="coerce")
    alvo = pd.to_numeric(pd.Series([id_chamado]), errors="coerce").iloc[0]
    versoes = pd.to_numeric(
        dados.loc[ids.eq(alvo), "Versao_Homologacao"],
        errors="coerce",
    ).dropna()

    return int(versoes.max()) + 1 if not versoes.empty else 1


def criar_registro_alteracao_parecer(
    *,
    id_chamado,
    alcada: str,
    coluna_parecer: str,
    decisao_anterior: str,
    parecer_anterior: str,
    decisao_solicitada: str,
    parecer_solicitado: str,
    justificativa: str,
    solicitante_nome: str,
    solicitante_email: str,
    origem_reabertura: str = "NÃO",
    id_reabertura: str = "",
) -> dict:
    """Monta um registro validado; a gravação será feita pela etapa de tela."""
    campos_obrigatorios = {
        "alçada": alcada,
        "nova decisão": decisao_solicitada,
        "justificativa": justificativa,
        "solicitante": solicitante_email,
    }
    ausentes = [nome for nome, valor in campos_obrigatorios.items() if not str(valor).strip()]
    if ausentes:
        raise ValueError(
            "Campos obrigatórios ausentes: " + ", ".join(ausentes)
        )

    return {
        "ID_Alteracao": gerar_id_registro("ALT"),
        "ID_Chamado": id_chamado,
        "Alcada": str(alcada).strip(),
        "Coluna_Parecer": str(coluna_parecer).strip(),
        "Decisao_Anterior": str(decisao_anterior).strip(),
        "Parecer_Anterior": str(parecer_anterior).strip(),
        "Decisao_Solicitada": str(decisao_solicitada).strip(),
        "Parecer_Solicitado": str(parecer_solicitado).strip(),
        "Justificativa_Alteracao": str(justificativa).strip(),
        "Solicitante_Nome": str(solicitante_nome).strip(),
        "Solicitante_Email": str(solicitante_email).strip().lower(),
        "Data_Solicitacao": _data_hora_registro(),
        "Status_Alteracao": STATUS_ALTERACAO_PENDENTE,
        "Admin_Responsavel": "",
        "Admin_Email": "",
        "Data_Analise": "",
        "Motivo_Recusa": "",
        "Origem_Reabertura": str(origem_reabertura).strip().upper(),
        "ID_Reabertura": str(id_reabertura).strip(),
    }


def extrair_decisao_e_parecer_registrado(valor_registrado) -> tuple[str, str]:
    """Separa a decisão principal do conteúdo descritivo armazenado na alçada."""
    texto = str(valor_registrado or "").strip()
    if not texto or texto.lower() in {"nan", "none", "pendente"}:
        return "Pendente", ""

    decisoes = ["Aprovar com ressalva", "Reprovar", "Aprovar"]
    decisao = next(
        (opcao for opcao in decisoes if texto.lower().startswith(opcao.lower())),
        texto.split("(", 1)[0].strip(),
    )

    parecer = ""
    if "(" in texto and texto.endswith(")"):
        conteudo = texto.split("(", 1)[1][:-1].strip()
        if ":" in conteudo:
            parecer = conteudo.split(":", 1)[1].strip()

    return decisao or texto, parecer


def chamado_esta_em_homologacao(row: pd.Series) -> bool:
    """Identifica processos que dependem de reabertura administrativa."""
    status_aprovadores = str(row.get("Status_Aprovadores", "")).strip().lower()
    status_final = str(row.get("Status_Final", "")).strip().lower()

    finalizado = status_final not in {"", "em análise", "em analise", "nan", "none"}
    aguardando_homologacao = status_aprovadores in {
        "aguardando homologação",
        "aguardando homologacao",
        "em homologação",
        "em homologacao",
    }
    return finalizado or aguardando_homologacao


def alcada_esta_liberada_para_revisao(row: pd.Series, label_alcada: str) -> bool:
    """Autoriza a revisão quando a homologação já foi formalmente reaberta."""
    status_revisao = str(row.get("Status_Revisao", "")).strip().lower()
    alcada_reaberta = str(row.get("Alcada_Reaberta", "")).strip().lower()
    label_normalizado = str(label_alcada).strip().lower()

    status_liberados = {
        STATUS_REVISAO_REABERTO.lower(),
        STATUS_REVISAO_AGUARDANDO_ALTERACAO.lower(),
    }
    return status_revisao in status_liberados and alcada_reaberta == label_normalizado


def adicionar_solicitacao_alteracao(registro: dict) -> bool:
    """Acrescenta uma solicitação à fila sem substituir o parecer oficial."""
    df_alteracoes = carregar_alteracoes_pareceres(forcar_atualizacao=True)

    if existe_alteracao_pendente(
        registro.get("ID_Chamado"),
        registro.get("Alcada", ""),
        df_alteracoes=df_alteracoes,
    ):
        return False

    novo_registro = pd.DataFrame([registro])
    dados_atualizados = pd.concat(
        [df_alteracoes, novo_registro],
        ignore_index=True,
    )
    return salvar_alteracoes_pareceres(dados_atualizados)


def criar_registro_historico_homologacao(
    *,
    id_chamado,
    status_final: str,
    parecer_final_admin: str,
    consideracoes_finais: str,
    admin_nome: str,
    admin_email: str,
    situacao_registro: str = "Vigente",
    motivo_reabertura: str = "",
    alcada_reaberta: str = "",
    data_reabertura: str = "",
    admin_reabertura: str = "",
    email_admin_reabertura: str = "",
    df_historico: pd.DataFrame | None = None,
) -> dict:
    """Cria uma versão imutável da homologação para auditoria futura."""
    return {
        "ID_Historico": gerar_id_registro("HOM"),
        "ID_Chamado": id_chamado,
        "Versao_Homologacao": proxima_versao_homologacao(
            id_chamado,
            df_historico=df_historico,
        ),
        "Status_Final": str(status_final).strip(),
        "Parecer_Final_Admin": str(parecer_final_admin).strip(),
        "Consideracoes_Finais": str(consideracoes_finais).strip(),
        "Admin_Nome": str(admin_nome).strip(),
        "Admin_Email": str(admin_email).strip().lower(),
        "Data_Homologacao": _data_hora_registro(),
        "Motivo_Reabertura": str(motivo_reabertura).strip(),
        "Alcada_Reaberta": str(alcada_reaberta).strip(),
        "Data_Reabertura": str(data_reabertura).strip(),
        "Admin_Reabertura": str(admin_reabertura).strip(),
        "Email_Admin_Reabertura": str(email_admin_reabertura).strip().lower(),
        "Situacao_Registro": str(situacao_registro).strip() or "Vigente",
    }


def salvar_base_principal_revisao(df_atualizado: pd.DataFrame) -> bool:
    """Salva a base principal e mantém o cache sincronizado."""
    try:
        dados = garantir_colunas_revisao_chamado(df_atualizado)
        conn.update(data=dados)
        st.session_state["df_dados_cache"] = dados.copy()
        st.session_state["df_dados_cache_timestamp"] = time.time()
        return True
    except Exception as erro:
        st.error(f"Não foi possível atualizar a base principal: {erro}")
        return False


def registrar_versao_atual_antes_reabertura(
    row: pd.Series,
    *,
    motivo_reabertura: str,
    alcada_reaberta: str,
    admin_nome: str,
    admin_email: str,
) -> bool:
    """Preserva uma decisão final existente antes de reabrir o processo."""
    status_final = str(row.get("Status_Final", "")).strip()
    if status_final.lower() in {"", "em análise", "em analise", "nan", "none"}:
        return True

    historico = carregar_historico_homologacoes(forcar_atualizacao=True)
    ids = pd.to_numeric(historico.get("ID_Chamado", pd.Series(dtype=float)), errors="coerce")
    alvo = pd.to_numeric(pd.Series([row.get("ID")]), errors="coerce").iloc[0]
    vigentes = historico[
        ids.eq(alvo)
        & historico.get("Situacao_Registro", pd.Series(index=historico.index, dtype=str))
        .astype(str).str.strip().str.lower().eq("vigente")
    ]

    # Evita registrar a mesma versão duas vezes em reexecuções do Streamlit.
    if not vigentes.empty:
        historico.loc[vigentes.index, "Situacao_Registro"] = "Substituída após reabertura"
    else:
        registro = criar_registro_historico_homologacao(
            id_chamado=row.get("ID"),
            status_final=status_final,
            parecer_final_admin=str(row.get("Parecer_Final_Admin", "")),
            consideracoes_finais=str(
                row.get(
                    "Consideracoes_Finais_Homologacao",
                    row.get("obs_admin", ""),
                )
            ),
            admin_nome=str(row.get("Responsavel_Homologacao_Final", "")),
            admin_email="",
            situacao_registro="Substituída após reabertura",
            motivo_reabertura=motivo_reabertura,
            alcada_reaberta=alcada_reaberta,
            data_reabertura=_data_hora_registro(),
            admin_reabertura=admin_nome,
            email_admin_reabertura=admin_email,
            df_historico=historico,
        )
        historico = pd.concat([historico, pd.DataFrame([registro])], ignore_index=True)

    return salvar_historico_homologacoes(historico)


def reabrir_chamado_para_revisao(
    *,
    id_chamado,
    alcada: str,
    motivo: str,
    admin_nome: str,
    admin_email: str,
) -> tuple[bool, str]:
    """Reabre formalmente um processo e libera uma única alçada para revisão."""
    if not str(alcada).strip() or not str(motivo).strip():
        return False, "Informe a alçada e o motivo da reabertura."

    dados = carregar_dados(forcar_atualizacao=True)
    if dados.empty or "ID" not in dados.columns:
        return False, "A base principal não está disponível."

    ids = pd.to_numeric(dados["ID"], errors="coerce")
    alvo = pd.to_numeric(pd.Series([id_chamado]), errors="coerce").iloc[0]
    indices = dados.index[ids.eq(alvo)].tolist()
    if not indices:
        return False, f"Chamado #{id_chamado} não localizado."

    indice = indices[0]
    row = dados.loc[indice].copy()
    status_revisao = str(row.get("Status_Revisao", "")).strip().lower()
    if status_revisao in {
        STATUS_REVISAO_REABERTO.lower(),
        STATUS_REVISAO_AGUARDANDO_ALTERACAO.lower(),
        STATUS_REVISAO_ALTERACAO_EM_ANALISE.lower(),
    }:
        return False, "Este chamado já possui uma revisão técnica em andamento."

    if not registrar_versao_atual_antes_reabertura(
        row,
        motivo_reabertura=motivo,
        alcada_reaberta=alcada,
        admin_nome=admin_nome,
        admin_email=admin_email,
    ):
        return False, "Não foi possível preservar o histórico da homologação anterior."

    id_reabertura = gerar_id_registro("REAB")
    quantidade = pd.to_numeric(
        pd.Series([row.get("Quantidade_Reaberturas", 0)]), errors="coerce"
    ).fillna(0).iloc[0]

    dados.at[indice, "Chamado_Reaberto"] = "SIM"
    dados.at[indice, "ID_Reabertura_Atual"] = id_reabertura
    dados.at[indice, "Motivo_Reabertura"] = str(motivo).strip()
    dados.at[indice, "Alcada_Reaberta"] = str(alcada).strip()
    dados.at[indice, "Admin_Reabertura"] = str(admin_nome).strip()
    dados.at[indice, "Email_Admin_Reabertura"] = str(admin_email).strip().lower()
    dados.at[indice, "Data_Reabertura"] = _data_hora_registro()
    dados.at[indice, "Status_Revisao"] = STATUS_REVISAO_AGUARDANDO_ALTERACAO
    dados.at[indice, "Quantidade_Reaberturas"] = int(quantidade) + 1
    dados.at[indice, "Retornou_Homologacao_Apos_Revisao"] = "NÃO"
    dados.at[indice, "Status_Aprovadores"] = "Reaberto para revisão técnica"
    dados.at[indice, "Status_Final"] = "Em análise"

    # A decisão anterior já foi preservada na aba histórica.
    for coluna in [
        "Parecer_Final_Admin",
        "Data_Homologacao_Final",
        "Responsavel_Homologacao_Final",
        "Consideracoes_Finais_Homologacao",
        "obs_admin",
    ]:
        if coluna in dados.columns:
            dados.at[indice, coluna] = ""

    if not salvar_base_principal_revisao(dados):
        return False, "A reabertura não pôde ser gravada na base principal."

    return True, id_reabertura


def _normalizar_decisao_planilha(decisao: str) -> str:
    """Converte rótulos administrativos para o padrão usado nas colunas das alçadas."""
    valor = str(decisao or "").strip().lower()
    mapa = {
        "aprovar": "Aprovar",
        "aprovado": "Aprovar",
        "aprovar com ressalva": "Aprovar com ressalva",
        "aprovado com ressalva": "Aprovar com ressalva",
        "reprovar": "Reprovar",
        "reprovado": "Reprovar",
    }
    return mapa.get(valor, str(decisao or "").strip())


def _montar_parecer_revisado(*, decisao: str, parecer: str, aprovador_nome: str, admin_nome: str, id_alteracao: str) -> str:
    """Monta o conteúdo oficial preservando autoria e validação administrativa."""
    decisao_padrao = _normalizar_decisao_planilha(decisao)
    momento = _data_hora_registro()
    parecer_limpo = str(parecer or "").strip().replace("\n", " ")
    autoria = str(aprovador_nome or "Aprovador").strip()
    validador = str(admin_nome or "Administrador").strip()
    metadados = f"{momento} - {autoria}; alteração confirmada por {validador}; protocolo {id_alteracao}"
    if parecer_limpo:
        return f"{decisao_padrao} ({metadados}: {parecer_limpo})"
    return f"{decisao_padrao} ({metadados})"


def _recalcular_status_tecnico(row: pd.Series) -> tuple[str, int, int]:
    """Aplica a mesma matriz usada no parecer inicial."""
    votos = []
    for info in ALCADAS_INFO.values():
        coluna = info.get("coluna_sheets", "")
        if coluna and coluna in row.index:
            votos.append(str(row.get(coluna, "")).strip())
    reprovados = sum(1 for voto in votos if voto.lower().startswith("reprovar"))
    emitidos = sum(1 for voto in votos if voto.lower().startswith(("aprovar", "reprovar")))
    if reprovados > 0:
        status = "Reunião Necessária"
    elif emitidos == len(ALCADAS_INFO):
        status = "Aguardando homologação"
    else:
        status = "Em deliberação"
    return status, emitidos, reprovados


def _enviar_email_resultado_alteracao(*, registro: pd.Series, confirmado: bool, admin_nome: str, motivo_recusa: str = "", status_tecnico: str = "") -> None:
    """Notifica o aprovador e os administradores sobre o resultado."""
    destinatario = str(registro.get("Solicitante_Email", "")).strip().lower()
    id_chamado = registro.get("ID_Chamado", "")
    alcada = str(registro.get("Alcada", "")).strip()
    decisao_nova = str(registro.get("Decisao_Solicitada", "")).strip()
    protocolo = str(registro.get("ID_Alteracao", ""))
    if confirmado:
        titulo = f"Alteração de parecer confirmada · Chamado #{id_chamado}"
        mensagem = f"A alteração da alçada <b>{escape(alcada)}</b> foi confirmada por <b>{escape(str(admin_nome))}</b> e já substituiu o parecer vigente."
        detalhes = (
            '<div style="margin-top:18px;padding:16px;background:#f3f8f5;border-left:4px solid #008D4C;border-radius:5px;">'
            f'<p style="margin:0 0 7px;"><b>Nova decisão:</b> {escape(decisao_nova)}</p>'
            f'<p style="margin:0 0 7px;"><b>Status técnico:</b> {escape(status_tecnico)}</p>'
            f'<p style="margin:0;"><b>Protocolo:</b> {escape(protocolo)}</p></div>'
        )
        destaque = "#008D4C"
    else:
        titulo = f"Alteração de parecer recusada · Chamado #{id_chamado}"
        mensagem = f"A solicitação da alçada <b>{escape(alcada)}</b> foi recusada. O parecer vigente foi preservado."
        detalhes = (
            '<div style="margin-top:18px;padding:16px;background:#fff8f1;border-left:4px solid #E6A23C;border-radius:5px;">'
            f'<p style="margin:0 0 7px;"><b>Motivo:</b> {escape(str(motivo_recusa))}</p>'
            f'<p style="margin:0;"><b>Protocolo:</b> {escape(protocolo)}</p></div>'
        )
        destaque = "#E6A23C"
    html = template_email_caproq(titulo=titulo, mensagem=mensagem, detalhes=detalhes, destaque=destaque)
    if "@" in destinatario:
        enviar_email(destinatario, f"CAPROQ: {titulo}", html)
    if confirmado:
        for email_admin in emails_unicos(ADMINS):
            if email_admin != destinatario:
                enviar_email(email_admin, f"CAPROQ: {titulo}", html)


def analisar_solicitacao_alteracao(*, id_alteracao: str, decisao_admin: str, admin_nome: str, admin_email: str, motivo_recusa: str = "") -> tuple[bool, str]:
    """Analisa e aplica oficialmente a alteração quando confirmada."""
    alteracoes = carregar_alteracoes_pareceres(forcar_atualizacao=True)
    if alteracoes.empty:
        return False, "A solicitação de alteração não foi localizada."
    mascara = alteracoes["ID_Alteracao"].astype(str).str.strip().eq(str(id_alteracao).strip())
    indices = alteracoes.index[mascara].tolist()
    if not indices:
        return False, "A solicitação de alteração não foi localizada."
    indice = indices[0]
    registro = alteracoes.loc[indice].copy()
    status_atual = str(registro.get("Status_Alteracao", "")).strip()
    if status_atual.lower() != STATUS_ALTERACAO_PENDENTE.lower():
        return False, f"Esta solicitação já foi analisada ({status_atual})."
    confirmar = str(decisao_admin).strip().lower() == "confirmar"
    if not confirmar and not str(motivo_recusa).strip():
        return False, "Informe o motivo da recusa."

    dados = carregar_dados(forcar_atualizacao=True)
    if dados.empty or "ID" not in dados.columns:
        return False, "A base principal não está disponível."
    id_chamado = registro.get("ID_Chamado")
    ids = pd.to_numeric(dados["ID"], errors="coerce")
    alvo = pd.to_numeric(pd.Series([id_chamado]), errors="coerce").iloc[0]
    indices_chamado = dados.index[ids.eq(alvo)].tolist()
    if not indices_chamado:
        return False, f"Chamado #{id_chamado} não localizado na base principal."
    idx = indices_chamado[0]
    coluna_parecer = str(registro.get("Coluna_Parecer", "")).strip()
    if confirmar and (not coluna_parecer or coluna_parecer not in dados.columns):
        return False, "A coluna da alçada não foi localizada na base principal."

    dados_antes = dados.copy()
    alteracoes_antes = alteracoes.copy()
    agora = _data_hora_registro()
    status_tecnico = str(dados.at[idx, "Status_Aprovadores"] if "Status_Aprovadores" in dados.columns else "")

    if confirmar:
        nova_decisao = _normalizar_decisao_planilha(registro.get("Decisao_Solicitada", ""))
        novo_parecer = str(registro.get("Parecer_Solicitado", "")).strip()
        if nova_decisao in {"Aprovar com ressalva", "Reprovar"} and not novo_parecer:
            return False, "O novo parecer descritivo é obrigatório para esta decisão."
        dados.at[idx, coluna_parecer] = _montar_parecer_revisado(decisao=nova_decisao, parecer=novo_parecer, aprovador_nome=str(registro.get("Solicitante_Nome", "")), admin_nome=admin_nome, id_alteracao=id_alteracao)
        status_tecnico, _, _ = _recalcular_status_tecnico(dados.loc[idx])
        dados.at[idx, "Status_Aprovadores"] = status_tecnico
        retornou = status_tecnico in {"Aguardando homologação", "Reunião Necessária"}
        dados.at[idx, "Status_Revisao"] = STATUS_REVISAO_RETORNADO_HOMOLOGACAO if retornou else STATUS_REVISAO_ALTERACAO_CONFIRMADA
        dados.at[idx, "Retornou_Homologacao_Apos_Revisao"] = "SIM" if retornou else "NÃO"
        dados.at[idx, "Chamado_Reaberto"] = "NÃO"
        dados.at[idx, "Status_Final"] = "Em análise"
        if not salvar_base_principal_revisao(dados):
            return False, "O parecer oficial não pôde ser atualizado."
        novo_status = STATUS_ALTERACAO_CONFIRMADA
    else:
        if str(dados.at[idx, "Chamado_Reaberto"]).strip().upper() == "SIM":
            dados.at[idx, "Status_Revisao"] = STATUS_REVISAO_AGUARDANDO_ALTERACAO
        else:
            dados.at[idx, "Status_Revisao"] = STATUS_REVISAO_NAO_APLICAVEL
        if not salvar_base_principal_revisao(dados):
            return False, "Não foi possível atualizar o controle da revisão."
        novo_status = STATUS_ALTERACAO_RECUSADA

    alteracoes.at[indice, "Status_Alteracao"] = novo_status
    alteracoes.at[indice, "Admin_Responsavel"] = str(admin_nome).strip()
    alteracoes.at[indice, "Admin_Email"] = str(admin_email).strip().lower()
    alteracoes.at[indice, "Data_Analise"] = agora
    alteracoes.at[indice, "Motivo_Recusa"] = "" if confirmar else str(motivo_recusa).strip()
    if not salvar_alteracoes_pareceres(alteracoes):
        salvar_base_principal_revisao(dados_antes)
        salvar_alteracoes_pareceres(alteracoes_antes)
        return False, "Não foi possível concluir o registro de auditoria; a operação foi revertida."

    _enviar_email_resultado_alteracao(registro=alteracoes.loc[indice], confirmado=confirmar, admin_nome=admin_nome, motivo_recusa=motivo_recusa, status_tecnico=status_tecnico)
    return True, novo_status

def carregar_dados(forcar_atualizacao=False):
    try:
        agora = time.time()

        cache_existe = "df_dados_cache" in st.session_state
        horario_cache = st.session_state.get(
            "df_dados_cache_timestamp",
            0
        )

        cache_valido = (
            cache_existe
            and not forcar_atualizacao
            and (agora - horario_cache) < 60
        )

        if cache_valido:
            return st.session_state["df_dados_cache"].copy()

        df = conn.read(ttl=60)
        df = df.dropna(how="all")
        df = garantir_colunas_revisao_chamado(df)

        if not df.empty and "ID" in df.columns:
            df["ID"] = pd.to_numeric(
                df["ID"],
                errors="coerce"
            )

            df = df.dropna(subset=["ID"])
            df["ID"] = df["ID"].astype(int)

        colunas_textuais = [
            "Status_Final",
            "Status_Aprovadores",
            "Parecer_Final_Admin",
            "Data_Homologacao_Final",
            "Responsavel_Homologacao_Final",
            "Consideracoes_Finais_Homologacao",
            "RMS_Produto",
            "Validade_RMS",
            "Pode_Ser_Rediluido",
            "Necessita_Monitoramento_Ocupacional",
            "Resultado_Teste",
            "Data_Resultado_Teste",
            "Parecer_Resultado_Teste",
            "Indicado_Para_Padronizacao",
            "Data_Indicacao_Padronizacao",
            "Parecer_Indicacao_Padronizacao",
        ]

        for coluna in colunas_textuais:
            if coluna in df.columns:
                df[coluna] = df[coluna].astype("object")

        st.session_state["df_dados_cache"] = df.copy()
        st.session_state["df_dados_cache_timestamp"] = agora

        return df

    except Exception as e:
        st.error(
            f"Erro ao conectar com a planilha de dados: {e}"
        )

        if "df_dados_cache" in st.session_state:
            st.warning(
                "⚠️ A planilha não pôde ser atualizada agora. "
                "Os últimos dados carregados serão utilizados."
            )
            return st.session_state["df_dados_cache"].copy()

        return pd.DataFrame()

# --- 3.2. CARREGAMENTO DINÂMICO DE USUÁRIOS E PERMISSÕES (Aba 'Usuarios') ---
def carregar_dados_usuarios(forcar_atualizacao=False):
    try:
        agora = time.time()

        cache_existe = "df_usuarios_cache" in st.session_state
        horario_cache = st.session_state.get(
            "df_usuarios_cache_timestamp",
            0
        )

        cache_valido = (
            cache_existe
            and not forcar_atualizacao
            and (agora - horario_cache) < 60
        )

        if cache_valido:
            return st.session_state["df_usuarios_cache"].copy()

        df = conn.read(
            worksheet="Usuarios",
            ttl=60
        )

        df = df.dropna(how="all")

        if not df.empty:
            if "Email" in df.columns:
                df["Email"] = (
                    df["Email"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )

            if "Ativo" in df.columns:
                df["Ativo"] = (
                    df["Ativo"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                )

            if "Admin" in df.columns:
                df["Admin"] = (
                    df["Admin"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                )

        st.session_state["df_usuarios_cache"] = df.copy()
        st.session_state["df_usuarios_cache_timestamp"] = agora

        return df

    except Exception as e:
        if "df_usuarios_cache" in st.session_state:
            st.warning(
                "⚠️ Não foi possível atualizar a lista de usuários agora. "
                "Os últimos dados carregados serão utilizados."
            )

            return st.session_state["df_usuarios_cache"].copy()

        st.error(
            "Erro ao conectar com a tabela de usuários: "
            f"{e}"
        )

        return pd.DataFrame()

df_usuarios = carregar_dados_usuarios()

if "user_nome" not in st.session_state:
    st.session_state["user_nome"] = "Novo Solicitante"
if "user_perfil" not in st.session_state:
    st.session_state["user_perfil"] = "Solicitante"
if "user_alcadas" not in st.session_state:
    st.session_state["user_alcadas"] = []
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "user_ativo" not in st.session_state:
    st.session_state["user_ativo"] = True
if "usuario_cadastrado" not in st.session_state:
    st.session_state["usuario_cadastrado"] = False
if "usuario_validado" not in st.session_state:
    st.session_state["usuario_validado"] = False
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "solicitacoes"

def validar_usuario_logado(email_usuario):
    email_usuario = str(email_usuario or "").strip().lower()

    if not email_usuario:
        return False, "Não foi possível identificar o e-mail da conta Google."

    # Todo usuário autenticado entra, por padrão, como solicitante.
    st.session_state["user_nome"] = (
        st.session_state.get("name")
        or email_usuario.split("@")[0]
        or "Solicitante"
    )
    st.session_state["user_perfil"] = "Solicitante"
    st.session_state["user_alcadas"] = []
    st.session_state["is_admin"] = False
    st.session_state["user_ativo"] = True
    st.session_state["usuario_cadastrado"] = False
    st.session_state["usuario_validado"] = True

    # A aba Usuarios controla apenas permissões especiais e bloqueios.
    if df_usuarios.empty or "Email" not in df_usuarios.columns:
        return True, ""

    usuario_encontrado = df_usuarios[
        df_usuarios["Email"].astype(str).str.strip().str.lower()
        == email_usuario
    ]

    if usuario_encontrado.empty:
        return True, ""

    usuario_info = usuario_encontrado.iloc[0]
    usuario_ativo = (
        str(usuario_info.get("Ativo", "Sim")).strip().lower() == "sim"
    )

    if not usuario_ativo:
        st.session_state["user_ativo"] = False
        return False, "Seu usuário está inativo no sistema."

    nome_planilha = str(usuario_info.get("Nome", "")).strip()
    perfil_planilha = str(
        usuario_info.get("Perfil", "Solicitante")
    ).strip()
    admin_planilha = (
        str(usuario_info.get("Admin", "Não")).strip().lower() == "sim"
    )
    alcadas_raw = str(usuario_info.get("Alcada", "Nenhum")).strip()

    if alcadas_raw and alcadas_raw.lower() not in {"nenhum", "nenhuma"}:
        lista_alcadas = [
            alcada.strip()
            for alcada in alcadas_raw.split(",")
            if alcada.strip()
        ]
    else:
        lista_alcadas = []

    st.session_state["user_nome"] = (
        nome_planilha or st.session_state.get("name") or "Usuário"
    )
    st.session_state["user_perfil"] = perfil_planilha or "Solicitante"
    st.session_state["user_alcadas"] = lista_alcadas
    st.session_state["is_admin"] = admin_planilha
    st.session_state["user_ativo"] = True
    st.session_state["usuario_cadastrado"] = True
    st.session_state["usuario_validado"] = True

    return True, ""


def usuario_eh_admin():
    return bool(st.session_state.get("is_admin", False))


def usuario_eh_aprovador():
    return bool(st.session_state.get("user_alcadas", []))


def usuario_tem_alcada(alcada):
    alcada_normalizada = str(alcada or "").strip().lower()
    alcadas_usuario = {
        str(item).strip().lower()
        for item in st.session_state.get("user_alcadas", [])
    }
    return usuario_eh_admin() or alcada_normalizada in alcadas_usuario


def exigir_login():
    if not st.session_state.get("connected", False):
        st.error("Sua sessão não está autenticada.")
        st.stop()


def exigir_admin():
    exigir_login()
    if not usuario_eh_admin():
        st.error("Você não possui permissão para acessar esta área.")
        st.stop()


def exigir_aprovador():
    exigir_login()
    if not (usuario_eh_aprovador() or usuario_eh_admin()):
        st.error("Esta área está disponível somente para aprovadores.")
        st.stop()

ADMINS = []
APROVADORES = []

mapa_emails_alcadas = {
    "Padronização (suprimentos)": [],
    "Segurança Ocupacional": [],
    "Saúde Ocupacional": [],
    "SCI": [],
    "Engenharia Clínica e Eletromecânica": [],
    "Gestão Ambiental": [],
    "Prevenção de Incêndio": []
}

if not df_usuarios.empty:
    df_ativos = df_usuarios[df_usuarios["Ativo"].astype(str).str.strip().str.lower() == "sim"]
    
    ADMINS = df_ativos[df_ativos["Admin"].astype(str).str.strip().str.lower() == "sim"]["Email"].str.lower().tolist()
    
    for _, row in df_ativos.iterrows():
        email_u = str(row.get("Email", "")).strip().lower()
        perfil_u = str(row.get("Perfil", "")).strip()
        alcadas_u = str(row.get("Alcada", "Nenhum")).strip()
        
        if perfil_u == "Aprovador" and alcadas_u.lower() != "nenhum":
            lista_alcadas_usuario = [a.strip() for a in alcadas_u.split(",")]
            for alc in lista_alcadas_usuario:
                if alc in mapa_emails_alcadas:
                    mapa_emails_alcadas[alc].append(email_u)
                    
            APROVADORES.append(email_u)

    APROVADORES = list(set(ADMINS + APROVADORES))

ALCADAS_INFO = {
    "V": {
        "coluna_sheets": "Padronização (suprimentos)",
        "label": "Padronização (Suprimentos)",
        "prazo_util": 7,
        "emails": mapa_emails_alcadas["Padronização (suprimentos)"] if mapa_emails_alcadas["Padronização (suprimentos)"] else ADMINS
    },
    "W": {
        "coluna_sheets": "Segurança Ocupacional (prazo de análise: 7 dias úteis)",
        "label": "Segurança Ocupacional",
        "prazo_util": 7,
        "emails": mapa_emails_alcadas["Segurança Ocupacional"] if mapa_emails_alcadas["Segurança Ocupacional"] else ADMINS
    },
    "X": {
        "coluna_sheets": "Saúde Ocupacional (prazo de análise: 7 dias úteis)",
        "label": "Saúde Ocupacional",
        "prazo_util": 7,
        "emails": mapa_emails_alcadas["Saúde Ocupacional"] if mapa_emails_alcadas["Saúde Ocupacional"] else ADMINS
    },
    "Y": {
        "coluna_sheets": "SCI (prazo de análise: 5 dias úteis)",
        "label": "SCI",
        "prazo_util": 5,
        "emails": mapa_emails_alcadas["SCI"] if mapa_emails_alcadas["SCI"] else ADMINS
    },
    "Z": {
        "coluna_sheets": "Engenharia clínica e eletromecânica (Prazo de análise: 5 dias úteis)",
        "label": "Engenharia Clínica e Eletromecânica",
        "prazo_util": 5,
        "emails": mapa_emails_alcadas["Engenharia Clínica e Eletromecânica"] if mapa_emails_alcadas["Engenharia Clínica e Eletromecânica"] else ADMINS
    },
    "AA": {
        "coluna_sheets": "Gestão Ambiental (prazo de análise: 5 dias úteis)",
        "label": "Gestão Ambiental",
        "prazo_util": 5,
        "emails": mapa_emails_alcadas["Gestão Ambiental"] if mapa_emails_alcadas["Gestão Ambiental"] else ADMINS
    },
    "AB": {
        "coluna_sheets": "Prevenção de Incêndio (prazo de análise: 5 dias úteis)",
        "label": "Prevenção de Incêndio",
        "prazo_util": 5,
        "emails": mapa_emails_alcadas["Prevenção de Incêndio"] if mapa_emails_alcadas["Prevenção de Incêndio"] else ADMINS
    }
}

def enviar_email(destinatario, assunto, corpo_html):
    remetente = st.secrets.get("SMTP_EMAIL", "")
    senha = st.secrets.get("SMTP_PASSWORD", "")
    if not remetente or not senha: return False
    try:
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.sendmail(remetente, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

def emails_unicos(valores):
    resultado = []
    vistos = set()
    for valor in valores:
        if isinstance(valor, (list, tuple, set)):
            itens = valor
        else:
            itens = [valor]
        for item in itens:
            email = str(item or "").strip().lower()
            if "@" in email and email not in vistos:
                vistos.add(email)
                resultado.append(email)
    return resultado

def todos_emails_aprovadores():
    emails = []
    for info in ALCADAS_INFO.values():
        emails.extend(info.get("emails", []))
    return emails_unicos(emails)
    
def bloco_botoes_arquivos(link_fds="", link_anexos=""):
    botoes = []

    def adicionar_botao(rotulo, url, cor="#005691"):
        url_limpa = str(url or "").strip()

        valores_vazios = {
            "",
            "nan",
            "none",
            "não aplicável",
            "nenhum arquivo anexado",
            "nenhum arquivo adicional",
        }

        if url_limpa.lower() in valores_vazios:
            return

        botoes.append(
            f'<a href="{url_limpa}" target="_blank" '
            f'style="display:inline-block;background:{cor};color:#ffffff;'
            'text-decoration:none;padding:11px 18px;border-radius:6px;'
            f'font-weight:600;margin:6px 8px 0 0;">{rotulo}</a>'
        )

    adicionar_botao(
        "Abrir FDS",
        link_fds,
        "#005691",
    )

    adicionar_botao(
        "Abrir arquivos anexados",
        link_anexos,
        "#3f6f8f",
    )

    if not botoes:
        return ""

    return (
        '<div style="margin-top:20px;padding-top:16px;'
        'border-top:1px solid #e8ecef;">'
        '<div style="font-size:14px;font-weight:700;'
        'color:#37474f;margin-bottom:4px;">'
        'Documentos do chamado'
        "</div>"
        + "".join(botoes)
        + "</div>"
    )

def template_email_caproq(titulo, mensagem, detalhes="", destaque="#005691", botao=True):
    url_app = "https://formulariocompras.streamlit.app"
    bloco_botao = ""
    if botao:
        bloco_botao = f"""
        <div style="margin-top:24px;">
            <a href="{url_app}" target="_blank"
               style="display:inline-block;background:#005691;color:#ffffff;
                      text-decoration:none;padding:11px 18px;border-radius:6px;
                      font-weight:600;">Acessar CAPROQ</a>
        </div>
        """

    return f"""
    <div style="background:#f4f6f8;padding:24px;font-family:Arial,sans-serif;color:#263238;">
      <div style="max-width:680px;margin:0 auto;background:#ffffff;border:1px solid #e2e7eb;
                  border-radius:10px;overflow:hidden;">
        <div style="background:#005691;padding:20px 24px;">
          <div style="color:#ffffff;font-size:13px;letter-spacing:.6px;font-weight:700;">
            HOSPITAL MOINHOS DE VENTO · CAPROQ
          </div>
        </div>
        <div style="padding:26px 28px;">
          <h2 style="color:{destaque};font-size:21px;margin:0 0 16px;">{titulo}</h2>
          <div style="font-size:15px;line-height:1.6;">{mensagem}</div>
          {detalhes}
          {bloco_botao}
        </div>
        <div style="border-top:1px solid #e8ecef;padding:15px 28px;color:#6c757d;
                    font-size:12px;text-align:center;">
          Mensagem automática do CAPROQ. Não responda a este e-mail.
        </div>
      </div>
    </div>
    """

# ==============================================================================
# 4. Configurações de login Google          
# ==============================================================================
if "connected" not in st.session_state:
    st.session_state.connected = False


client_config = {
    "web": {
        "client_id": st.secrets.get(
            "GOOGLE_CLIENT_ID",
            "",
        ),
        "client_secret": st.secrets.get(
            "GOOGLE_CLIENT_SECRET",
            "",
        ),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [
            st.secrets.get(
                "GOOGLE_REDIRECT_URI",
                "",
            )
        ],
    }
}


query_params = st.query_params

if (
    "code" in query_params
    and not st.session_state.get("connected", False)
):
    try:
        codigo_google = query_params["code"]

        if isinstance(codigo_google, list):
            codigo_google = codigo_google[0]

        flow = Flow.from_client_config(
            client_config,
            scopes=[
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
                "openid",
                "https://www.googleapis.com/auth/drive.file",
            ],
            redirect_uri=st.secrets["GOOGLE_REDIRECT_URI"],
        )

        flow.fetch_token(
            code=codigo_google
        )

        credentials = flow.credentials

        st.session_state[
            "google_credentials"
        ] = credentials

        user_info_service = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={
                "Authorization": (
                    f"Bearer {credentials.token}"
                )
            },
            timeout=20,
        ).json()

        st.session_state.connected = True
        st.session_state.name = (
            user_info_service.get("name")
        )
        st.session_state.email = (
            user_info_service.get("email")
        )
        st.session_state.picture = (
            user_info_service.get("picture")
        )

        st.query_params.clear()
        st.rerun()

    except Exception as erro:
        st.session_state[
            "erro_login_google"
        ] = (
            f"{type(erro).__name__}: {erro}"
        )

        st.session_state.connected = False
        st.session_state.pop(
            "google_credentials",
            None,
        )

        st.query_params.clear()
        st.rerun()

# ==============================================================================
# 5. Confirgurações tela de Login                     
# ==============================================================================
if not st.session_state.connected:
    ui.load_login_css()

    auth_url = (
        "https://accounts.google.com/o/oauth2/auth?"
        "response_type=code"
        f"&client_id={st.secrets.get('GOOGLE_CLIENT_ID', '')}"
        f"&redirect_uri={st.secrets.get('GOOGLE_REDIRECT_URI', '')}"
        "&scope="
        "https://www.googleapis.com/auth/userinfo.profile"
        "%20https://www.googleapis.com/auth/userinfo.email"
        "%20openid"
        "%20https://www.googleapis.com/auth/drive.file"
        "&prompt=select_account"
    )

    erro_login = st.session_state.pop(
        "erro_login_google",
        None,
    )

    if erro_login:
        ui.render_feedback("Tente novamente. Caso o problema persista, consulte os detalhes técnicos abaixo.", kind="error", title="Não foi possível concluir o login com o Google", icon="🔐")

        with st.expander("Detalhes técnicos"):
            st.code(erro_login)

    logo_html = ""

    if os.path.exists("logomoinhos.png"):
        with open("logomoinhos.png", "rb") as arquivo_logo:
            logo_base64 = base64.b64encode(
                arquivo_logo.read()
            ).decode("utf-8")

        logo_html = f"""
        <div class="login-logo-wrap">
            <img
                src="data:image/png;base64,{logo_base64}"
                alt="Hospital Moinhos de Vento"
                class="login-logo-image"
            >
        </div>
        """

    auth_url_html = auth_url

    login_html = f"""
<div class="login-shell">
    <div class="login-premium-grid">

        <div class="login-brand-panel">
            <div>
                <p class="login-brand-kicker">
                    Hospital Moinhos de Vento
                </p>

                <h1 class="login-brand-title">
                    CAPROQ
                </h1>

                <p class="login-brand-text">
                    Plataforma para solicitação, análise técnica,
                    acompanhamento e padronização de produtos químicos.
                </p>
            </div>

            <div class="login-brand-footer">
                Processo integrado de avaliação por alçadas técnicas
            </div>
        </div>

        <div class="login-access-panel">
            {logo_html}

            <h2 class="login-access-title">
                Acesse sua conta
            </h2>

            <p class="login-access-subtitle">
                Entre com sua conta Google para registrar solicitações
                e acompanhar o fluxo de avaliação.
            </p>

            <a
                class="login-google-button"
                href="{auth_url_html}"
                target="_blank" rel="noopener noreferrer"
            >
                Continuar com o Google
            </a>

            <div class="login-security-note">
                <strong>Acesso seguro</strong><br>
                Usuários não cadastrados entram automaticamente como
                solicitantes. Permissões adicionais são carregadas
                conforme a aba de usuários.
            </div>
        </div>

    </div>
</div>
"""

    st.html(login_html)

    st.stop()

usuario_valido, mensagem_validacao = validar_usuario_logado(
    st.session_state.get("email", "")
)

if not usuario_valido:
    ui.render_feedback(mensagem_validacao, kind="error", title="Acesso indisponível", icon="🔒")
    ui.render_feedback("Entre em contato com a administração do CAPROQ caso seja necessário reativar seu acesso.", kind="info", title="Como resolver", icon="📩")

    if st.button(
        "Voltar para o login",
        use_container_width=True,
        key="voltar_login_usuario_inativo",
    ):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

    st.stop()

exigir_login()

usuario_privilegiado = (
    usuario_eh_aprovador()
    or usuario_eh_admin()
)

if (
    usuario_privilegiado
    and st.session_state.get("pagina_atual") == "solicitacoes"
):
    st.session_state["pagina_atual"] = "painel_principal"

if "pagina_atual" not in st.session_state:

    if usuario_eh_admin() or usuario_eh_aprovador():
        st.session_state["pagina_atual"] = "painel_principal"

    else:
        st.session_state["pagina_atual"] = "solicitacoes"

pagina = st.session_state["pagina_atual"]

CAPROQ_SHEETS_URL = str(
    st.secrets.get("CAPROQ_SHEETS_URL", "")
).strip()

CAPROQ_DRIVE_URL = str(
    st.secrets.get("CAPROQ_DRIVE_URL", "")
).strip()

# ==============================================================================
# 6. Configurações da sidebar
# ==============================================================================
# ------------------------------------------------------------------------------
# Cabeçalho institucional
# ------------------------------------------------------------------------------

st.sidebar.markdown(
    """
<div class="sidebar-brand-card">
    <p class="sidebar-brand-kicker">Hospital Moinhos de Vento</p>
    <p class="sidebar-brand-title">CAPROQ</p>
    <p class="sidebar-brand-subtitle">
        Gestão e padronização de produtos químicos
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# Dados do usuário
# ------------------------------------------------------------------------------

user_name = (
    st.session_state.get("user_nome")
    or st.session_state.get("name")
    or "Usuário"
)

user_email = (
    st.session_state.get("email")
    or ""
)

user_picture = (
    st.session_state.get("picture")
    or "https://cdn-icons-png.flaticon.com/512/149/149071.png"
)

if usuario_eh_admin():
    perfil_usuario = "Administrador"
    icone_perfil = "🛡️"

elif usuario_eh_aprovador():
    perfil_usuario = "Aprovador"
    icone_perfil = "✅"

else:
    perfil_usuario = "Solicitante"
    icone_perfil = "👤"

user_name_safe = escape(str(user_name))
user_email_safe = escape(str(user_email))
user_picture_safe = escape(str(user_picture), quote=True)
perfil_usuario_safe = escape(str(perfil_usuario))

avatar_html = f"""
<div class="sidebar-user-card">
    <img
        class="sidebar-user-avatar"
        src="{user_picture_safe}"
        alt="Foto do usuário"
        onerror="this.onerror=null;this.src='https://cdn-icons-png.flaticon.com/512/149/149071.png';"
    >
    <div class="sidebar-user-info">
        <span class="sidebar-user-name">{user_name_safe}</span>
        <span class="sidebar-user-email">{user_email_safe}</span>
    </div>
</div>
<div class="sidebar-role-badge">
    {icone_perfil}&nbsp; {perfil_usuario_safe}
</div>
"""

st.sidebar.markdown(
    avatar_html,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# Navegação principal
# ------------------------------------------------------------------------------

st.sidebar.markdown(
    '<div class="sidebar-section-label">Navegação</div>',
    unsafe_allow_html=True,
)

# Tela exclusiva dos solicitantes
if not usuario_privilegiado:

    if st.sidebar.button(
        "📝 Nova solicitação",
        use_container_width=True,
        key="menu_solicitacoes",
    ):
        st.session_state["pagina_atual"] = "solicitacoes"
        st.rerun()

# Painel exclusivo dos aprovadores e administradores
if usuario_privilegiado:

    if st.sidebar.button(
        "📥 Painel de aprovações",
        use_container_width=True,
        key="menu_aprovacoes",
    ):
        st.session_state["pagina_atual"] = "painel_principal"
        st.rerun()

# ------------------------------------------------------------------------------
# Área administrativa
# ------------------------------------------------------------------------------

if usuario_eh_admin():

    st.sidebar.markdown(
        '<div class="sidebar-section-label">Administração</div>',
        unsafe_allow_html=True,
    )

    if st.sidebar.button(
        "🛡️ Homologação final",
        use_container_width=True,
        key="menu_homologacao",
    ):
        st.session_state["pagina_atual"] = "homologacao_final"
        st.rerun()

    if st.sidebar.button(
        "🔄 Alterações de parecer",
        use_container_width=True,
        key="menu_alteracoes_parecer",
    ):
        st.session_state["pagina_atual"] = "alteracoes_parecer_admin"
        st.rerun()

    if st.sidebar.button(
        "⚙️ Gerenciar aprovadores",
        use_container_width=True,
        key="menu_usuarios",
    ):
        st.session_state["pagina_atual"] = "gerenciar_aprovadores"
        st.rerun()

# ------------------------------------------------------------------------------
# Acessos externos
# ------------------------------------------------------------------------------

if usuario_privilegiado:

    st.sidebar.markdown(
        '<div class="sidebar-section-label">Acessos rápidos</div>',
        unsafe_allow_html=True,
    )

    if CAPROQ_SHEETS_URL:

        st.sidebar.link_button(
            "📊 Planilha do CAPROQ",
            CAPROQ_SHEETS_URL,
            use_container_width=True,
        )

    else:

        st.sidebar.button(
            "📊 Planilha não configurada",
            use_container_width=True,
            disabled=True,
            key="link_sheets_nao_configurado",
            help=(
                "Adicione CAPROQ_SHEETS_URL "
                "nos Secrets do aplicativo."
            ),
        )

    if CAPROQ_DRIVE_URL:

        st.sidebar.link_button(
            "📁 Pasta de documentos",
            CAPROQ_DRIVE_URL,
            use_container_width=True,
        )

# ------------------------------------------------------------------------------
# Rodapé e saída
# ------------------------------------------------------------------------------

st.sidebar.markdown(
    '<div class="sidebar-divider"></div>',
    unsafe_allow_html=True,
)

if st.sidebar.button(
    "🚪 Encerrar sessão",
    use_container_width=True,
    key="botao_sair_sidebar",
):
    st.session_state.pop(
        "google_credentials",
        None,
    )

    st.session_state.pop(
        "oauth_state",
        None,
    )

    st.session_state.pop(
        "google_auth_url",
        None,
    )

    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown(
    """
<div class="sidebar-footer">
    CAPROQ · Hospital Moinhos de Vento<br>
    Processo integrado de avaliação técnica
</div>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 7. Tela principal
# ==============================================================================
df_dados = carregar_dados()

user_email = st.session_state.get('email', '')
user_name = (
    st.session_state.get('user_nome')
    or st.session_state.get('name')
    or 'Usuário'
)
is_aprovador = usuario_eh_aprovador() or usuario_eh_admin()

col_header1, col_header2 = st.columns([1, 5])
if os.path.exists("logomoinhos.png"):
    col_header1.image("logomoinhos.png", width=150)

with col_header2:
    st.title("Solicitação de Padronização de Produtos Químicos - CAPROQ")
    st.markdown("<p style='color: #6c757d; font-size: 1.1em; margin-top: -15px;'>Fluxo de envio de solicitações para aprovação.</p>", unsafe_allow_html=True)

def valor_seguro(valor, padrao="Não informado"):
    if pd.isna(valor):
        return padrao

    valor_texto = str(valor).strip()

    if valor_texto.lower() in ["", "nan", "none"]:
        return padrao

    return valor_texto

# ==============================================================================
# 8. Tela aprovadores e Gerenciamento de Usuários (Ajustado cirurgicamente)
# ==============================================================================
if is_aprovador and st.session_state.get("pagina_atual") != "solicitacoes":
    exigir_aprovador()
    
    if st.session_state.get("is_admin", False) and st.session_state.get("pagina_atual") == "gerenciar_aprovadores":
        exigir_admin()


        df_usuarios = carregar_dados_usuarios()

        if not df_usuarios.empty:
            df_usuarios["Email"] = df_usuarios["Email"].astype(str).str.strip().str.lower()
            df_usuarios["Ativo"] = df_usuarios["Ativo"].astype(str).str.strip().str.upper()
            df_usuarios["Admin"] = df_usuarios["Admin"].astype(str).str.strip().str.upper()

        total_usuarios = len(df_usuarios) if not df_usuarios.empty else 0
        total_ativos = int((df_usuarios["Ativo"] == "SIM").sum()) if not df_usuarios.empty else 0
        total_admins = int((df_usuarios["Admin"] == "SIM").sum()) if not df_usuarios.empty else 0
        total_aprovadores = int((df_usuarios["Perfil"].astype(str).str.lower() == "aprovador").sum()) if not df_usuarios.empty and "Perfil" in df_usuarios.columns else 0

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Usuários cadastrados", total_usuarios)
        col_m2.metric("Usuários ativos", total_ativos)
        col_m3.metric("Aprovadores", total_aprovadores)
        col_m4.metric("Administradores", total_admins)

        st.markdown(
            """
<div class="caproq-admin-section">
    <h3>👥 Diretório de usuários</h3>
    <p>Visualize os cadastros existentes e confira rapidamente perfis, alçadas e situação de acesso.</p>
</div>
""",
            unsafe_allow_html=True,
        )

        if not df_usuarios.empty:
            col_busca, col_status, col_perfil = st.columns([2.2, 1, 1])
            with col_busca:
                busca_usuario = st.text_input(
                    "Buscar usuário",
                    placeholder="Nome ou e-mail",
                    key="busca_usuario_admin",
                )
            with col_status:
                filtro_status = st.selectbox(
                    "Status",
                    ["Todos", "Ativos", "Inativos"],
                    key="filtro_status_usuario_admin",
                )
            with col_perfil:
                perfis_disponiveis = sorted(
                    [p for p in df_usuarios.get("Perfil", pd.Series(dtype=str)).dropna().astype(str).unique() if p.strip()]
                )
                filtro_perfil = st.selectbox(
                    "Perfil",
                    ["Todos"] + perfis_disponiveis,
                    key="filtro_perfil_usuario_admin",
                )

            df_exibicao = df_usuarios.copy()
            if busca_usuario.strip():
                termo = busca_usuario.strip().lower()
                mascara_busca = (
                    df_exibicao["Email"].astype(str).str.lower().str.contains(termo, na=False)
                    | df_exibicao["Nome"].astype(str).str.lower().str.contains(termo, na=False)
                )
                df_exibicao = df_exibicao[mascara_busca]

            if filtro_status == "Ativos":
                df_exibicao = df_exibicao[df_exibicao["Ativo"] == "SIM"]
            elif filtro_status == "Inativos":
                df_exibicao = df_exibicao[df_exibicao["Ativo"] != "SIM"]

            if filtro_perfil != "Todos":
                df_exibicao = df_exibicao[df_exibicao["Perfil"].astype(str) == filtro_perfil]

            st.caption(f"Exibindo {len(df_exibicao)} de {total_usuarios} usuários.")
            st.dataframe(
                df_exibicao,
                column_config={
                    "Email": st.column_config.TextColumn("E-mail"),
                    "Nome": st.column_config.TextColumn("Nome completo"),
                    "Perfil": st.column_config.TextColumn("Perfil"),
                    "Alcada": st.column_config.TextColumn("Alçadas associadas"),
                    "Admin": st.column_config.TextColumn("Administrador"),
                    "Ativo": st.column_config.TextColumn("Ativo"),
                    "Data_Cadastro": st.column_config.TextColumn("Cadastro"),
                },
                use_container_width=True,
                hide_index=True,
            )
        else:
            ui.render_empty_state("Nenhum usuário cadastrado", "A aba Usuarios do Google Sheets ainda não possui registros. Use o formulário abaixo para incluir o primeiro usuário.", icon="👥")

        st.markdown(
            """
<div class="caproq-admin-section">
    <h3>⚙️ Ações administrativas</h3>
    <p>Cadastre, atualize ou remova usuários mantendo o controle centralizado no Google Sheets.</p>
</div>
""",
            unsafe_allow_html=True,
        )

        tab_salvar_usuario, tab_excluir_usuario = st.tabs([
            "➕ Cadastrar ou atualizar",
            "🗑️ Remover usuário",
        ])

        lista_alcadas_disponiveis = [
            ALCADAS_INFO[chave].get("label", chave) for chave in ALCADAS_INFO.keys()
        ]

        with tab_salvar_usuario:
            st.markdown(
                """
<div class="caproq-admin-note">
    <strong>Cadastro inteligente:</strong> quando o e-mail já existir, o registro será atualizado sem criar duplicidade.
</div>
""",
                unsafe_allow_html=True,
            )

            with st.form("form_usuario_sheets"):
                st.markdown("#### Identificação do usuário")
                col_ident1, col_ident2 = st.columns(2)
                with col_ident1:
                    email_input = st.text_input(
                        "E-mail do usuário *",
                        placeholder="nome@empresa.com.br",
                    ).strip().lower()
                with col_ident2:
                    nome_input = st.text_input(
                        "Nome completo *",
                        placeholder="Nome e sobrenome",
                    )

                st.markdown("#### Perfil e permissões")
                col_permissao1, col_permissao2, col_permissao3 = st.columns(3)
                with col_permissao1:
                    perfil_input = st.selectbox(
                        "Perfil de acesso",
                        ["Aprovador", "Solicitante", "Visualizador"],
                    )
                with col_permissao2:
                    is_admin_input = st.selectbox("Administrador", ["NÃO", "SIM"])
                with col_permissao3:
                    is_ativo_input = st.selectbox("Usuário ativo", ["SIM", "NÃO"])

                st.markdown("#### Alçadas técnicas")
                st.caption("Selecione somente as áreas pelas quais o usuário será responsável.")
                alcadas_selecionadas = []
                col_checkboxes = st.columns(2)
                for idx, nome_alcada in enumerate(lista_alcadas_disponiveis):
                    with col_checkboxes[idx % 2]:
                        if st.checkbox(nome_alcada, key=f"check_alcada_{nome_alcada}"):
                            alcadas_selecionadas.append(nome_alcada)

                botao_salvar_usr = st.form_submit_button(
                    "💾 Salvar usuário",
                    use_container_width=True,
                    type="primary",
                )

                if botao_salvar_usr:
                    if not email_input or "@" not in email_input:
                        ui.render_feedback("Informe um endereço de e-mail válido para identificar o usuário.", kind="error", title="E-mail inválido", icon="✉️")
                    elif not nome_input.strip():
                        ui.render_feedback("Preencha o nome do usuário antes de salvar o cadastro.", kind="error", title="Nome obrigatório", icon="👤")
                    else:
                        string_alcadas = ", ".join(alcadas_selecionadas) if alcadas_selecionadas else "Nenhuma"

                        fuso_br = datetime.timezone(datetime.timedelta(hours=-3))
                        data_atual_str = datetime.datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")

                        nova_linha = {
                            "Email": email_input,
                            "Nome": nome_input,
                            "Perfil": perfil_input,
                            "Alcada": string_alcadas,
                            "Admin": is_admin_input,
                            "Ativo": is_ativo_input,
                            "Data_Cadastro": data_atual_str,
                        }

                        if not df_usuarios.empty and email_input in df_usuarios["Email"].values:
                            idx_existente = df_usuarios[df_usuarios["Email"] == email_input].index[0]
                            for col, valor in nova_linha.items():
                                df_usuarios.at[idx_existente, col] = valor
                            msg_sucesso = f"🔄 Cadastro do usuário `{email_input}` atualizado com sucesso!"
                        else:
                            df_nova_linha = pd.DataFrame([nova_linha])
                            df_usuarios = pd.concat([df_usuarios, df_nova_linha], ignore_index=True)
                            msg_sucesso = f"🎉 Usuário `{email_input}` cadastrado com sucesso!"

                        try:
                            conn.update(worksheet="Usuarios", data=df_usuarios)
                            st.session_state["df_usuarios_cache"] = df_usuarios.copy()
                            st.session_state["df_usuarios_cache_timestamp"] = time.time()
                            ui.render_feedback(msg_sucesso, kind="success", title="Cadastro atualizado", icon="✅")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            ui.render_feedback(f"Não foi possível salvar os dados na aba Usuarios: {e}", kind="error", title="Falha ao salvar usuário", icon="💾")

        with tab_excluir_usuario:
            st.markdown(
                """
<div class="caproq-admin-danger">
    <strong>Atenção:</strong> a remoção apaga o registro da base do sistema. Para apenas bloquear o acesso, prefira atualizar o usuário como <strong>inativo</strong>.
</div>
""",
                unsafe_allow_html=True,
            )

            if not df_usuarios.empty:
                opcoes_exclusao = {
                    f"{valor_seguro(row.get('Nome'))} · {row.get('Email', '')}": row.get("Email", "")
                    for _, row in df_usuarios.iterrows()
                }
                with st.form("form_excluir_usuario"):
                    usuario_excluir_label = st.selectbox(
                        "Selecione o usuário para remover",
                        options=list(opcoes_exclusao.keys()),
                    )
                    email_excluir = opcoes_exclusao[usuario_excluir_label]
                    confirmar_exclusao = st.checkbox(
                        "Confirmo que desejo apagar permanentemente este registro."
                    )
                    botao_excluir_usr = st.form_submit_button(
                        "🗑️ Remover usuário",
                        use_container_width=True,
                    )

                    if botao_excluir_usr:
                        if not confirmar_exclusao:
                            ui.render_feedback("Marque a caixa de confirmação antes de remover o usuário.", kind="warning", title="Confirmação necessária", icon="☑️")
                        else:
                            df_usuarios = df_usuarios[df_usuarios["Email"] != email_excluir]
                            try:
                                conn.update(worksheet="Usuarios", data=df_usuarios)
                                st.session_state["df_usuarios_cache"] = df_usuarios.copy()
                                st.session_state["df_usuarios_cache_timestamp"] = time.time()
                                ui.render_feedback(f"O usuário {email_excluir} foi removido com sucesso.", kind="success", title="Usuário removido", icon="🗑️")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                ui.render_feedback(f"Não foi possível registrar a exclusão no Google Sheets: {e}", kind="error", title="Falha ao remover usuário", icon="🗑️")
            else:
                ui.render_empty_state("Nenhum usuário disponível", "Não há usuários cadastrados que possam ser removidos neste momento.", icon="👤")

    # --------------------------------------------------------------------------
    # PAINEL DE CONTROLE PRINCIPAL
    # --------------------------------------------------------------------------
    elif st.session_state.get("pagina_atual") == "painel_principal":
        st.markdown(
            """
<div class="caproq-page-hero">
    <p class="caproq-page-kicker">Central técnica · CAPROQ</p>
    <h1 class="caproq-page-title">Painel de Aprovações</h1>
    <p class="caproq-page-subtitle">
        Consulte solicitações, acompanhe o andamento das alçadas e registre
        decisões técnicas em um ambiente único e organizado.
    </p>
</div>
""",
            unsafe_allow_html=True,
        )
        
        colunas_permitidas_usuario = []
        is_user_admin = user_email in ADMINS
        
        for letra_col, info_alcada in ALCADAS_INFO.items():
            nome_coluna_sheets = info_alcada["coluna_sheets"]
            emails_alcada = info_alcada.get("emails", [])
            if not isinstance(emails_alcada, list):
                emails_alcada = [emails_alcada]
            if is_user_admin or user_email in emails_alcada:
                colunas_permitidas_usuario.append(nome_coluna_sheets)

        if not df_dados.empty:
            colunas_validas = [c for c in colunas_permitidas_usuario if c in df_dados.columns]
            
            if colunas_validas:
                condicao_pendente = (df_dados["Status_Final"] == "Em análise") & (
                    df_dados[colunas_validas].eq("Pendente").any(axis=1)
                )
                pendentes = df_dados[condicao_pendente]
                
                condicao_historico = df_dados[colunas_validas].apply(
                    lambda col: col.astype(str).str.startswith(("Aprovar", "Reprovar"), na=False)
                ).any(axis=1)
                
                historico_aprovador = df_dados[condicao_historico]
            else:
                pendentes = pd.DataFrame()
                historico_aprovador = pd.DataFrame()
            
            total_aprovados = len(
                df_dados[df_dados["Status_Final"] == "Aprovado"]
            )
            total_reprovados = len(
                df_dados[df_dados["Status_Final"] == "Reprovado"]
            )

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Pendências da sua área", len(pendentes))
            with m2:
                st.metric("Chamados aprovados", total_aprovados)
            with m3:
                st.metric("Chamados reprovados", total_reprovados)

            st.markdown(
                '<div class="caproq-panel-divider"></div>',
                unsafe_allow_html=True,
            )

            tab_pendentes, tab_hist_aprovador, tab_logs, tab_indicadores = st.tabs([
                "📥 Minhas pendências",
                "📋 Histórico de decisões",
                "🕒 Log de atividades",
                "📊 Indicadores",
            ])
            
            # ----------------------------------------------------------------------
            # 8.1. Aba "Minhas pendências"
            # ----------------------------------------------------------------------
            with tab_pendentes:

                st.markdown(
                    """
<div class="caproq-section-intro">
    <p class="caproq-section-intro-title">Solicitações aguardando seu parecer</p>
    <p class="caproq-section-intro-text">
        Abra um chamado para consultar os dados completos, acompanhar o placar
        das alçadas e registrar sua decisão técnica.
    </p>
</div>
""",
                    unsafe_allow_html=True,
                )

                if pendentes.empty:
                    ui.render_empty_state("Tudo em dia por aqui", "Não há solicitações pendentes para a sua alçada técnica neste momento.", icon="✅")
                else:
                    for _, row in pendentes.iterrows():
                        id_chamado = int(row["ID"])

                        # Identificação uniforme do produto
                        if "Descrição completa do produto" in row.index:
                            col_prod = "Descrição completa do produto"
                        elif "Descrição do produto" in row.index:
                            col_prod = "Descrição do produto"
                        else:
                            col_prod = "Descricao_Produto"

                        descricao_produto = valor_seguro(
                            row.get(col_prod, "Sem descrição"),
                            "Sem descrição",
                        )

                        # Data e hora de abertura para o título resumido
                        carimbo_abertura = row.get(
                            "Carimbo de data/hora",
                            row.get("Timestamp", row.get("Data_Abertura", "")),
                        )
                        abertura_formatada = "Data não informada"

                        if str(carimbo_abertura).strip().lower() not in {
                            "", "nan", "none", "nat"
                        }:
                            try:
                                data_abertura = pd.to_datetime(
                                    carimbo_abertura,
                                    dayfirst=True,
                                    errors="raise",
                                )
                                abertura_formatada = data_abertura.strftime(
                                    "%d/%m/%Y às %H:%M"
                                )
                            except Exception:
                                abertura_formatada = valor_seguro(
                                    carimbo_abertura,
                                    "Data não informada",
                                )

                        titulo_expander = (
                            f"Chamado #{id_chamado} — {descricao_produto} "
                            f"— {abertura_formatada}"
                        )

                        with st.expander(
                            titulo_expander,
                            expanded=False,
                        ):
                            # ------------------------------------------------------
                            # Placar das alçadas
                            # ------------------------------------------------------
                            st.markdown(
                                '<div class="caproq-section-title">'
                                'Situação das alçadas técnicas'
                                '</div>',
                                unsafe_allow_html=True,
                            )

                            itens_placar = []

                            for _, info_placar in ALCADAS_INFO.items():
                                coluna_placar = info_placar["coluna_sheets"]
                                label_placar = info_placar["label"]
                                voto_placar = str(
                                    row.get(coluna_placar, "Pendente")
                                ).strip()
                                voto_minusculo = voto_placar.lower()

                                if voto_placar.startswith("Reprovar"):
                                    classe_status = "reprovado"
                                    texto_status = "Reprovado"
                                    icone_status = "✕"
                                elif "ressalva" in voto_minusculo:
                                    classe_status = "ressalva"
                                    texto_status = "Com ressalva"
                                    icone_status = "!"
                                elif voto_placar.startswith("Aprovar"):
                                    classe_status = "aprovado"
                                    texto_status = "Aprovado"
                                    icone_status = "✓"
                                else:
                                    classe_status = "pendente"
                                    texto_status = "Pendente"
                                    icone_status = "•"

                                itens_placar.append(
                                    f"""
<div class="caproq-score-item {classe_status}">
    <div class="caproq-score-icon">{icone_status}</div>
    <div class="caproq-score-content">
        <div class="caproq-score-area">{escape(label_placar)}</div>
        <div class="caproq-score-status">{texto_status}</div>
    </div>
</div>
"""
                                )

                            st.markdown(
                                '<div class="caproq-score-grid">'
                                + "".join(itens_placar)
                                + "</div>",
                                unsafe_allow_html=True,
                            )

                            # ------------------------------------------------------
                            # Resumo da solicitação
                            # ------------------------------------------------------
                            nome_solicitante_chamado = valor_seguro(
                                row.get(
                                    "Nome solicitante",
                                    row.get("Nome", "Não informado"),
                                ),
                                "Não informado",
                            )
                            email_solicitante_chamado = valor_seguro(
                                row.get("Endereço de e-mail", ""),
                                "Não informado",
                            )

                            st.markdown(
                                '<div class="caproq-section-title">'
                                'Resumo da solicitação'
                                '</div>',
                                unsafe_allow_html=True,
                            )

                            resumo_col1, resumo_col2, resumo_col3 = st.columns(3)

                            with resumo_col1:
                                st.markdown("**Solicitante**")
                                st.write(nome_solicitante_chamado)

                            with resumo_col2:
                                st.markdown("**E-mail**")
                                st.write(email_solicitante_chamado)

                            with resumo_col3:
                                st.markdown("**Abertura**")
                                st.write(abertura_formatada)

                            # ------------------------------------------------------
                            # Dados completos do formulário
                            # ------------------------------------------------------
                            st.markdown(
                                '<div class="caproq-section-title">'
                                'Informações do produto'
                                '</div>',
                                unsafe_allow_html=True,
                            )

                            col_detalhe1, col_detalhe2 = st.columns(2)

                            with col_detalhe1:
                                st.markdown("**Descrição do produto**")
                                st.write(descricao_produto)

                                st.markdown("**Apresentação / volume**")
                                st.write(valor_seguro(row.get("Apresentação/volume", "")))

                                st.markdown("**Fabricante / fornecedor**")
                                st.write(valor_seguro(row.get("Fabricante/fornecedor", "")))

                                st.markdown("**Área e indicação de uso**")
                                st.write(
                                    valor_seguro(
                                        row.get(
                                            "Área onde será utilizado e indicação detalhada de uso do produto",
                                            "",
                                        )
                                    )
                                )

                            with col_detalhe2:
                                st.markdown("**Contato do fornecedor**")
                                st.write(
                                    valor_seguro(
                                        row.get(
                                            "Informações de contato do fornecedor (nome, e-mail e telefone)",
                                            "",
                                        )
                                    )
                                )

                                st.markdown("**Procedimento atual sem o produto**")
                                st.write(
                                    valor_seguro(
                                        row.get(
                                            "Explique como o procedimento/atividade atual é realizado SEM este produto:",
                                            "",
                                        )
                                    )
                                )

                                st.markdown("**Gera resíduo perigoso?**")
                                st.write(
                                    valor_seguro(
                                        row.get(
                                            "O item solicitado gera resíduo perigoso?",
                                            "",
                                        )
                                    )
                                )

                                st.markdown("**Possui estudos científicos?**")
                                st.write(
                                    valor_seguro(
                                        row.get(
                                            "O produto apresenta estudos científicos e de custo-efetividade comparado com o utilizado atualmente no HMV? Caso sim, anexe o arquivo abaixo.",
                                            "",
                                        )
                                    )
                                )

                            # ------------------------------------------------------
                            # Documentos
                            # ------------------------------------------------------
                            st.markdown(
                                '<div class="caproq-section-title">Documentos</div>',
                                unsafe_allow_html=True,
                            )

                            link_anexo = row.get(
                                "Link_Anexo",
                                row.get("Arquivos anexados", ""),
                            )
                            link_fds = row.get("Anexar FDS", "")

                            doc_col1, doc_col2 = st.columns(2)

                            with doc_col1:
                                if str(link_fds).strip().lower() not in {
                                    "", "nan", "none", "não aplicável"
                                }:
                                    st.link_button(
                                        "📄 Abrir FDS",
                                        str(link_fds).strip(),
                                        use_container_width=True,
                                    )
                                else:
                                    st.caption("FDS não disponível.")

                            with doc_col2:
                                if str(link_anexo).strip().lower() not in {
                                    "",
                                    "nan",
                                    "none",
                                    "nenhum arquivo anexado",
                                    "nenhum arquivo adicional",
                                }:
                                    st.link_button(
                                        "📎 Abrir arquivos anexados",
                                        str(link_anexo).strip(),
                                        use_container_width=True,
                                    )
                                else:
                                    st.caption("Nenhum arquivo adicional anexado.")

                            st.markdown(
                                '<div class="caproq-section-title">'
                                'Seu parecer técnico'
                                '</div>',
                                unsafe_allow_html=True,
                            )
                            
                            for letra_col, info in ALCADAS_INFO.items():
                                col_voto = info["coluna_sheets"]
                                
                                if col_voto in colunas_validas and row[col_voto] == "Pendente":
                                    with st.container(border=True):
                                        st.markdown(f"**Alçada:** `{info['label']}`")
                                        
                                        key_voto = f"voto_escolha_{id_chamado}_{letra_col}"
                                        key_parecer = f"parecer_text_{id_chamado}_{letra_col}"
                                        
                                        voto_opcao = st.radio(
                                            "Decisão da Alçada:",
                                            options=["Aprovar", "Aprovar com ressalva", "Reprovar"],
                                            format_func=lambda x: "👍 Aprovar" if x == "Aprovar" else "⚠️ Aprovar com ressalva" if x == "Aprovar com ressalva" else "👎 Reprovar",
                                            index=None,
                                            horizontal=True,
                                            key=key_voto
                                        )
                                        
                                        if voto_opcao:
                                            parecer_obrigatorio = voto_opcao in ["Aprovar com ressalva", "Reprovar"]
                                            label_parecer = f"Parecer técnico para {info['label']} (Obrigatório):" if parecer_obrigatorio else f"Parecer técnico para {info['label']} (Opcional):"
                                            
                                            parecer_texto = st.text_area(label_parecer, key=key_parecer)
                                            
                                            if st.button(f"Confirmar parecer {info['label']}", key=f"btn_salvar_{id_chamado}_{letra_col}", type="primary"):
                                                if parecer_obrigatorio and not parecer_texto.strip():
                                                    ui.render_feedback(f"Preencha o parecer antes de registrar a decisão '{voto_opcao}'.", kind="error", title="Parecer obrigatório", icon="📝")
                                                else:
                                                    fuso_br = datetime.timezone(datetime.timedelta(hours=-3))
                                                    timestamp_atual = datetime.datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                                                    
                                                    aprovador_nome_seguro = st.session_state.get('name', user_name)
                                                    if not aprovador_nome_seguro or str(aprovador_nome_seguro).strip() in ["None", ""]:
                                                        aprovador_nome_seguro = f"Aprovador {info['label']}"
                                                    
                                                    texto_parecer_limpo = parecer_texto.strip().replace("\n", " ")
                                                    
                                                    if texto_parecer_limpo:
                                                        conteudo_coluna = f"{voto_opcao} ({timestamp_atual} - {aprovador_nome_seguro}: {texto_parecer_limpo})"
                                                    else:
                                                        conteudo_coluna = f"{voto_opcao} ({timestamp_atual} - {aprovador_nome_seguro})"
                                                    
                                                    df_dados.loc[df_dados["ID"] == id_chamado, col_voto] = conteudo_coluna
                                                    
                                                    linha_atualizada = df_dados[df_dados["ID"] == id_chamado].iloc[0]
                                                    todos_votos_valores = [str(linha_atualizada[inf["coluna_sheets"]]) for inf in ALCADAS_INFO.values() if inf["coluna_sheets"] in df_dados.columns]
                                                    
                                                    reprovados_count = sum(1 for v in todos_votos_valores if v.startswith("Reprovar"))
                                                    votos_total_emitidos = sum(1 for v in todos_votos_valores if v.startswith(("Aprovar", "Reprovar")))

                                                    if "Status_Aprovadores" not in df_dados.columns:
                                                        df_dados["Status_Aprovadores"] = ""
                                                    else:
                                                        df_dados["Status_Aprovadores"] = df_dados["Status_Aprovadores"].astype(str)
                                                    
                                                    # Notificações do parecer emitido
                                                    email_solicitante = str(
                                                        row.get("Endereço de e-mail", "")
                                                    ).strip().lower()
                                                    nome_solicitante = valor_seguro(
                                                        row.get("Nome solicitante", row.get("Nome", "Solicitante")),
                                                        "Solicitante",
                                                    )
                                                    cor_parecer = (
                                                        "#D93025" if voto_opcao == "Reprovar"
                                                        else "#E6A23C" if voto_opcao == "Aprovar com ressalva"
                                                        else "#008D4C"
                                                    )
                                                    detalhes_parecer = f"""
                                                    <div style="margin-top:20px;padding:16px;background:#f8f9fa;
                                                                border-left:4px solid {cor_parecer};border-radius:4px;">
                                                      <p style="margin:0 0 8px;"><b>Chamado:</b> #{id_chamado}</p>
                                                      <p style="margin:0 0 8px;"><b>Área:</b> {info['label']}</p>
                                                      <p style="margin:0 0 8px;"><b>Avaliação:</b> {voto_opcao}</p>
                                                      <p style="margin:0;"><b>Parecer:</b> {texto_parecer_limpo or 'Sem observação adicional.'}</p>
                                                    </div>
                                                    """
                                                    html_solicitante_parecer = template_email_caproq(
                                                        titulo=f"Nova avaliação no Chamado #{id_chamado}",
                                                        mensagem=(
                                                            f"Olá, <b>{nome_solicitante}</b>. A área "
                                                            f"<b>{info['label']}</b> registrou sua avaliação "
                                                            "técnica. O chamado continua no fluxo até a "
                                                            "homologação final dos administradores."
                                                        ),
                                                        detalhes=detalhes_parecer,
                                                        destaque=cor_parecer,
                                                    )
                                                    if "@" in email_solicitante:
                                                        enviar_email(
                                                            destinatario=email_solicitante,
                                                            assunto=f"CAPROQ: Avaliação de {info['label']} - #{id_chamado}",
                                                            corpo_html=html_solicitante_parecer,
                                                        )

                                                    # Toda reprovação técnica alerta o comitê para reunião.
                                                    if voto_opcao == "Reprovar":
                                                        html_alerta = template_email_caproq(
                                                            titulo=f"Reunião necessária · Chamado #{id_chamado}",
                                                            mensagem=(
                                                                f"A área <b>{info['label']}</b> registrou parecer "
                                                                f"desfavorável para o produto <b>{descricao_produto}</b>. "
                                                                "Os demais pareceres devem continuar normalmente, mas "
                                                                "uma reunião do comitê deverá ser organizada antes da "
                                                                "homologação final."
                                                            ),
                                                            detalhes=detalhes_parecer,
                                                            destaque="#D93025",
                                                        )
                                                        for email_membro in todos_emails_aprovadores():
                                                            enviar_email(
                                                                destinatario=email_membro,
                                                                assunto=f"CAPROQ: Reunião necessária - Chamado #{id_chamado}",
                                                                corpo_html=html_alerta,
                                                            )

                                                    # Matriz de decisão hierárquica corrigida para priorizar a reunião necessária
                                                    if reprovados_count > 0:
                                                        df_dados.loc[df_dados["ID"] == id_chamado, "Status_Aprovadores"] = "Reunião Necessária"
                                                    elif votos_total_emitidos == len(ALCADAS_INFO):
                                                        df_dados.loc[df_dados["ID"] == id_chamado, "Status_Aprovadores"] = "Aguardando homologação"
                                                    else:
                                                        df_dados.loc[df_dados["ID"] == id_chamado, "Status_Aprovadores"] = "Em deliberação"

                                                    conn.update(data=df_dados)

                                                    st.session_state["df_dados_cache"] = df_dados.copy()
                                                    st.session_state["df_dados_cache_timestamp"] = time.time()

                                                    ui.render_feedback("Seu parecer técnico foi registrado e o fluxo do chamado foi atualizado.", kind="success", title="Parecer registrado", icon="✅")
                                                    time.sleep(1.2)
                                                    st.rerun()

            # ----------------------------------------------------------------------
            # 8.2. Aba "Histórico Geral"
            # ----------------------------------------------------------------------
            with tab_hist_aprovador:


                if historico_aprovador.empty:
                    ui.render_empty_state("Histórico ainda vazio", "Ainda não há decisões registradas para as alçadas vinculadas ao seu perfil.", icon="🕘")
                else:
                    df_historico = historico_aprovador.copy()

                    def _hist_coluna(candidatas):
                        for candidata in candidatas:
                            if candidata in df_historico.columns:
                                return candidata
                        return None

                    col_hist_produto = _hist_coluna([
                        "Descrição completa do produto",
                        "Descrição do produto",
                        "Descricao_Produto",
                    ])
                    col_hist_data = _hist_coluna([
                        "Carimbo de data/hora",
                        "Timestamp",
                        "Data_Abertura",
                        "Data de abertura",
                    ])
                    col_hist_solicitante = _hist_coluna([
                        "Nome solicitante",
                        "Remetente_Nome",
                        "Nome",
                    ])
                    col_hist_email = _hist_coluna([
                        "Endereço de e-mail",
                        "Remetente_Email",
                        "Email",
                    ])
                    col_hist_setor = _hist_coluna([
                        "Setor_Solicitante",
                        "Setor solicitante",
                        "Setor",
                    ])
                    col_hist_fornecedor = _hist_coluna([
                        "Fornecedor",
                        "Nome do fornecedor",
                        "Fornecedor do produto",
                    ])

                    df_historico["_hist_data"] = (
                        pd.to_datetime(df_historico[col_hist_data], errors="coerce", dayfirst=True)
                        if col_hist_data else pd.NaT
                    )
                    df_historico["_hist_status"] = (
                        df_historico["Status_Final"].fillna("Não informado").astype(str).str.strip()
                        if "Status_Final" in df_historico.columns else "Não informado"
                    )

                    st.markdown('<div class="caproq-history-filter-shell">', unsafe_allow_html=True)
                    hist_f1, hist_f2, hist_f3 = st.columns([1.7, 1, 1])
                    with hist_f1:
                        busca_historico = st.text_input(
                            "Buscar no histórico",
                            placeholder="Número do chamado, produto, fornecedor ou solicitante",
                            key="historico_geral_busca",
                        )
                    status_hist_disponiveis = sorted(
                        [s for s in df_historico["_hist_status"].dropna().unique().tolist() if s]
                    )
                    with hist_f2:
                        status_hist_selecionados = st.multiselect(
                            "Status geral",
                            status_hist_disponiveis,
                            default=status_hist_disponiveis,
                            key="historico_geral_status",
                        )
                    with hist_f3:
                        periodo_hist = st.selectbox(
                            "Período de abertura",
                            ["Todo o histórico", "Últimos 30 dias", "Últimos 90 dias", "Últimos 12 meses"],
                            key="historico_geral_periodo",
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

                    df_hist_filtrado = df_historico.copy()

                    if status_hist_selecionados:
                        df_hist_filtrado = df_hist_filtrado[
                            df_hist_filtrado["_hist_status"].isin(status_hist_selecionados)
                        ]
                    else:
                        df_hist_filtrado = df_hist_filtrado.iloc[0:0]

                    dias_periodo_hist = {
                        "Últimos 30 dias": 30,
                        "Últimos 90 dias": 90,
                        "Últimos 12 meses": 365,
                    }.get(periodo_hist)
                    if dias_periodo_hist is not None and df_hist_filtrado["_hist_data"].notna().any():
                        limite_hist = pd.Timestamp.now().normalize() - pd.Timedelta(days=dias_periodo_hist)
                        df_hist_filtrado = df_hist_filtrado[
                            df_hist_filtrado["_hist_data"] >= limite_hist
                        ]

                    termo_hist = busca_historico.strip().lower()
                    if termo_hist:
                        colunas_busca_hist = ["ID"]
                        for coluna_busca in [
                            col_hist_produto,
                            col_hist_solicitante,
                            col_hist_email,
                            col_hist_setor,
                            col_hist_fornecedor,
                        ]:
                            if coluna_busca and coluna_busca in df_hist_filtrado.columns:
                                colunas_busca_hist.append(coluna_busca)

                        mascara_hist = pd.Series(False, index=df_hist_filtrado.index)
                        for coluna_busca in colunas_busca_hist:
                            mascara_hist = mascara_hist | (
                                df_hist_filtrado[coluna_busca]
                                .fillna("")
                                .astype(str)
                                .str.lower()
                                .str.contains(termo_hist, regex=False)
                            )
                        df_hist_filtrado = df_hist_filtrado[mascara_hist]

                    df_hist_filtrado = df_hist_filtrado.sort_values(
                        by="_hist_data",
                        ascending=False,
                        na_position="last",
                    )

                    total_hist = len(df_hist_filtrado)
                    aprovados_hist = int((df_hist_filtrado["_hist_status"].str.lower() == "aprovado").sum())
                    ressalvas_hist = int(df_hist_filtrado["_hist_status"].str.lower().str.contains("ressalva", na=False).sum())
                    reprovados_hist = int((df_hist_filtrado["_hist_status"].str.lower() == "reprovado").sum())

                    st.markdown(
                        f"""
<div class="caproq-history-summary">
    <div class="caproq-history-summary-card">
        <p class="caproq-history-summary-label">Resultados encontrados</p>
        <p class="caproq-history-summary-value">{total_hist}</p>
    </div>
    <div class="caproq-history-summary-card">
        <p class="caproq-history-summary-label">Aprovados</p>
        <p class="caproq-history-summary-value">{aprovados_hist}</p>
    </div>
    <div class="caproq-history-summary-card">
        <p class="caproq-history-summary-label">Com ressalva</p>
        <p class="caproq-history-summary-value">{ressalvas_hist}</p>
    </div>
    <div class="caproq-history-summary-card">
        <p class="caproq-history-summary-label">Reprovados</p>
        <p class="caproq-history-summary-value">{reprovados_hist}</p>
    </div>
</div>
""",
                        unsafe_allow_html=True,
                    )

                    if df_hist_filtrado.empty:
                        ui.render_empty_state("Nenhum chamado encontrado", "Revise os filtros ou o termo de busca para ampliar os resultados.", icon="🔎")
                    else:
                        for _, row in df_hist_filtrado.iterrows():
                            try:
                                id_c = int(float(row.get("ID", 0)))
                            except (TypeError, ValueError):
                                id_c = row.get("ID", "—")

                            desc_h = valor_seguro(
                                row.get(col_hist_produto, "Sem descrição") if col_hist_produto else "Sem descrição",
                                "Sem descrição",
                            )
                            status_h = valor_seguro(row.get("Status_Final", "Não informado"), "Não informado")
                            data_h = row.get("_hist_data")
                            data_titulo = (
                                data_h.strftime("%d/%m/%Y")
                                if pd.notna(data_h) else "data não informada"
                            )

                            titulo_hist = f"Chamado #{id_c} · {desc_h} · {status_h} · {data_titulo}"

                            with st.expander(titulo_hist, expanded=False):
                                solicitante_h = valor_seguro(
                                    row.get(col_hist_solicitante, "Não informado") if col_hist_solicitante else "Não informado"
                                )
                                email_h = valor_seguro(
                                    row.get(col_hist_email, "Não informado") if col_hist_email else "Não informado"
                                )
                                setor_h = valor_seguro(
                                    row.get(col_hist_setor, "Não informado") if col_hist_setor else "Não informado"
                                )
                                fornecedor_h = valor_seguro(
                                    row.get(col_hist_fornecedor, "Não informado") if col_hist_fornecedor else "Não informado"
                                )
                                abertura_h = (
                                    data_h.strftime("%d/%m/%Y às %H:%M")
                                    if pd.notna(data_h) else "Não identificada"
                                )

                                st.markdown(
                                    f"""
<div class="caproq-history-request">
    <div class="caproq-history-request-grid">
        <div>
            <div class="caproq-history-field-label">Solicitante</div>
            <div class="caproq-history-field-value">{escape(str(solicitante_h))}</div>
        </div>
        <div>
            <div class="caproq-history-field-label">Setor</div>
            <div class="caproq-history-field-value">{escape(str(setor_h))}</div>
        </div>
        <div>
            <div class="caproq-history-field-label">Fornecedor</div>
            <div class="caproq-history-field-value">{escape(str(fornecedor_h))}</div>
        </div>
        <div>
            <div class="caproq-history-field-label">Abertura</div>
            <div class="caproq-history-field-value">{escape(str(abertura_h))}</div>
        </div>
    </div>
</div>
""",
                                    unsafe_allow_html=True,
                                )

                                st.markdown(
                                    '<div class="caproq-history-section-label">Situação das alçadas técnicas</div>',
                                    unsafe_allow_html=True,
                                )

                                cards_alcadas_hist = []
                                for _, info in ALCADAS_INFO.items():
                                    c_nome = info["coluna_sheets"]
                                    voto_hist = valor_seguro(row.get(c_nome, "Pendente"), "Pendente")
                                    voto_lower = str(voto_hist).lower()

                                    if "reprovar" in voto_lower or "reprov" in voto_lower:
                                        badge_classe = "rejected"
                                        badge_rotulo = "Reprovado"
                                        badge_icone = "●"
                                    elif "ressalva" in voto_lower:
                                        badge_classe = "warning"
                                        badge_rotulo = "Com ressalva"
                                        badge_icone = "●"
                                    elif "aprovar" in voto_lower or voto_lower == "aprovado":
                                        badge_classe = "approved"
                                        badge_rotulo = "Aprovado"
                                        badge_icone = "●"
                                    else:
                                        badge_classe = "pending"
                                        badge_rotulo = "Pendente"
                                        badge_icone = "○"

                                    cards_alcadas_hist.append(
                                        f"""
<div class="caproq-history-area-card">
    <div class="caproq-history-area-name">{escape(str(info['label']))}</div>
    <span class="caproq-history-badge {badge_classe}">{badge_icone} {badge_rotulo}</span>
</div>
"""
                                    )

                                st.markdown(
                                    '<div class="caproq-history-scoreboard">'
                                    + "".join(cards_alcadas_hist)
                                    + '</div>',
                                    unsafe_allow_html=True,
                                )

                                st.markdown(
                                    '<div class="caproq-history-section-label">Pareceres registrados</div>',
                                    unsafe_allow_html=True,
                                )
                                pareceres_encontrados_hist = False
                                for _, info in ALCADAS_INFO.items():
                                    c_nome = info["coluna_sheets"]
                                    voto_hist = valor_seguro(row.get(c_nome, "Pendente"), "Pendente")
                                    if str(voto_hist).strip().lower() not in {"", "pendente", "nan", "none"}:
                                        pareceres_encontrados_hist = True
                                        voto_lower = str(voto_hist).lower()
                                        if "reprovar" in voto_lower or "reprov" in voto_lower:
                                            st.error(f"🔴 **{info['label']}** — {voto_hist}")
                                        elif "ressalva" in voto_lower:
                                            st.warning(f"🟡 **{info['label']}** — {voto_hist}")
                                        else:
                                            st.success(f"🟢 **{info['label']}** — {voto_hist}")

                                if not pareceres_encontrados_hist:
                                    st.caption("Nenhum parecer técnico foi registrado para este chamado.")

                                # ----------------------------------------------------------
                                # Solicitação de alteração de parecer da própria alçada
                                # ----------------------------------------------------------
                                st.markdown(
                                    '<div class="caproq-history-section-label">Revisão do parecer técnico</div>',
                                    unsafe_allow_html=True,
                                )

                                df_alteracoes_ui = carregar_alteracoes_pareceres()
                                alcadas_editaveis = []
                                for _, info_revisao in ALCADAS_INFO.items():
                                    coluna_revisao = info_revisao["coluna_sheets"]
                                    if coluna_revisao not in colunas_permitidas_usuario:
                                        continue
                                    if coluna_revisao not in row.index:
                                        continue

                                    voto_revisao = valor_seguro(row.get(coluna_revisao, "Pendente"), "Pendente")
                                    decisao_revisao, parecer_revisao = extrair_decisao_e_parecer_registrado(voto_revisao)
                                    if decisao_revisao.lower() == "pendente":
                                        continue

                                    alcadas_editaveis.append(
                                        {
                                            "label": info_revisao["label"],
                                            "coluna": coluna_revisao,
                                            "decisao": decisao_revisao,
                                            "parecer": parecer_revisao,
                                        }
                                    )

                                if not alcadas_editaveis:
                                    st.caption("Não há parecer da sua alçada disponível para solicitar alteração neste chamado.")
                                else:
                                    for item_revisao in alcadas_editaveis:
                                        label_revisao = item_revisao["label"]
                                        coluna_revisao = item_revisao["coluna"]
                                        decisao_atual_revisao = item_revisao["decisao"]
                                        parecer_atual_revisao = item_revisao["parecer"]
                                        chave_revisao = f"alterar_parecer_{id_c}_{coluna_revisao}"

                                        alteracao_pendente = existe_alteracao_pendente(
                                            id_c,
                                            label_revisao,
                                            df_alteracoes=df_alteracoes_ui,
                                        )
                                        em_homologacao = chamado_esta_em_homologacao(row)
                                        liberada_reabertura = alcada_esta_liberada_para_revisao(
                                            row,
                                            label_revisao,
                                        )

                                        with st.container(border=True):
                                            cab1, cab2 = st.columns([1.2, 2.2])
                                            with cab1:
                                                st.markdown(f"**{label_revisao}**")
                                                st.caption(f"Decisão vigente: {decisao_atual_revisao}")
                                            with cab2:
                                                st.caption(
                                                    "O parecer vigente permanece válido até que um administrador confirme a alteração."
                                                )

                                            if alteracao_pendente:
                                                solicitacoes_alcada = df_alteracoes_ui[
                                                    pd.to_numeric(
                                                        df_alteracoes_ui["ID_Chamado"],
                                                        errors="coerce",
                                                    ).eq(pd.to_numeric(pd.Series([id_c]), errors="coerce").iloc[0])
                                                    & df_alteracoes_ui["Alcada"].astype(str).str.strip().str.lower().eq(label_revisao.lower())
                                                    & df_alteracoes_ui["Status_Alteracao"].astype(str).str.strip().str.lower().eq(STATUS_ALTERACAO_PENDENTE.lower())
                                                ]
                                                data_pendente = ""
                                                if not solicitacoes_alcada.empty:
                                                    data_pendente = str(solicitacoes_alcada.iloc[-1].get("Data_Solicitacao", "")).strip()
                                                mensagem_pendente = "Já existe uma solicitação aguardando validação administrativa."
                                                if data_pendente:
                                                    mensagem_pendente += f" Enviada em {data_pendente}."
                                                ui.render_feedback(
                                                    mensagem_pendente,
                                                    kind="warning",
                                                    title="Alteração em análise",
                                                    icon="⏳",
                                                )
                                                continue

                                            if em_homologacao and not liberada_reabertura:
                                                ui.render_feedback(
                                                    "Este chamado já chegou à homologação. Um administrador precisa reabri-lo para a sua alçada antes de uma nova solicitação.",
                                                    kind="info",
                                                    title="Reabertura administrativa necessária",
                                                    icon="🔒",
                                                )
                                                continue

                                            if liberada_reabertura:
                                                ui.render_feedback(
                                                    "O administrador reabriu este chamado para revisão da sua alçada. Registre abaixo a alteração proposta.",
                                                    kind="info",
                                                    title="Revisão técnica liberada",
                                                    icon="🔄",
                                                )

                                            with st.expander("Solicitar alteração do parecer", expanded=False):
                                                st.markdown(f"**Decisão atual:** {decisao_atual_revisao}")
                                                if parecer_atual_revisao:
                                                    st.markdown(f"**Parecer atual:** {parecer_atual_revisao}")
                                                else:
                                                    st.caption("O registro atual não possui observação textual separada.")

                                                with st.form(chave_revisao, clear_on_submit=False):
                                                    nova_decisao = st.selectbox(
                                                        "Nova decisão proposta *",
                                                        ["Aprovar", "Aprovar com ressalva", "Reprovar"],
                                                        index=(
                                                            ["Aprovar", "Aprovar com ressalva", "Reprovar"].index(decisao_atual_revisao)
                                                            if decisao_atual_revisao in ["Aprovar", "Aprovar com ressalva", "Reprovar"]
                                                            else 0
                                                        ),
                                                        key=f"nova_decisao_{chave_revisao}",
                                                    )
                                                    novo_parecer = st.text_area(
                                                        "Novo parecer técnico",
                                                        value=parecer_atual_revisao,
                                                        placeholder="Descreva as condições, ressalvas ou fundamentos técnicos da nova decisão.",
                                                        height=130,
                                                        key=f"novo_parecer_{chave_revisao}",
                                                    )
                                                    justificativa_alteracao = st.text_area(
                                                        "Justificativa da alteração *",
                                                        placeholder="Explique o que mudou desde a decisão anterior e por que o parecer deve ser revisto.",
                                                        height=120,
                                                        key=f"justificativa_{chave_revisao}",
                                                    )

                                                    confirmar_ciencia = st.checkbox(
                                                        "Estou ciente de que a decisão vigente só será substituída após confirmação de um administrador.",
                                                        key=f"ciencia_{chave_revisao}",
                                                    )
                                                    enviar_alteracao = st.form_submit_button(
                                                        "Enviar para validação administrativa",
                                                        use_container_width=True,
                                                    )

                                                if enviar_alteracao:
                                                    erros_alteracao = []
                                                    if nova_decisao == decisao_atual_revisao and novo_parecer.strip() == parecer_atual_revisao.strip():
                                                        erros_alteracao.append("A nova proposta é igual ao parecer vigente.")
                                                    if not justificativa_alteracao.strip():
                                                        erros_alteracao.append("Informe a justificativa da alteração.")
                                                    if nova_decisao in ["Aprovar com ressalva", "Reprovar"] and not novo_parecer.strip():
                                                        erros_alteracao.append("O novo parecer é obrigatório para ressalva ou reprovação.")
                                                    if not confirmar_ciencia:
                                                        erros_alteracao.append("Confirme a ciência sobre a validação administrativa.")

                                                    if erros_alteracao:
                                                        ui.render_feedback(
                                                            " ".join(erros_alteracao),
                                                            kind="error",
                                                            title="Revise os campos",
                                                            icon="⚠️",
                                                        )
                                                    else:
                                                        try:
                                                            registro_alteracao = criar_registro_alteracao_parecer(
                                                                id_chamado=id_c,
                                                                alcada=label_revisao,
                                                                coluna_parecer=coluna_revisao,
                                                                decisao_anterior=decisao_atual_revisao,
                                                                parecer_anterior=parecer_atual_revisao,
                                                                decisao_solicitada=nova_decisao,
                                                                parecer_solicitado=novo_parecer,
                                                                justificativa=justificativa_alteracao,
                                                                solicitante_nome=user_name,
                                                                solicitante_email=user_email,
                                                                origem_reabertura="SIM" if liberada_reabertura else "NÃO",
                                                                id_reabertura=str(row.get("ID_Reabertura_Atual", "")),
                                                            )

                                                            if adicionar_solicitacao_alteracao(registro_alteracao):
                                                                if "Status_Revisao" not in df_dados.columns:
                                                                    df_dados["Status_Revisao"] = STATUS_REVISAO_NAO_APLICAVEL
                                                                mascara_chamado_revisao = df_dados["ID"] == id_c
                                                                df_dados.loc[
                                                                    mascara_chamado_revisao,
                                                                    "Status_Revisao",
                                                                ] = STATUS_REVISAO_ALTERACAO_EM_ANALISE
                                                                conn.update(data=df_dados)
                                                                st.session_state["df_dados_cache"] = df_dados.copy()
                                                                st.session_state["df_dados_cache_timestamp"] = time.time()

                                                                detalhes_admin = f"""
                                                                <div style="margin-top:20px;padding:16px;background:#f8f9fa;border-left:4px solid #005691;border-radius:4px;">
                                                                  <p style="margin:0 0 8px;"><b>Chamado:</b> #{id_c}</p>
                                                                  <p style="margin:0 0 8px;"><b>Alçada:</b> {label_revisao}</p>
                                                                  <p style="margin:0 0 8px;"><b>Decisão vigente:</b> {decisao_atual_revisao}</p>
                                                                  <p style="margin:0 0 8px;"><b>Nova decisão proposta:</b> {nova_decisao}</p>
                                                                  <p style="margin:0;"><b>Justificativa:</b> {justificativa_alteracao.strip()}</p>
                                                                </div>
                                                                """
                                                                html_admin = template_email_caproq(
                                                                    titulo=f"Alteração de parecer · Chamado #{id_c}",
                                                                    mensagem=(
                                                                        f"<b>{user_name}</b> solicitou a revisão do parecer da alçada "
                                                                        f"<b>{label_revisao}</b>. A decisão vigente não foi alterada e aguarda validação administrativa."
                                                                    ),
                                                                    detalhes=detalhes_admin,
                                                                    destaque="#005691",
                                                                )
                                                                for email_admin in sorted(set(ADMINS)):
                                                                    enviar_email(
                                                                        destinatario=email_admin,
                                                                        assunto=f"CAPROQ: Alteração de parecer aguardando validação - #{id_c}",
                                                                        corpo_html=html_admin,
                                                                    )

                                                                ui.render_feedback(
                                                                    "A solicitação foi registrada. O parecer atual permanece vigente até a análise de um administrador.",
                                                                    kind="success",
                                                                    title="Alteração enviada",
                                                                    icon="✅",
                                                                )
                                                                time.sleep(1.2)
                                                                st.rerun()
                                                            else:
                                                                ui.render_feedback(
                                                                    "Já existe uma solicitação pendente para este chamado e alçada, ou não foi possível gravar a nova solicitação.",
                                                                    kind="warning",
                                                                    title="Solicitação não registrada",
                                                                    icon="⏳",
                                                                )
                                                        except Exception as erro_alteracao:
                                                            ui.render_feedback(
                                                                str(erro_alteracao),
                                                                kind="error",
                                                                title="Falha ao solicitar alteração",
                                                                icon="⚠️",
                                                            )

                                with st.expander("Dados complementares do chamado", expanded=False):
                                    c1_hist, c2_hist = st.columns(2)
                                    with c1_hist:
                                        st.markdown(f"**E-mail do solicitante:** {email_h}")
                                        st.markdown(f"**Status dos aprovadores:** {valor_seguro(row.get('Status_Aprovadores', 'Não informado'))}")
                                    with c2_hist:
                                        st.markdown(f"**Status final:** {status_h}")
                                        st.markdown(f"**Produto de teste:** {valor_seguro(row.get('Produto_Teste', row.get('Este produto é um Produto de Teste / Piloto?', 'Não informado')))}")

            # ----------------------------------------------------------------------
            # 8.3. Aba "Log de atividades"
            # ----------------------------------------------------------------------
            with tab_logs:

                st.markdown("### Eventos de revisão e auditoria")
                eventos_revisao = []
                try:
                    alteracoes_log = carregar_alteracoes_pareceres(forcar_atualizacao=True)
                    for _, evento_alt in alteracoes_log.iterrows():
                        status_evento = str(evento_alt.get("Status_Alteracao", "")).strip()
                        eventos_revisao.append({
                            "Data": evento_alt.get("Data_Solicitacao", ""),
                            "Chamado": evento_alt.get("ID_Chamado", ""),
                            "Evento": "Alteração de parecer solicitada",
                            "Alçada": evento_alt.get("Alcada", ""),
                            "Responsável": evento_alt.get("Solicitante_Nome", ""),
                            "Detalhes": f"{evento_alt.get('Decisao_Anterior', '')} → {evento_alt.get('Decisao_Solicitada', '')}",
                            "Protocolo": evento_alt.get("ID_Alteracao", ""),
                        })
                        if status_evento and status_evento.lower() != STATUS_ALTERACAO_PENDENTE.lower():
                            eventos_revisao.append({
                                "Data": evento_alt.get("Data_Analise", ""),
                                "Chamado": evento_alt.get("ID_Chamado", ""),
                                "Evento": f"Alteração de parecer {status_evento.lower()}",
                                "Alçada": evento_alt.get("Alcada", ""),
                                "Responsável": evento_alt.get("Admin_Responsavel", ""),
                                "Detalhes": evento_alt.get("Motivo_Recusa", "") or f"Nova decisão oficial: {evento_alt.get('Decisao_Solicitada', '')}",
                                "Protocolo": evento_alt.get("ID_Alteracao", ""),
                            })
                    if "Data_Reabertura" in df_dados.columns:
                        for _, evento_reab in df_dados[df_dados["Data_Reabertura"].astype(str).str.strip().ne("")].iterrows():
                            eventos_revisao.append({
                                "Data": evento_reab.get("Data_Reabertura", ""),
                                "Chamado": evento_reab.get("ID", ""),
                                "Evento": "Chamado reaberto para revisão técnica",
                                "Alçada": evento_reab.get("Alcada_Reaberta", ""),
                                "Responsável": evento_reab.get("Admin_Reabertura", ""),
                                "Detalhes": evento_reab.get("Motivo_Reabertura", ""),
                                "Protocolo": evento_reab.get("ID_Reabertura_Atual", ""),
                            })
                except Exception as erro_auditoria:
                    print(f"Falha ao consolidar eventos de revisão: {erro_auditoria}")
                if eventos_revisao:
                    df_eventos_revisao = pd.DataFrame(eventos_revisao)
                    df_eventos_revisao["__ordem"] = pd.to_datetime(df_eventos_revisao["Data"], dayfirst=True, errors="coerce")
                    df_eventos_revisao = df_eventos_revisao.sort_values("__ordem", ascending=False).drop(columns=["__ordem"])
                    with st.expander(f"Revisões registradas ({len(df_eventos_revisao)})", expanded=False):
                        st.dataframe(df_eventos_revisao.head(200), use_container_width=True, hide_index=True)
                else:
                    st.caption("Nenhum evento de revisão foi registrado até o momento.")

                df_logs = df_dados.copy()

                coluna_data_log = None
                for coluna_candidata in ["Carimbo de data/hora", "Timestamp"]:
                    if coluna_candidata in df_logs.columns:
                        coluna_data_log = coluna_candidata
                        break

                if coluna_data_log:
                    df_logs["__data_log"] = pd.to_datetime(
                        df_logs[coluna_data_log],
                        errors="coerce",
                        dayfirst=True,
                    )
                else:
                    df_logs["__data_log"] = pd.NaT

                with st.container():
                    st.markdown('<div class="caproq-audit-filter-shell">', unsafe_allow_html=True)
                    f1_log, f2_log, f3_log, f4_log = st.columns([2.2, 1.2, 1.2, 1.35])

                    with f1_log:
                        busca_log = st.text_input(
                            "Buscar no histórico",
                            placeholder="Chamado, produto, solicitante, e-mail ou fornecedor",
                            key="audit_search",
                        )

                    status_disponiveis_log = ["Todos"]
                    if "Status_Final" in df_logs.columns:
                        status_disponiveis_log += sorted(
                            {
                                str(v).strip()
                                for v in df_logs["Status_Final"].dropna().tolist()
                                if str(v).strip()
                            }
                        )

                    with f2_log:
                        status_log = st.selectbox(
                            "Status",
                            status_disponiveis_log,
                            key="audit_status",
                        )

                    alcadas_filtro_log = ["Todas"] + [
                        info["label"] for info in ALCADAS_INFO.values()
                    ]
                    with f3_log:
                        alcada_log = st.selectbox(
                            "Alçada",
                            alcadas_filtro_log,
                            key="audit_area",
                        )

                    with f4_log:
                        periodo_log = st.selectbox(
                            "Período",
                            ["Todo o período", "Últimos 30 dias", "Últimos 90 dias", "Este ano"],
                            key="audit_period",
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

                if busca_log:
                    termo_log = busca_log.strip().lower()
                    colunas_busca_log = [
                        "ID",
                        "Descrição completa do produto",
                        "Nome solicitante",
                        "Nome",
                        "Endereço de e-mail",
                        "Fornecedor",
                        "Nome do fornecedor",
                    ]
                    mascara_busca_log = pd.Series(False, index=df_logs.index)
                    for coluna_busca_log in colunas_busca_log:
                        if coluna_busca_log in df_logs.columns:
                            mascara_busca_log = mascara_busca_log | (
                                df_logs[coluna_busca_log]
                                .astype(str)
                                .str.lower()
                                .str.contains(termo_log, na=False, regex=False)
                            )
                    df_logs = df_logs[mascara_busca_log]

                if status_log != "Todos" and "Status_Final" in df_logs.columns:
                    df_logs = df_logs[
                        df_logs["Status_Final"].astype(str).str.strip() == status_log
                    ]

                if alcada_log != "Todas":
                    info_alcada_log = next(
                        (
                            info
                            for info in ALCADAS_INFO.values()
                            if info["label"] == alcada_log
                        ),
                        None,
                    )
                    if info_alcada_log:
                        coluna_alcada_log = info_alcada_log["coluna_sheets"]
                        if coluna_alcada_log in df_logs.columns:
                            df_logs = df_logs[
                                ~df_logs[coluna_alcada_log]
                                .astype(str)
                                .str.strip()
                                .str.lower()
                                .isin(["", "pendente", "nan", "none"])
                            ]

                hoje_log = pd.Timestamp.now().normalize()
                if periodo_log == "Últimos 30 dias":
                    df_logs = df_logs[df_logs["__data_log"] >= hoje_log - pd.Timedelta(days=30)]
                elif periodo_log == "Últimos 90 dias":
                    df_logs = df_logs[df_logs["__data_log"] >= hoje_log - pd.Timedelta(days=90)]
                elif periodo_log == "Este ano":
                    df_logs = df_logs[df_logs["__data_log"].dt.year == hoje_log.year]

                df_logs = df_logs.sort_values(
                    by=["__data_log", "ID"],
                    ascending=[False, False],
                    na_position="last",
                )

                total_logs = len(df_logs)
                finalizados_logs = 0
                pareceres_logs = 0
                pendentes_logs = 0

                for _, linha_log_metricas in df_logs.iterrows():
                    status_metrica_log = str(
                        linha_log_metricas.get("Status_Final", "")
                    ).strip().lower()
                    if status_metrica_log in {
                        "aprovado",
                        "aprovado com ressalva",
                        "reprovado",
                    }:
                        finalizados_logs += 1

                    votos_registrados_log = 0
                    for info_log in ALCADAS_INFO.values():
                        coluna_voto_log = info_log["coluna_sheets"]
                        voto_log = str(
                            linha_log_metricas.get(coluna_voto_log, "Pendente")
                        ).strip().lower()
                        if voto_log not in {"", "pendente", "nan", "none"}:
                            votos_registrados_log += 1
                    pareceres_logs += votos_registrados_log
                    if votos_registrados_log < len(ALCADAS_INFO):
                        pendentes_logs += 1

                st.markdown(
                    f"""
<div class="caproq-audit-summary-grid">
    <div class="caproq-audit-summary-card">
        <div class="caproq-audit-summary-label">Chamados exibidos</div>
        <div class="caproq-audit-summary-value">{total_logs}</div>
    </div>
    <div class="caproq-audit-summary-card">
        <div class="caproq-audit-summary-label">Eventos técnicos</div>
        <div class="caproq-audit-summary-value">{pareceres_logs}</div>
    </div>
    <div class="caproq-audit-summary-card">
        <div class="caproq-audit-summary-label">Fluxos finalizados</div>
        <div class="caproq-audit-summary-value">{finalizados_logs}</div>
    </div>
    <div class="caproq-audit-summary-card">
        <div class="caproq-audit-summary-label">Com etapas pendentes</div>
        <div class="caproq-audit-summary-value">{pendentes_logs}</div>
    </div>
</div>
""",
                    unsafe_allow_html=True,
                )

                if df_logs.empty:
                    st.markdown(
                        """
<div class="caproq-audit-empty">
    <strong>Nenhum registro encontrado.</strong><br>
    Ajuste os filtros para ampliar a consulta da trilha de auditoria.
</div>
""",
                        unsafe_allow_html=True,
                    )
                else:
                    for _, row in df_logs.iterrows():
                        try:
                            id_c = int(float(row.get("ID", 0)))
                        except (TypeError, ValueError):
                            id_c = row.get("ID", "—")

                        desc_l = valor_seguro(
                            row.get("Descrição completa do produto", "Sem descrição"),
                            "Sem descrição",
                        )
                        solicitante_nome = valor_seguro(
                            row.get("Nome solicitante", row.get("Nome", "Não informado")),
                            "Não informado",
                        )
                        solicitante_email = valor_seguro(
                            row.get("Endereço de e-mail", "Não informado"),
                            "Não informado",
                        )
                        fornecedor_log = valor_seguro(
                            row.get("Fornecedor", row.get("Nome do fornecedor", "Não informado")),
                            "Não informado",
                        )
                        status_atual_log = valor_seguro(
                            row.get("Status_Final", "Em análise"),
                            "Em análise",
                        )
                        carimbo_abertura = valor_seguro(
                            row.get("Carimbo de data/hora", row.get("Timestamp", "Data não registrada")),
                            "Data não registrada",
                        )

                        titulo_expander_log = (
                            f"🕒 Chamado #{id_c} · {desc_l} · {status_atual_log}"
                        )

                        with st.expander(titulo_expander_log, expanded=False):
                            st.markdown(
                                f"""
<div class="caproq-audit-meta-grid">
    <div class="caproq-audit-meta-card">
        <div class="caproq-audit-meta-label">Solicitante</div>
        <div class="caproq-audit-meta-value">{escape(str(solicitante_nome))}</div>
    </div>
    <div class="caproq-audit-meta-card">
        <div class="caproq-audit-meta-label">E-mail</div>
        <div class="caproq-audit-meta-value">{escape(str(solicitante_email))}</div>
    </div>
    <div class="caproq-audit-meta-card">
        <div class="caproq-audit-meta-label">Fornecedor</div>
        <div class="caproq-audit-meta-value">{escape(str(fornecedor_log))}</div>
    </div>
    <div class="caproq-audit-meta-card">
        <div class="caproq-audit-meta-label">Abertura</div>
        <div class="caproq-audit-meta-value">{escape(str(carimbo_abertura))}</div>
    </div>
</div>
<div class="caproq-audit-section-label">Trilha cronológica do processo</div>
""",
                                unsafe_allow_html=True,
                            )

                            eventos_html_log = [
                                f"""
<div class="caproq-audit-event">
    <span class="caproq-audit-dot info"></span>
    <p class="caproq-audit-event-title">Abertura da solicitação</p>
    <p class="caproq-audit-event-text">
        Processo cadastrado em {escape(str(carimbo_abertura))} por
        <strong>{escape(str(solicitante_nome))}</strong>.
    </p>
</div>
"""
                            ]

                            logs_encontrados = False
                            for info in ALCADAS_INFO.values():
                                c_nome = info["coluna_sheets"]
                                voto_detalhado = valor_seguro(
                                    row.get(c_nome, "Pendente"),
                                    "Pendente",
                                )
                                voto_lower_log = str(voto_detalhado).strip().lower()

                                if voto_lower_log in {"", "pendente", "nan", "none"}:
                                    continue

                                logs_encontrados = True
                                if "reprov" in voto_lower_log:
                                    classe_evento_log = "rejected"
                                    rotulo_evento_log = "Parecer reprovado"
                                elif "ressalva" in voto_lower_log:
                                    classe_evento_log = "warning"
                                    rotulo_evento_log = "Parecer com ressalva"
                                else:
                                    classe_evento_log = "approved"
                                    rotulo_evento_log = "Parecer aprovado"

                                eventos_html_log.append(
                                    f"""
<div class="caproq-audit-event">
    <span class="caproq-audit-dot {classe_evento_log}"></span>
    <p class="caproq-audit-event-title">{escape(str(info['label']))} · {rotulo_evento_log}</p>
    <p class="caproq-audit-event-text">{escape(str(voto_detalhado))}</p>
</div>
"""
                                )

                            status_lower_log = str(status_atual_log).strip().lower()
                            if status_lower_log in {
                                "aprovado",
                                "aprovado com ressalva",
                                "reprovado",
                            }:
                                if "reprov" in status_lower_log:
                                    classe_final_log = "rejected"
                                elif "ressalva" in status_lower_log:
                                    classe_final_log = "warning"
                                else:
                                    classe_final_log = "approved"

                                responsavel_final_log = valor_seguro(
                                    row.get("Responsavel_Homologacao_Final", "Não informado"),
                                    "Não informado",
                                )
                                data_final_log = valor_seguro(
                                    row.get("Data_Homologacao_Final", "Data não registrada"),
                                    "Data não registrada",
                                )
                                consideracoes_log = valor_seguro(
                                    row.get("Consideracoes_Finais_Homologacao", row.get("obs_admin", "Sem considerações registradas")),
                                    "Sem considerações registradas",
                                )

                                eventos_html_log.append(
                                    f"""
<div class="caproq-audit-event">
    <span class="caproq-audit-dot {classe_final_log}"></span>
    <p class="caproq-audit-event-title">Decisão final · {escape(str(status_atual_log))}</p>
    <p class="caproq-audit-event-text">
        Registrada por <strong>{escape(str(responsavel_final_log))}</strong>
        em {escape(str(data_final_log))}.<br>
        {escape(str(consideracoes_log))}
    </p>
</div>
"""
                                )
                            elif not logs_encontrados:
                                eventos_html_log.append(
                                    """
<div class="caproq-audit-event">
    <span class="caproq-audit-dot"></span>
    <p class="caproq-audit-event-title">Aguardando deliberações técnicas</p>
    <p class="caproq-audit-event-text">
        Nenhuma alçada registrou parecer para este chamado até o momento.
    </p>
</div>
"""
                                )

                            st.markdown(
                                "".join(eventos_html_log),
                                unsafe_allow_html=True,
                            )

                            with st.expander("Dados brutos para conferência", expanded=False):
                                dados_auditoria_log = {
                                    "ID": id_c,
                                    "Produto": desc_l,
                                    "Status final": status_atual_log,
                                    "Status dos aprovadores": valor_seguro(
                                        row.get("Status_Aprovadores", "Não informado"),
                                        "Não informado",
                                    ),
                                    "Solicitante": solicitante_nome,
                                    "E-mail": solicitante_email,
                                    "Abertura": carimbo_abertura,
                                }
                                st.json(dados_auditoria_log)

            # ----------------------------------------------------------------------
            # 8.4. Aba "Indicadores"
            # ----------------------------------------------------------------------
            with tab_indicadores:


                # Cópia de trabalho para que filtros e conversões não alterem o dataframe global.
                df_indicadores = df_dados.copy()

                def localizar_coluna(candidatas, termos=None):
                    """Localiza uma coluna por nomes preferenciais ou termos contidos."""
                    for candidata in candidatas:
                        if candidata in df_indicadores.columns:
                            return candidata
                    if termos:
                        for coluna in df_indicadores.columns:
                            nome = str(coluna).lower()
                            if all(termo.lower() in nome for termo in termos):
                                return coluna
                    return None

                col_data_abertura = localizar_coluna(
                    ["Carimbo de data/hora", "Timestamp", "Data_Abertura", "Data de abertura"],
                    ["data"],
                )
                col_data_fechamento = localizar_coluna(
                    ["Data_Homologacao_Final", "Data de homologação final", "Data_Conclusao", "Data de conclusão"]
                )
                col_status = localizar_coluna(["Status_Final", "Status final", "Status"])
                col_setor = localizar_coluna(
                    ["Setor_Solicitante", "Setor solicitante", "Setor", "Área solicitante"]
                )
                col_produto_teste = localizar_coluna(
                    ["Produto_Teste", "Este produto é um Produto de Teste / Piloto?"]
                )

                if col_data_abertura:
                    df_indicadores["_data_abertura_dashboard"] = pd.to_datetime(
                        df_indicadores[col_data_abertura], errors="coerce", dayfirst=True
                    )
                else:
                    df_indicadores["_data_abertura_dashboard"] = pd.NaT

                if col_data_fechamento:
                    df_indicadores["_data_fechamento_dashboard"] = pd.to_datetime(
                        df_indicadores[col_data_fechamento], errors="coerce", dayfirst=True
                    )
                else:
                    df_indicadores["_data_fechamento_dashboard"] = pd.NaT

                if col_status:
                    df_indicadores["_status_dashboard"] = (
                        df_indicadores[col_status].fillna("Não informado").astype(str).str.strip()
                    )
                else:
                    df_indicadores["_status_dashboard"] = "Não informado"

                if col_setor:
                    df_indicadores["_setor_dashboard"] = (
                        df_indicadores[col_setor].fillna("Não informado").astype(str).str.strip()
                    )
                else:
                    df_indicadores["_setor_dashboard"] = "Não informado"

                # ------------------------------------------------------------------
                # Filtros executivos
                # ------------------------------------------------------------------
                st.markdown('<div class="caproq-filter-shell">', unsafe_allow_html=True)
                filtro_1, filtro_2, filtro_3 = st.columns([1.15, 1, 1.35])

                periodos_dashboard = {
                    "Últimos 30 dias": 30,
                    "Últimos 90 dias": 90,
                    "Últimos 12 meses": 365,
                    "Todo o histórico": None,
                }
                with filtro_1:
                    periodo_selecionado = st.selectbox(
                        "Período de abertura",
                        list(periodos_dashboard.keys()),
                        index=2,
                        key="dashboard_periodo",
                    )

                status_disponiveis = sorted(
                    [s for s in df_indicadores["_status_dashboard"].dropna().unique().tolist() if s]
                )
                with filtro_2:
                    status_selecionados = st.multiselect(
                        "Status",
                        status_disponiveis,
                        default=status_disponiveis,
                        key="dashboard_status",
                    )

                setores_disponiveis = sorted(
                    [s for s in df_indicadores["_setor_dashboard"].dropna().unique().tolist() if s]
                )
                with filtro_3:
                    setores_selecionados = st.multiselect(
                        "Setores solicitantes",
                        setores_disponiveis,
                        default=setores_disponiveis,
                        key="dashboard_setores",
                    )
                st.markdown('</div>', unsafe_allow_html=True)

                df_filtrado = df_indicadores.copy()
                dias_periodo = periodos_dashboard[periodo_selecionado]
                if dias_periodo is not None and df_filtrado["_data_abertura_dashboard"].notna().any():
                    data_limite = pd.Timestamp.now().normalize() - pd.Timedelta(days=dias_periodo)
                    df_filtrado = df_filtrado[
                        df_filtrado["_data_abertura_dashboard"] >= data_limite
                    ]
                if status_selecionados:
                    df_filtrado = df_filtrado[
                        df_filtrado["_status_dashboard"].isin(status_selecionados)
                    ]
                else:
                    df_filtrado = df_filtrado.iloc[0:0]
                if setores_selecionados:
                    df_filtrado = df_filtrado[
                        df_filtrado["_setor_dashboard"].isin(setores_selecionados)
                    ]
                else:
                    df_filtrado = df_filtrado.iloc[0:0]

                # ------------------------------------------------------------------
                # KPIs principais
                # ------------------------------------------------------------------
                total_filtrado = len(df_filtrado)
                qtd_analise = int((df_filtrado["_status_dashboard"].str.lower() == "em análise").sum())
                qtd_aprovados = int((df_filtrado["_status_dashboard"].str.lower() == "aprovado").sum())
                qtd_reprovados = int((df_filtrado["_status_dashboard"].str.lower() == "reprovado").sum())
                taxa_aprovacao = (
                    (qtd_aprovados / (qtd_aprovados + qtd_reprovados) * 100)
                    if (qtd_aprovados + qtd_reprovados) > 0
                    else 0.0
                )

                qtd_testes = 0
                if col_produto_teste and col_produto_teste in df_filtrado.columns:
                    qtd_testes = int(
                        df_filtrado[col_produto_teste]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        .isin(["SIM", "S", "YES", "TRUE", "1"])
                        .sum()
                    )

                tempo_medio_dias = None
                if (
                    df_filtrado["_data_abertura_dashboard"].notna().any()
                    and df_filtrado["_data_fechamento_dashboard"].notna().any()
                ):
                    tempos = (
                        df_filtrado["_data_fechamento_dashboard"]
                        - df_filtrado["_data_abertura_dashboard"]
                    ).dt.total_seconds() / 86400
                    tempos = tempos[(tempos >= 0) & tempos.notna()]
                    if not tempos.empty:
                        tempo_medio_dias = float(tempos.mean())

                st.markdown('<div class="caproq-dashboard-section">Visão geral do período</div>', unsafe_allow_html=True)
                kpi_1, kpi_2, kpi_3, kpi_4, kpi_5 = st.columns(5)
                kpi_1.metric("Solicitações", total_filtrado)
                kpi_2.metric("Em análise", qtd_analise)
                kpi_3.metric("Aprovadas", qtd_aprovados)
                kpi_4.metric("Reprovadas", qtd_reprovados)
                kpi_5.metric("Taxa de aprovação", f"{taxa_aprovacao:.1f}%")

                kpi_b1, kpi_b2, kpi_b3 = st.columns(3)
                kpi_b1.metric("Produtos de teste", qtd_testes)
                kpi_b2.metric(
                    "Tempo médio de conclusão",
                    f"{tempo_medio_dias:.1f} dias" if tempo_medio_dias is not None else "Sem dados",
                )
                setores_ativos = int(df_filtrado["_setor_dashboard"].nunique()) if total_filtrado else 0
                kpi_b3.metric("Setores com solicitações", setores_ativos)

                if df_filtrado.empty:
                    st.info("Nenhum chamado corresponde aos filtros selecionados.")
                else:
                    import plotly.express as px
                    import plotly.graph_objects as go

                    # --------------------------------------------------------------
                    # Evolução temporal e status
                    # --------------------------------------------------------------
                    st.markdown('<div class="caproq-dashboard-section">Evolução e composição dos chamados</div>', unsafe_allow_html=True)
                    grafico_1, grafico_2 = st.columns([1.45, 1])

                    with grafico_1:
                        st.markdown(
                            '<div class="caproq-dashboard-card-title">Solicitações abertas por mês</div>'
                            '<div class="caproq-dashboard-card-caption">Tendência de entrada de novos chamados no período filtrado.</div>',
                            unsafe_allow_html=True,
                        )
                        df_temporal = df_filtrado.dropna(subset=["_data_abertura_dashboard"]).copy()
                        if not df_temporal.empty:
                            df_temporal["Mês"] = df_temporal["_data_abertura_dashboard"].dt.to_period("M").dt.to_timestamp()
                            serie_mensal = df_temporal.groupby("Mês").size().reset_index(name="Solicitações")
                            fig_tendencia = px.line(
                                serie_mensal,
                                x="Mês",
                                y="Solicitações",
                                markers=True,
                            )
                            fig_tendencia.update_traces(line=dict(width=3), marker=dict(size=8))
                            fig_tendencia.update_layout(
                                height=320,
                                margin=dict(t=15, b=15, l=10, r=10),
                                xaxis_title=None,
                                yaxis_title="Chamados",
                                hovermode="x unified",
                                legend_title_text="",
                            )
                            st.plotly_chart(fig_tendencia, use_container_width=True)
                        else:
                            st.caption("Não há datas de abertura válidas para montar a evolução temporal.")

                    with grafico_2:
                        st.markdown(
                            '<div class="caproq-dashboard-card-title">Distribuição por status</div>'
                            '<div class="caproq-dashboard-card-caption">Participação atual de cada estágio do fluxo.</div>',
                            unsafe_allow_html=True,
                        )
                        df_status = (
                            df_filtrado["_status_dashboard"]
                            .value_counts()
                            .rename_axis("Status")
                            .reset_index(name="Quantidade")
                        )
                        fig_status = px.pie(
                            df_status,
                            names="Status",
                            values="Quantidade",
                            hole=.58,
                            color="Status",
                            color_discrete_map={
                                "Aprovado": "#2e9d68",
                                "Em análise": "#d6a21f",
                                "Reprovado": "#d04a4a",
                                "Aprovado com ressalva": "#2f7db7",
                            },
                        )
                        fig_status.update_traces(textposition="inside", textinfo="percent+label")
                        fig_status.update_layout(
                            height=320,
                            margin=dict(t=15, b=15, l=10, r=10),
                            showlegend=False,
                        )
                        st.plotly_chart(fig_status, use_container_width=True)

                    # --------------------------------------------------------------
                    # Setores e decisões
                    # --------------------------------------------------------------
                    st.markdown('<div class="caproq-dashboard-section">Origem das solicitações e desfechos</div>', unsafe_allow_html=True)
                    grafico_3, grafico_4 = st.columns(2)

                    with grafico_3:
                        st.markdown(
                            '<div class="caproq-dashboard-card-title">Setores com maior demanda</div>'
                            '<div class="caproq-dashboard-card-caption">Dez principais setores solicitantes no recorte selecionado.</div>',
                            unsafe_allow_html=True,
                        )
                        df_setores = (
                            df_filtrado["_setor_dashboard"]
                            .replace("", "Não informado")
                            .value_counts()
                            .head(10)
                            .sort_values()
                            .rename_axis("Setor")
                            .reset_index(name="Solicitações")
                        )
                        fig_setores = px.bar(
                            df_setores,
                            x="Solicitações",
                            y="Setor",
                            orientation="h",
                            text="Solicitações",
                        )
                        fig_setores.update_traces(textposition="outside", cliponaxis=False)
                        fig_setores.update_layout(
                            height=360,
                            margin=dict(t=15, b=15, l=10, r=30),
                            xaxis_title="Chamados",
                            yaxis_title=None,
                            showlegend=False,
                        )
                        st.plotly_chart(fig_setores, use_container_width=True)

                    with grafico_4:
                        st.markdown(
                            '<div class="caproq-dashboard-card-title">Desfecho das decisões concluídas</div>'
                            '<div class="caproq-dashboard-card-caption">Comparativo entre aprovações, ressalvas identificadas e reprovações.</div>',
                            unsafe_allow_html=True,
                        )
                        aprovacoes_sem_ressalva = 0
                        aprovacoes_com_ressalva = 0
                        recusas = qtd_reprovados

                        for _, linha_ind in df_filtrado.iterrows():
                            status_linha = str(linha_ind.get("_status_dashboard", "")).strip().lower()
                            if status_linha == "aprovado":
                                possui_ressalva = any(
                                    "ressalva" in str(linha_ind.get(info["coluna_sheets"], "")).lower()
                                    for info in ALCADAS_INFO.values()
                                    if info["coluna_sheets"] in df_filtrado.columns
                                )
                                if possui_ressalva:
                                    aprovacoes_com_ressalva += 1
                                else:
                                    aprovacoes_sem_ressalva += 1

                        df_desfechos = pd.DataFrame({
                            "Decisão": ["Aprovado", "Com ressalva", "Reprovado"],
                            "Quantidade": [aprovacoes_sem_ressalva, aprovacoes_com_ressalva, recusas],
                        })
                        fig_desfechos = px.bar(
                            df_desfechos,
                            x="Decisão",
                            y="Quantidade",
                            text="Quantidade",
                            color="Decisão",
                            color_discrete_map={
                                "Aprovado": "#2e9d68",
                                "Com ressalva": "#2f7db7",
                                "Reprovado": "#d04a4a",
                            },
                        )
                        fig_desfechos.update_traces(textposition="outside")
                        fig_desfechos.update_layout(
                            height=360,
                            margin=dict(t=15, b=15, l=10, r=10),
                            xaxis_title=None,
                            yaxis_title="Chamados",
                            showlegend=False,
                        )
                        st.plotly_chart(fig_desfechos, use_container_width=True)

                    # --------------------------------------------------------------
                    # Alçadas técnicas
                    # --------------------------------------------------------------
                    st.markdown('<div class="caproq-dashboard-section">Carga operacional das alçadas</div>', unsafe_allow_html=True)
                    dados_areas = []
                    for _, info_area in ALCADAS_INFO.items():
                        coluna_voto = info_area["coluna_sheets"]
                        if coluna_voto in df_filtrado.columns:
                            votos = df_filtrado[coluna_voto].fillna("Pendente").astype(str).str.strip()
                            concluidos = int(votos.str.startswith(("Aprovar", "Reprovar")).sum())
                            pendentes_area = int((votos == "Pendente").sum())
                            total_area = concluidos + pendentes_area
                            percentual_conclusao = (concluidos / total_area * 100) if total_area else 0
                            dados_areas.append({
                                "Área técnica": info_area["label"],
                                "Pareceres emitidos": concluidos,
                                "Pendências": pendentes_area,
                                "Conclusão (%)": percentual_conclusao,
                            })

                    if dados_areas:
                        df_areas = pd.DataFrame(dados_areas)
                        area_chart, area_table = st.columns([1.25, 1])

                        with area_chart:
                            df_area_long = df_areas.melt(
                                id_vars=["Área técnica"],
                                value_vars=["Pareceres emitidos", "Pendências"],
                                var_name="Situação",
                                value_name="Quantidade",
                            )
                            fig_areas = px.bar(
                                df_area_long,
                                x="Área técnica",
                                y="Quantidade",
                                color="Situação",
                                barmode="group",
                                color_discrete_map={
                                    "Pareceres emitidos": "#2e9d68",
                                    "Pendências": "#d6a21f",
                                },
                            )
                            fig_areas.update_layout(
                                height=390,
                                margin=dict(t=15, b=80, l=10, r=10),
                                xaxis_title=None,
                                yaxis_title="Chamados",
                                legend_title_text="",
                                xaxis_tickangle=-28,
                            )
                            st.plotly_chart(fig_areas, use_container_width=True)

                        with area_table:
                            df_areas_exibicao = df_areas.copy()
                            df_areas_exibicao["Conclusão (%)"] = df_areas_exibicao["Conclusão (%)"].round(1)
                            st.dataframe(
                                df_areas_exibicao,
                                column_config={
                                    "Área técnica": st.column_config.TextColumn("Alçada"),
                                    "Pareceres emitidos": st.column_config.NumberColumn("Emitidos", format="%d"),
                                    "Pendências": st.column_config.NumberColumn("Pendentes", format="%d"),
                                    "Conclusão (%)": st.column_config.ProgressColumn(
                                        "Conclusão",
                                        min_value=0,
                                        max_value=100,
                                        format="%.1f%%",
                                    ),
                                },
                                use_container_width=True,
                                hide_index=True,
                                height=390,
                            )
                    else:
                        st.caption("Não foram localizadas colunas de votação das alçadas na base atual.")

                    st.markdown(
                        f"""
<div class="caproq-dashboard-note">
    <strong>Leitura do painel:</strong> os indicadores consideram <strong>{total_filtrado}</strong>
    chamado(s) após a aplicação dos filtros. O tempo médio de conclusão somente é calculado
    quando existem datas válidas de abertura e homologação final.
</div>
""",
                        unsafe_allow_html=True,
                    )

    # ==============================================================================
    # 8.5. Análise administrativa das alterações de parecer
    # ==============================================================================
    if (
        st.session_state.get("is_admin", False)
        and st.session_state.get("pagina_atual") == "alteracoes_parecer_admin"
    ):
        exigir_admin()

        ui.render_page_header(
            title="Alterações de parecer",
            subtitle="Analise solicitações de revisão antes que qualquer decisão técnica seja substituída.",
            icon="🔄",
        )

        df_alteracoes_admin = carregar_alteracoes_pareceres(forcar_atualizacao=True)
        if df_alteracoes_admin.empty:
            ui.render_empty_state(
                "Nenhuma solicitação registrada",
                "As solicitações enviadas pelos aprovadores aparecerão nesta área.",
                icon="📭",
            )
        else:
            status_admin = df_alteracoes_admin["Status_Alteracao"].astype(str).str.strip()
            pendentes_admin = df_alteracoes_admin[
                status_admin.str.lower().eq(STATUS_ALTERACAO_PENDENTE.lower())
            ].copy()
            confirmadas_admin = int(status_admin.str.lower().eq(STATUS_ALTERACAO_CONFIRMADA.lower()).sum())
            recusadas_admin = int(status_admin.str.lower().eq(STATUS_ALTERACAO_RECUSADA.lower()).sum())

            c1, c2, c3 = st.columns(3)
            c1.metric("Aguardando análise", len(pendentes_admin))
            c2.metric("Confirmadas", confirmadas_admin)
            c3.metric("Recusadas", recusadas_admin)

            if pendentes_admin.empty:
                ui.render_empty_state(
                    "Nenhuma análise pendente",
                    "Todas as solicitações de alteração já foram avaliadas.",
                    icon="✅",
                )
            else:
                pendentes_admin["__data"] = pd.to_datetime(
                    pendentes_admin["Data_Solicitacao"], dayfirst=True, errors="coerce"
                )
                pendentes_admin = pendentes_admin.sort_values("__data", ascending=True)

                for _, alt in pendentes_admin.iterrows():
                    id_alt = str(alt.get("ID_Alteracao", "")).strip()
                    id_chamado_alt = alt.get("ID_Chamado", "")
                    alcada_alt = str(alt.get("Alcada", "")).strip()
                    titulo_alt = (
                        f"Chamado #{id_chamado_alt} · {alcada_alt} · "
                        f"{alt.get('Data_Solicitacao', 'Data não informada')}"
                    )

                    with st.expander(titulo_alt, expanded=False):
                        st.markdown(
                            f"""
                            <div class="caproq-summary-grid">
                                <div class="caproq-summary-card"><div class="caproq-summary-label">Aprovador</div><div class="caproq-summary-value">{escape(str(alt.get('Solicitante_Nome', 'Não informado')))}</div></div>
                                <div class="caproq-summary-card"><div class="caproq-summary-label">E-mail</div><div class="caproq-summary-value">{escape(str(alt.get('Solicitante_Email', 'Não informado')))}</div></div>
                                <div class="caproq-summary-card"><div class="caproq-summary-label">Origem</div><div class="caproq-summary-value">{'Reabertura administrativa' if str(alt.get('Origem_Reabertura', '')).upper() == 'SIM' else 'Fluxo técnico ativo'}</div></div>
                                <div class="caproq-summary-card"><div class="caproq-summary-label">ID da alteração</div><div class="caproq-summary-value">{escape(id_alt)}</div></div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        col_antes, col_depois = st.columns(2)
                        with col_antes:
                            st.markdown("#### Parecer vigente")
                            st.info(f"**Decisão:** {alt.get('Decisao_Anterior', 'Não informada')}")
                            st.write(alt.get("Parecer_Anterior", "Sem parecer descritivo."))
                        with col_depois:
                            st.markdown("#### Alteração proposta")
                            st.warning(f"**Nova decisão:** {alt.get('Decisao_Solicitada', 'Não informada')}")
                            st.write(alt.get("Parecer_Solicitado", "Sem parecer descritivo."))

                        st.markdown("#### Justificativa do aprovador")
                        st.write(alt.get("Justificativa_Alteracao", "Não informada."))

                        with st.form(f"form_analise_alt_{id_alt}"):
                            decisao_admin_alt = st.radio(
                                "Decisão administrativa",
                                ["Confirmar", "Recusar"],
                                horizontal=True,
                                key=f"decisao_admin_alt_{id_alt}",
                            )
                            motivo_recusa_alt = st.text_area(
                                "Motivo da recusa",
                                placeholder="Obrigatório apenas quando a alteração for recusada.",
                                disabled=decisao_admin_alt == "Confirmar",
                                key=f"motivo_recusa_alt_{id_alt}",
                            )
                            ciencia_admin_alt = st.checkbox(
                                "Confirmo que comparei o parecer vigente com a alteração proposta.",
                                key=f"ciencia_admin_alt_{id_alt}",
                            )
                            enviar_analise_alt = st.form_submit_button(
                                "Registrar análise administrativa",
                                use_container_width=True,
                            )

                        if enviar_analise_alt:
                            if not ciencia_admin_alt:
                                ui.render_feedback(
                                    "Confirme a ciência antes de registrar a análise.",
                                    kind="warning",
                                    title="Confirmação necessária",
                                    icon="⚠️",
                                )
                            else:
                                sucesso_alt, retorno_alt = analisar_solicitacao_alteracao(
                                    id_alteracao=id_alt,
                                    decisao_admin=decisao_admin_alt,
                                    admin_nome=user_name,
                                    admin_email=user_email,
                                    motivo_recusa=motivo_recusa_alt,
                                )
                                if sucesso_alt:
                                    mensagem_alt = (
                                        "A alteração foi confirmada, aplicada ao parecer oficial e o fluxo foi recalculado."
                                        if retorno_alt == STATUS_ALTERACAO_CONFIRMADA
                                        else "A alteração foi recusada e o parecer vigente foi preservado."
                                    )
                                    ui.render_feedback(
                                        mensagem_alt,
                                        kind="success" if retorno_alt == STATUS_ALTERACAO_CONFIRMADA else "warning",
                                        title="Análise registrada",
                                        icon="✅" if retorno_alt == STATUS_ALTERACAO_CONFIRMADA else "↩️",
                                    )
                                    st.rerun()
                                else:
                                    ui.render_feedback(
                                        retorno_alt,
                                        kind="error",
                                        title="Não foi possível registrar",
                                        icon="⛔",
                                    )

            with st.expander("Histórico de solicitações analisadas", expanded=False):
                historico_alt_admin = df_alteracoes_admin[
                    ~status_admin.str.lower().eq(STATUS_ALTERACAO_PENDENTE.lower())
                ].copy()
                if historico_alt_admin.empty:
                    st.caption("Nenhuma análise concluída até o momento.")
                else:
                    colunas_historico_alt = [
                        "ID_Alteracao", "ID_Chamado", "Alcada", "Decisao_Anterior",
                        "Decisao_Solicitada", "Status_Alteracao", "Admin_Responsavel",
                        "Data_Analise", "Motivo_Recusa",
                    ]
                    st.dataframe(
                        historico_alt_admin[[c for c in colunas_historico_alt if c in historico_alt_admin.columns]],
                        use_container_width=True,
                        hide_index=True,
                    )

    # ==============================================================================
    # 9. Segunda Etapa: Homologação e Decisão Final (Exclusivo Administradores)
    # ==============================================================================
    if (
        st.session_state.get("is_admin", False)
        and st.session_state.get("pagina_atual") == "homologacao_final"
    ):
        exigir_admin()


        if df_dados.empty:
            ui.render_empty_state("Nenhum dado para homologação", "A base de solicitações está vazia. Novos chamados aparecerão aqui após o registro.", icon="🛡️")
        elif "Status_Aprovadores" not in df_dados.columns:
            st.warning(
                "⚠️ A coluna 'Status_Aprovadores' não foi localizada na planilha."
            )
        else:
            status_validos_admin = [
                "Aguardando homologação",
                "Reunião Necessária",
                "Reunião necessária",
            ]

            chamados_para_decisao = df_dados[
                (df_dados["Status_Final"] == "Em análise")
                & (
                    df_dados["Status_Aprovadores"]
                    .astype(str)
                    .str.strip()
                    .isin(status_validos_admin)
                )
            ]

            st.markdown("### Reabertura para revisão técnica")
            st.caption(
                "Use esta operação quando uma alçada precisar revisar o parecer de um processo que já chegou à homologação ou foi finalizado."
            )

            status_final_normalizado = df_dados.get(
                "Status_Final", pd.Series(index=df_dados.index, dtype=str)
            ).astype(str).str.strip().str.lower()
            status_aprov_normalizado = df_dados.get(
                "Status_Aprovadores", pd.Series(index=df_dados.index, dtype=str)
            ).astype(str).str.strip().str.lower()
            status_revisao_normalizado = df_dados.get(
                "Status_Revisao", pd.Series(index=df_dados.index, dtype=str)
            ).astype(str).str.strip().str.lower()

            candidatos_reabertura = df_dados[
                (
                    ~status_final_normalizado.isin(["", "em análise", "em analise", "nan", "none"])
                    | status_aprov_normalizado.isin([
                        "aguardando homologação", "aguardando homologacao",
                        "em homologação", "em homologacao",
                        "reunião necessária", "reuniao necessaria",
                    ])
                )
                & ~status_revisao_normalizado.isin([
                    STATUS_REVISAO_REABERTO.lower(),
                    STATUS_REVISAO_AGUARDANDO_ALTERACAO.lower(),
                    STATUS_REVISAO_ALTERACAO_EM_ANALISE.lower(),
                    STATUS_REVISAO_ALTERACAO_CONFIRMADA.lower(),
                ])
            ].copy()

            with st.expander("Reabrir chamado", expanded=False):
                if candidatos_reabertura.empty:
                    st.caption("Nenhum chamado está elegível para reabertura neste momento.")
                else:
                    opcoes_reabertura = {}
                    for _, candidato in candidatos_reabertura.sort_values("ID", ascending=False).iterrows():
                        descricao_candidato = valor_seguro(
                            candidato.get(
                                "Descrição completa do produto",
                                candidato.get("Descrição do produto", candidato.get("Descricao_Produto", "Produto não informado")),
                            )
                        )
                        rotulo = (
                            f"Chamado #{candidato.get('ID')} · {descricao_candidato} · "
                            f"{valor_seguro(candidato.get('Status_Final', candidato.get('Status_Aprovadores', '')))}"
                        )
                        opcoes_reabertura[rotulo] = candidato.get("ID")

                    with st.form("form_reabrir_homologacao"):
                        chamado_reabrir_rotulo = st.selectbox(
                            "Chamado",
                            list(opcoes_reabertura.keys()),
                        )
                        alcadas_reabrir = [info["label"] for info in ALCADAS_INFO.values()]
                        alcada_reabrir = st.selectbox("Alçada que deverá revisar o parecer", alcadas_reabrir)
                        motivo_reabrir = st.text_area(
                            "Motivo da reabertura",
                            placeholder="Descreva o fato novo, documento complementar ou razão técnica que justifica a revisão.",
                        )
                        confirmar_reabrir = st.checkbox(
                            "Estou ciente de que o processo sairá da homologação e deverá retornar para uma nova decisão final."
                        )
                        enviar_reabertura = st.form_submit_button(
                            "Reabrir para revisão técnica",
                            use_container_width=True,
                        )

                    if enviar_reabertura:
                        if not confirmar_reabrir:
                            ui.render_feedback(
                                "Confirme a ciência para concluir a reabertura.",
                                kind="warning",
                                title="Confirmação necessária",
                                icon="⚠️",
                            )
                        elif len(str(motivo_reabrir).strip()) < 10:
                            ui.render_feedback(
                                "Informe um motivo claro para a reabertura, com pelo menos 10 caracteres.",
                                kind="warning",
                                title="Motivo insuficiente",
                                icon="📝",
                            )
                        else:
                            sucesso_reab, retorno_reab = reabrir_chamado_para_revisao(
                                id_chamado=opcoes_reabertura[chamado_reabrir_rotulo],
                                alcada=alcada_reabrir,
                                motivo=motivo_reabrir,
                                admin_nome=user_name,
                                admin_email=user_email,
                            )
                            if sucesso_reab:
                                ui.render_feedback(
                                    f"Chamado reaberto com sucesso. Protocolo: {retorno_reab}",
                                    kind="success",
                                    title="Reabertura registrada",
                                    icon="🔓",
                                )
                                st.rerun()
                            else:
                                ui.render_feedback(
                                    retorno_reab,
                                    kind="error",
                                    title="Não foi possível reabrir",
                                    icon="⛔",
                                )

            st.markdown("---")

            if chamados_para_decisao.empty:
                ui.render_empty_state(
                    "Nenhuma decisão pendente",
                    "No momento, não há chamados aguardando homologação final ou reunião técnica.",
                    icon="✅",
                )
            else:
                total_homologacao = len(chamados_para_decisao)
                total_reuniao = chamados_para_decisao[
                    chamados_para_decisao["Status_Aprovadores"]
                    .astype(str)
                    .str.lower()
                    .str.contains("reunião|reuniao", regex=True)
                ].shape[0]
                total_teste = chamados_para_decisao.get(
                    "Produto_Teste", pd.Series(index=chamados_para_decisao.index, dtype=str)
                ).astype(str).str.strip().str.upper().eq("SIM").sum()

                metrica_1, metrica_2, metrica_3 = st.columns(3)
                metrica_1.metric("Aguardando decisão", total_homologacao)
                metrica_2.metric("Produtos de teste", int(total_teste))
                metrica_3.metric("Com reunião indicada", total_reuniao)
                st.caption(
                    "Abra um chamado para visualizar o resumo executivo, os pareceres técnicos e o formulário de decisão final."
                )

                for _, row in chamados_para_decisao.iterrows():
                    id_chamado = row["ID"]
                    status_apr = row["Status_Aprovadores"]

                    col_prod = (
                        "Descrição completa do produto"
                        if "Descrição completa do produto" in row
                        else "Descrição do produto"
                        if "Descrição do produto" in row
                        else "Descricao_Produto"
                    )
                    descricao_produto = str(row.get(col_prod, "Sem descrição"))

                    data_abertura = row.get(
                        "Carimbo de data/hora", row.get("Timestamp", "")
                    )
                    try:
                        data_abertura_formatada = pd.to_datetime(
                            data_abertura, dayfirst=True
                        ).strftime("%d/%m/%Y às %H:%M")
                    except Exception:
                        data_abertura_formatada = valor_seguro(data_abertura)

                    titulo_homologacao = (
                        f"Chamado #{id_chamado} · {descricao_produto} · "
                        f"{data_abertura_formatada}"
                    )

                    with st.expander(titulo_homologacao, expanded=False):
                        eh_produto_teste = (
                            str(row.get("Produto_Teste", "NÃO"))
                            .strip()
                            .upper()
                            == "SIM"
                        )

                        nome_solicitante_resumo = valor_seguro(
                            row.get("Nome solicitante", row.get("Nome", "Não informado"))
                        )
                        setor_solicitante_resumo = valor_seguro(
                            row.get("Setor_Solicitante", row.get("Setor", "Não informado"))
                        )
                        fornecedor_resumo = valor_seguro(
                            row.get("Fornecedor", row.get("Nome do fornecedor", "Não informado"))
                        )
                        tipo_resumo = "Produto de teste / piloto" if eh_produto_teste else "Solicitação padrão"
                        status_seguro = escape(valor_seguro(status_apr))
                        st.markdown(
                            f"""
                            <div class="caproq-summary-grid">
                                <div class="caproq-summary-card"><div class="caproq-summary-label">Solicitante</div><div class="caproq-summary-value">{escape(nome_solicitante_resumo)}</div></div>
                                <div class="caproq-summary-card"><div class="caproq-summary-label">Setor</div><div class="caproq-summary-value">{escape(setor_solicitante_resumo)}</div></div>
                                <div class="caproq-summary-card"><div class="caproq-summary-label">Fornecedor</div><div class="caproq-summary-value">{escape(fornecedor_resumo)}</div></div>
                                <div class="caproq-summary-card"><div class="caproq-summary-label">Modalidade</div><div class="caproq-summary-value">{escape(tipo_resumo)}</div></div>
                            </div>
                            <div class="caproq-decision-box"><b>Status do fluxo técnico:</b> {status_seguro}</div>
                            """,
                            unsafe_allow_html=True,
                        )

                        if eh_produto_teste:
                            st.warning(
                                "🧪 Este chamado refere-se a um Produto de "
                                "Teste / Piloto."
                            )
                            st.markdown(
                                "#### 📦 Informações do Produto Teste"
                            )

                            with st.expander(
                                "Visualizar informações fornecidas pelo solicitante",
                                expanded=True,
                            ):
                                col_teste_1, col_teste_2 = st.columns(2)

                                with col_teste_1:
                                    st.markdown(
                                        "**Classificação do item no HMV:**  \n"
                                        f"{valor_seguro(row.get('Motivo_Teste'))}"
                                    )
                                    st.markdown(
                                        "**Consumo estimado por mês:**  \n"
                                        f"{valor_seguro(row.get('Consumo_Mes_Teste'))}"
                                    )
                                    st.markdown(
                                        "**Quantidade destinada ao teste:**  \n"
                                        f"{valor_seguro(row.get('Quantidade_Teste'))}"
                                    )
                                    st.markdown(
                                        "**Setores onde o teste será realizado:**  \n"
                                        f"{valor_seguro(row.get('Setor_Destino_Teste'))}"
                                    )

                                with col_teste_2:
                                    st.markdown(
                                        "**Setor solicitante:**  \n"
                                        f"{valor_seguro(row.get('Setor_Solicitante'))}"
                                    )
                                    st.markdown(
                                        "**Telefone ou ramal do setor:**  \n"
                                        f"{valor_seguro(row.get('Ramal_Solicitante'))}"
                                    )
                                    st.markdown(
                                        "**Gerente ou coordenador responsável:**  \n"
                                        f"{valor_seguro(row.get('Responsavel_Area'))}"
                                    )

                        st.markdown(
                            '<div class="caproq-section-title">📋 Panorama das alçadas técnicas</div>',
                            unsafe_allow_html=True,
                        )
                        cards_votos = []
                        for _, info in ALCADAS_INFO.items():
                            voto_atual = str(row.get(info["coluna_sheets"], "Pendente"))
                            voto_lower = voto_atual.lower()
                            if "aprovar" in voto_lower and "ressalva" not in voto_lower:
                                rotulo_voto, icone_voto = "Aprovado", "●"
                                fundo_voto, borda_voto = "rgba(0,141,76,.11)", "rgba(0,141,76,.32)"
                            elif "ressalva" in voto_lower:
                                rotulo_voto, icone_voto = "Com ressalva", "●"
                                fundo_voto, borda_voto = "rgba(230,162,60,.13)", "rgba(230,162,60,.38)"
                            elif "reprovar" in voto_lower:
                                rotulo_voto, icone_voto = "Reprovado", "●"
                                fundo_voto, borda_voto = "rgba(217,48,37,.11)", "rgba(217,48,37,.34)"
                            else:
                                rotulo_voto, icone_voto = "Pendente", "○"
                                fundo_voto, borda_voto = "rgba(128,128,128,.08)", "rgba(128,128,128,.25)"
                            cards_votos.append(
                                f'<div class="caproq-score-card" style="--score-bg:{fundo_voto};--score-border:{borda_voto}">'
                                f'<div class="caproq-score-label">{escape(info["label"])}</div>'
                                f'<div class="caproq-score-status">{icone_voto} {rotulo_voto}</div></div>'
                            )
                        st.markdown(
                            '<div class="caproq-score-grid">' + ''.join(cards_votos) + '</div>',
                            unsafe_allow_html=True,
                        )

                        with st.expander(
                            "💬 Pareceres completos das alçadas", expanded=False
                        ):
                            for _, info in ALCADAS_INFO.items():
                                voto_detalhado = valor_seguro(
                                    row.get(info["coluna_sheets"], "Pendente")
                                )
                                st.markdown(
                                    f'<div class="caproq-parecer-card">'
                                    f'<div class="caproq-parecer-head">{escape(info["label"])}</div>'
                                    f'<div class="caproq-parecer-text">{escape(voto_detalhado)}</div>'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )

                        if eh_produto_teste:
                            st.markdown("---")
                            st.markdown(
                                '<div class="caproq-section-title">🧪 Avaliação técnica do produto de teste</div>',
                                unsafe_allow_html=True,
                            )
                            st.info(
                                "Preencha os dados técnicos referentes ao teste "
                                "realizado."
                            )

                            with st.expander(
                                "Preencher avaliação técnica do produto",
                                expanded=True,
                            ):
                                col_rms_1, col_rms_2 = st.columns(2)

                                with col_rms_1:
                                    rms_produto = st.text_input(
                                        "RMS do produto",
                                        placeholder="Informe o RMS do produto",
                                        key=f"rms_produto_{id_chamado}",
                                    )

                                with col_rms_2:
                                    validade_rms = st.date_input(
                                        "Validade do RMS",
                                        value=None,
                                        format="DD/MM/YYYY",
                                        key=f"validade_rms_{id_chamado}",
                                    )

                                col_carac_1, col_carac_2 = st.columns(2)

                                with col_carac_1:
                                    pode_ser_rediluido = st.radio(
                                        "Pode ser REDILUÍDO?",
                                        options=["SIM", "NÃO", "NA"],
                                        index=None,
                                        horizontal=True,
                                        key=f"rediluido_{id_chamado}",
                                    )

                                with col_carac_2:
                                    necessita_monitoramento = st.radio(
                                        "Necessário monitoramento ocupacional?",
                                        options=["SIM", "NÃO", "NA"],
                                        index=None,
                                        horizontal=True,
                                        key=f"monitoramento_{id_chamado}",
                                    )

                                resultado_teste = st.radio(
                                    "Resultado do teste",
                                    options=[
                                        "APROVADO",
                                        "REPROVADO",
                                        "NÃO REALIZADO",
                                    ],
                                    index=None,
                                    horizontal=True,
                                    key=f"resultado_teste_{id_chamado}",
                                )

                                data_resultado_teste = st.date_input(
                                    "Data do resultado do teste",
                                    value=None,
                                    format="DD/MM/YYYY",
                                    key=f"data_teste_{id_chamado}",
                                )

                                parecer_resultado_teste = st.text_area(
                                    "Parecer sobre o resultado do teste",
                                    placeholder=(
                                        "Descreva obrigatoriamente o parecer, "
                                        "independentemente do resultado."
                                    ),
                                    height=120,
                                    key=f"parecer_teste_{id_chamado}",
                                )

                                indicado_padronizacao = st.radio(
                                    "Indicado para PADRONIZAÇÃO?",
                                    options=["SIM", "NÃO"],
                                    index=None,
                                    horizontal=True,
                                    key=f"indicado_padronizacao_{id_chamado}",
                                )

                                data_indicacao_padronizacao = st.date_input(
                                    "Data da indicação para padronização",
                                    value=None,
                                    format="DD/MM/YYYY",
                                    key=f"data_padronizacao_{id_chamado}",
                                )

                                parecer_indicacao_padronizacao = st.text_area(
                                    "Parecer sobre a indicação para padronização",
                                    placeholder=(
                                        "Descreva obrigatoriamente o parecer, "
                                        "independentemente da indicação."
                                    ),
                                    height=120,
                                    key=f"parecer_padronizacao_{id_chamado}",
                                )

                        st.markdown(
                            '<div class="caproq-section-title">✅ Validações de encerramento</div>',
                            unsafe_allow_html=True,
                        )
                        st.info(
                            "Estas questões devem ser respondidas para todos os "
                            "chamados, independentemente de o produto ter sido "
                            "marcado como teste."
                        )

                        produto_aprovado = st.radio(
                            "1. Padronização: o produto foi aprovado?",
                            options=["SIM", "NÃO"],
                            index=None,
                            horizontal=True,
                            key=f"homologacao_produto_aprovado_{id_chamado}",
                        )

                        produto_padronizado = st.radio(
                            "2. Padronização: o produto foi padronizado?",
                            options=["SIM", "NÃO"],
                            index=None,
                            horizontal=True,
                            key=f"homologacao_produto_padronizado_{id_chamado}",
                        )

                        codigo_padronizacao = st.text_input(
                            "Código do produto padronizado",
                            placeholder="Informe o código do produto",
                            disabled=produto_padronizado != "SIM",
                            key=f"homologacao_codigo_padronizacao_{id_chamado}",
                        )

                        produto_comprado = st.radio(
                            "3. Solicitante: o produto foi comprado?",
                            options=["SIM", "NÃO"],
                            index=None,
                            horizontal=True,
                            key=f"homologacao_produto_comprado_{id_chamado}",
                        )

                        inventario_perigosos = st.radio(
                            (
                                "4. Segurança Ocupacional: o produto foi incluído "
                                "no inventário de produtos perigosos e o inventário "
                                "foi atualizado no PGR?"
                            ),
                            options=["SIM", "NÃO", "NA"],
                            index=None,
                            horizontal=True,
                            key=f"homologacao_inventario_perigosos_{id_chamado}",
                        )

                        fispq_setor = st.radio(
                            (
                                "5. Segurança Ocupacional: a FISPQ já está no "
                                "setor solicitante?"
                            ),
                            options=["SIM", "NÃO", "NA"],
                            index=None,
                            horizontal=True,
                            key=f"homologacao_fispq_setor_{id_chamado}",
                        )

                        st.markdown(
                            '<div class="caproq-section-title">🛡️ Deliberação administrativa final</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            '<div class="caproq-decision-box"><b>Decisão institucional</b><br><span style="opacity:.75">Considere os pareceres técnicos e registre abaixo o veredito que encerrará oficialmente o chamado.</span></div>',
                            unsafe_allow_html=True,
                        )
                        decisao_final_admin = st.radio(
                            "6. Decisão administrativa final do chamado:",
                            options=[
                                "Aprovado",
                                "Aprovado com ressalva",
                                "Reprovado",
                            ],
                            index=None,
                            horizontal=True,
                            help=(
                                "A decisão final pertence exclusivamente aos "
                                "administradores. Os pareceres das áreas são "
                                "subsídios técnicos para esta deliberação."
                            ),
                            key=f"decisao_final_admin_{id_chamado}",
                        )

                        obs_admin = st.text_area(
                            (
                                "✍️ Considerações finais do comitê / "
                                "Justificativa do veredito:"
                            ),
                            placeholder=(
                                "Registre observações, ressalvas, decisões de "
                                "consenso ou justificativas relevantes para o "
                                "encerramento."
                            ),
                            height=140,
                            key=f"admin_obs_{id_chamado}",
                        )

                        respostas_finais_preenchidas = all(
                            [
                                produto_aprovado is not None,
                                produto_padronizado is not None,
                                produto_comprado is not None,
                                inventario_perigosos is not None,
                                fispq_setor is not None,
                                decisao_final_admin is not None,
                            ]
                        )

                        codigo_padronizacao_valido = (
                            produto_padronizado != "SIM"
                            or bool(str(codigo_padronizacao).strip())
                        )

                        campos_teste_preenchidos = True
                        dados_homologacao_teste = {}

                        if eh_produto_teste:
                            campos_teste_preenchidos = all(
                                [
                                    bool(str(rms_produto).strip()),
                                    validade_rms is not None,
                                    pode_ser_rediluido is not None,
                                    necessita_monitoramento is not None,
                                    resultado_teste is not None,
                                    data_resultado_teste is not None,
                                    bool(str(parecer_resultado_teste).strip()),
                                    indicado_padronizacao is not None,
                                    data_indicacao_padronizacao is not None,
                                    bool(
                                        str(
                                            parecer_indicacao_padronizacao
                                        ).strip()
                                    ),
                                ]
                            )

                            dados_homologacao_teste = {
                                "RMS_Produto": str(rms_produto).strip(),
                                "Validade_RMS": (
                                    validade_rms.strftime("%d/%m/%Y")
                                    if validade_rms
                                    else ""
                                ),
                                "Pode_Ser_Rediluido": (
                                    pode_ser_rediluido or ""
                                ),
                                "Necessita_Monitoramento_Ocupacional": (
                                    necessita_monitoramento or ""
                                ),
                                "Resultado_Teste": resultado_teste or "",
                                "Data_Resultado_Teste": (
                                    data_resultado_teste.strftime("%d/%m/%Y")
                                    if data_resultado_teste
                                    else ""
                                ),
                                "Parecer_Resultado_Teste": str(
                                    parecer_resultado_teste
                                ).strip(),
                                "Indicado_Para_Padronizacao": (
                                    indicado_padronizacao or ""
                                ),
                                "Data_Indicacao_Padronizacao": (
                                    data_indicacao_padronizacao.strftime(
                                        "%d/%m/%Y"
                                    )
                                    if data_indicacao_padronizacao
                                    else ""
                                ),
                                "Parecer_Indicacao_Padronizacao": str(
                                    parecer_indicacao_padronizacao
                                ).strip(),
                            }

                        if produto_padronizado == "SIM":
                            resposta_produto_padronizado = (
                                "SIM - Código: "
                                f"{str(codigo_padronizacao).strip()}"
                            )
                        elif produto_padronizado == "NÃO":
                            resposta_produto_padronizado = "NÃO"
                        else:
                            resposta_produto_padronizado = ""

                        dados_homologacao_padrao = {
                            "Decisao_Final_Admin": decisao_final_admin or "",
                            "Padronização: o produto foi aprovado?": (
                                produto_aprovado or ""
                            ),
                            (
                                "Padronização: o produto foi padronizado? "
                                "Qual o cód.?"
                            ): resposta_produto_padronizado,
                            "Solicitante: o produto foi comprado?": (
                                produto_comprado or ""
                            ),
                            (
                                "Segurança Ocupacional: o produto foi incluído "
                                "no inventário de prod. perigosos? E inventário "
                                "atualizado no PRG?"
                            ): inventario_perigosos or "",
                            (
                                "Segurança Ocupacional: a FISPQ já está no "
                                "setor solicitante?"
                            ): fispq_setor or "",
                        }

                        if st.button(
                            f"Firmar decisão final - Chamado #{id_chamado}",
                            key=f"btn_admin_final_{id_chamado}",
                            type="primary",
                            use_container_width=True,
                        ):
                            if not respostas_finais_preenchidas:
                                st.error(
                                    "❌ Responda às perguntas finais e selecione "
                                    "a decisão administrativa do chamado."
                                )
                            elif not codigo_padronizacao_valido:
                                st.error(
                                    "❌ Informe o código do produto padronizado."
                                )
                            elif (
                                eh_produto_teste
                                and not campos_teste_preenchidos
                            ):
                                st.error(
                                    "❌ Preencha todos os campos obrigatórios "
                                    "da avaliação técnica do Produto Teste."
                                )
                            elif not str(obs_admin).strip():
                                st.error(
                                    "❌ É obrigatório preencher as considerações "
                                    "finais para fins de auditoria e registro."
                                )
                            else:
                                fuso_br = datetime.timezone(
                                    datetime.timedelta(hours=-3)
                                )
                                timestamp_homologacao = datetime.datetime.now(
                                    fuso_br
                                ).strftime("%d/%m/%Y %H:%M")

                                responsavel_homologacao = (
                                    st.session_state.get("name")
                                    or st.session_state.get("email")
                                    or user_name
                                )

                                status_final_texto = decisao_final_admin
                                if decisao_final_admin == "Aprovado":
                                    emoji_resultado = "✅ APROVADO"
                                    cor_resultado = "#008D4C"
                                elif decisao_final_admin == "Aprovado com ressalva":
                                    emoji_resultado = "⚠️ APROVADO COM RESSALVA"
                                    cor_resultado = "#E6A23C"
                                else:
                                    emoji_resultado = "❌ REPROVADO"
                                    cor_resultado = "#D93025"

                                respostas_resumo = (
                                    f"Produto aprovado: {produto_aprovado} | "
                                    "Produto padronizado: "
                                    f"{resposta_produto_padronizado} | "
                                    f"Produto comprado: {produto_comprado} | "
                                    "Inventário de produtos perigosos/PGR: "
                                    f"{inventario_perigosos} | "
                                    "FISPQ no setor solicitante: "
                                    f"{fispq_setor}"
                                )

                                resumo_produto_teste = ""
                                if eh_produto_teste:
                                    resumo_produto_teste = (
                                        f" | RMS: {str(rms_produto).strip()} "
                                        "| Validade RMS: "
                                        f"{validade_rms.strftime('%d/%m/%Y')} "
                                        "| Pode ser rediluído: "
                                        f"{pode_ser_rediluido} "
                                        "| Monitoramento ocupacional: "
                                        f"{necessita_monitoramento} "
                                        "| Resultado do teste: "
                                        f"{resultado_teste} "
                                        "| Data do teste: "
                                        f"{data_resultado_teste.strftime('%d/%m/%Y')} "
                                        "| Indicado para padronização: "
                                        f"{indicado_padronizacao} "
                                        "| Data da indicação: "
                                        f"{data_indicacao_padronizacao.strftime('%d/%m/%Y')}"
                                    )

                                historico_admin_completo = (
                                    f"{status_final_texto} "
                                    f"({timestamp_homologacao} - por "
                                    f"{responsavel_homologacao}: "
                                    f"[{respostas_resumo}"
                                    f"{resumo_produto_teste}] "
                                    f"{str(obs_admin).strip().replace(chr(10), ' ')})"
                                )

                                mascara_chamado = (
                                    df_dados["ID"].astype(str)
                                    == str(id_chamado)
                                )

                                colunas_texto_homologacao = [
                                    "Status_Final",
                                    "Parecer_Final_Admin",
                                    "Data_Homologacao_Final",
                                    "Responsavel_Homologacao_Final",
                                    "Consideracoes_Finais_Homologacao",
                                ]

                                colunas_texto_homologacao.extend(
                                    dados_homologacao_padrao.keys()
                                )

                                if eh_produto_teste:
                                    colunas_texto_homologacao.extend(
                                        dados_homologacao_teste.keys()
                                    )

                                for coluna_texto in colunas_texto_homologacao:
                                    if coluna_texto not in df_dados.columns:
                                        df_dados[coluna_texto] = ""

                                    df_dados[coluna_texto] = (
                                        df_dados[coluna_texto]
                                        .astype("object")
                                    )

                                df_dados.loc[
                                    mascara_chamado, "Status_Final"
                                ] = status_final_texto
                                df_dados.loc[
                                    mascara_chamado, "Parecer_Final_Admin"
                                ] = historico_admin_completo
                                df_dados.loc[
                                    mascara_chamado, "Data_Homologacao_Final"
                                ] = timestamp_homologacao
                                df_dados.loc[
                                    mascara_chamado,
                                    "Responsavel_Homologacao_Final",
                                ] = responsavel_homologacao
                                df_dados.loc[
                                    mascara_chamado,
                                    "Consideracoes_Finais_Homologacao",
                                ] = str(obs_admin).strip()

                                for nome_coluna, valor_coluna in (
                                    dados_homologacao_padrao.items()
                                ):
                                    df_dados.loc[
                                        mascara_chamado, nome_coluna
                                    ] = valor_coluna

                                if eh_produto_teste:
                                    for nome_coluna, valor_coluna in (
                                        dados_homologacao_teste.items()
                                    ):
                                        df_dados.loc[
                                            mascara_chamado, nome_coluna
                                        ] = valor_coluna

                                email_solicitante = row.get(
                                    "Endereço de e-mail", ""
                                )
                                nome_solicitante = row.get(
                                    "Nome solicitante",
                                    row.get("Nome", "Solicitante"),
                                )

                                detalhes_pareceres = "".join(
                                    f"<li><b>{inf['label']}:</b> "
                                    f"{valor_seguro(row.get(inf['coluna_sheets'], 'Pendente'))}</li>"
                                    for inf in ALCADAS_INFO.values()
                                )
                                detalhes_final = f"""
                                <div style="margin-top:20px;padding:16px;background:#f8f9fa;
                                            border-left:4px solid {cor_resultado};border-radius:4px;">
                                  <p style="margin:0 0 8px;"><b>Chamado:</b> #{id_chamado}</p>
                                  <p style="margin:0 0 8px;"><b>Produto:</b> {descricao_produto}</p>
                                  <p style="margin:0 0 8px;"><b>Resultado final:</b> {emoji_resultado}</p>
                                  <p style="margin:0;"><b>Deliberação:</b> {str(obs_admin).strip()}</p>
                                </div>
                                <h3 style="font-size:16px;margin:22px 0 8px;">Pareceres das áreas</h3>
                                <ul style="padding-left:20px;line-height:1.55;">{detalhes_pareceres}</ul>
                                """
                                html_encerramento = template_email_caproq(
                                    titulo=f"Resultado final do Chamado #{id_chamado}",
                                    mensagem=(
                                        f"Olá, <b>{nome_solicitante}</b>. O processo de avaliação "
                                        f"técnica e homologação do produto <b>{descricao_produto}</b> "
                                        "foi concluído. A decisão abaixo foi registrada pelos "
                                        "administradores após análise dos pareceres das áreas."
                                    ),
                                    detalhes=detalhes_final,
                                    destaque=cor_resultado,
                                )

                                try:
                                    conn.update(data=df_dados)

                                    st.session_state["df_dados_cache"] = df_dados.copy()
                                    st.session_state["df_dados_cache_timestamp"] = time.time()

                                    destinatarios_resultado = emails_unicos(
                                        [email_solicitante, todos_emails_aprovadores()]
                                    )
                                    for destinatario_resultado in destinatarios_resultado:
                                        enviar_email(
                                            destinatario=destinatario_resultado,
                                            assunto=(
                                                f"CAPROQ: {status_final_texto} - "
                                                f"Chamado #{id_chamado}"
                                            ),
                                            corpo_html=html_encerramento,
                                        )

                                    st.success(
                                        f"🎉 Chamado #{id_chamado} deliberado "
                                        "e encerrado com sucesso!"
                                    )
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(
                                        "❌ Erro ao salvar a deliberação final "
                                        f"na planilha: {e}"
                                    )

else:

# ==============================================================================
# 10. Tela solicitantes
# ==============================================================================
    
    tab_novo, tab_status = st.tabs(["📝 Nova solicitação", "📚 Meus chamados"])
    
    with tab_novo:
        st.markdown("<div class='caproq-required-note'>Os campos identificados com <b>*</b> são obrigatórios.</div>", unsafe_allow_html=True)
        
        PASTA_DRIVE_ID = "1YM8-vbxx0nMKD_5b0xZ8plr_iw7I9k7R"
        
        # Cria um inicializador de versão para resetar os widgets de upload e chaves de input
        if "form_version" not in st.session_state:
            st.session_state["form_version"] = 0
            
        v = st.session_state["form_version"]
    
        CONFIG_CAMPOS = [
            # SEÇÃO 1: Identificação do produto e fornecedor
            {"id": f"descricao_{v}", "label": "Descrição completa do produto", "tipo": "area_texto", "secao": "Dados do Produto", "obrigatorio": True},
            {"id": f"apresentacao_{v}", "label": "Apresentação/volume", "tipo": "texto", "secao": "Dados do Produto", "obrigatorio": True},
            {"id": f"area_uso_{v}", "label": "Área onde será utilizado e indicação detalhada de uso do produto", "tipo": "area_texto", "secao": "Dados do Produto", "obrigatorio": True},
            {"id": f"fabricante_{v}", "label": "Fabricante/fornecedor", "tipo": "texto", "secao": "Dados do Produto", "obrigatorio": True},
            {"id": f"contato_fornecedor_{v}", "label": "Informações de contato do fornecedor (nome, e-mail e telefone)", "tipo": "area_texto", "secao": "Dados do Produto", "obrigatorio": True},
            
            # SEÇÃO 2: Dependências e processos
            {"id": f"insumos_associados_{v}", "label": "Equipamentos e/ou insumos associados ao uso do produto? Se SIM, quais?", "tipo": "area_texto", "secao": "Processos e Dependências", "obrigatorio": False},
            {"id": f"sem_produto_{v}", "label": "Explique como o procedimento/atividade atual é realizado SEM este produto:", "tipo": "area_texto", "secao": "Processos e Dependências", "obrigatorio": True},

            # SEÇÃO 3: Avaliação de impacto e riscos
            {"id": f"reducao_tempo_{v}", "label": "O produto contribui para a redução de tempo de execução dos procedimentos?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": f"reducao_acidentes_{v}", "label": "O produto proposto contribui para a redução do risco de acidentes de trabalho?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": f"seguranca_paciente_{v}", "label": "O produto favorece a segurança do paciente e dos profissionais?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": f"reducao_infeccao_{v}", "label": "O produto proposto contribui para a redução de risco de infecção hospitalar?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": f"requerido_legislacao_{v}", "label": "O item é requerido pela legislação, padrões de qualidade e segurança adotados pela instituição?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": f"residuo_perigoso_{v}", "label": "O item solicitado gera resíduo perigoso?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
                
            # SEÇÃO 4: Estudos e viabilidade
            {"id": f"estudos_cientificos_{v}", "label": "O produto apresenta estudos científicos e de custo-efetividade comparado com o utilizado atualmente no HMV? Caso sim, anexe o arquivo abaixo.", "tipo": "radio_horizontal", "secao": "Studies e Viabilidade", "obrigatorio": True},
        ]
    
        respostas_formulario = {}
        
        fuso_br = datetime.timezone(datetime.timedelta(hours=-3))
        timestamp_criacao = datetime.datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
        
        respostas_formulario["Carimbo de data/hora"] = timestamp_criacao
        respostas_formulario["Endereço de e-mail"] = user_email

        # 9.1. Formulário Base Obrigatório - clear_on_submit=True garante limpeza visual nativa
        with st.form(key=f"form_requisicao_fixo_{v}", clear_on_submit=True):
            
            st.markdown("""
            <div class="caproq-form-section">
                <div class="caproq-form-section-title">🧭 Classificação inicial</div>
                <div class="caproq-form-section-help">Informe se o item seguirá o fluxo padrão ou se será avaliado como produto de teste ou piloto.</div>
            </div>
            """, unsafe_allow_html=True)
            valor_produto_teste = st.radio(
                "Este produto é um Produto de Teste / Piloto? *",
                options=["SIM", "NÃO"],
                index=1,  # Padrão NÃO
                horizontal=True,
                key=f"produto_teste_reativo_{v}",
                help="Selecione SIM se este produto passará por um período de testes práticos antes da compra final."
            )
            respostas_formulario["Este produto é um Produto de Teste / Piloto?"] = valor_produto_teste

            # Restante dos campos estruturados do formulário base
            secao_atual = ""
            for campo in CONFIG_CAMPOS:
                if campo["secao"] != secao_atual:
                    secao_atual = campo["secao"]
                    secoes_visuais = {
                        "Dados do Produto": ("📦", "Dados do produto", "Descreva o item, a apresentação, o fabricante e a finalidade de uso."),
                        "Processos e Dependências": ("⚙️", "Processos e dependências", "Explique o processo atual e eventuais equipamentos ou insumos relacionados."),
                        "Avaliação de Impacto e Segurança": ("🛡️", "Impacto e segurança", "Avalie os ganhos esperados e os possíveis impactos assistenciais, ocupacionais e ambientais."),
                        "Studies e Viabilidade": ("📊", "Estudos e viabilidade", "Informe a existência de evidências científicas e análises de custo-efetividade."),
                    }
                    icone_secao, titulo_secao, ajuda_secao = secoes_visuais.get(
                        secao_atual,
                        ("📌", secao_atual, "Preencha as informações desta etapa."),
                    )
                    st.markdown(
                        f"""
                        <div class="caproq-form-section">
                            <div class="caproq-form-section-title">{icone_secao} {titulo_secao}</div>
                            <div class="caproq-form-section-help">{ajuda_secao}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                
                label_final = f"{campo['label']} *" if campo["obrigatorio"] else campo["label"]
                
                if campo["tipo"] == "texto":
                    respostas_formulario[campo["label"]] = st.text_input(label_final, key=campo["id"])
                elif campo["tipo"] == "area_texto":
                    respostas_formulario[campo["label"]] = st.text_area(label_final, key=campo["id"])
                elif campo["tipo"] == "selecao_tripla":
                    respostas_formulario[campo["label"]] = st.selectbox(label_final, options=["", "Sim", "Não", "Não se aplica"], key=campo["id"])
                elif campo["tipo"] == "selecao_binaria":
                    respostas_formulario[campo["label"]] = st.selectbox(label_final, options=["", "Sim", "Não"], key=campo["id"])
                elif campo["tipo"] == "radio_horizontal":
                    opcoes_radio = ["Sim", "Não"] if "estudos_cientificos" in campo["id"] else ["Sim", "Não", "Não se aplica"]
                    
                    respostas_formulario[campo["label"]] = st.radio(
                        label_final, 
                        options=opcoes_radio, 
                        index=None,  
                        horizontal=True, 
                        key=campo["id"]
                    )
            
            # 9.2. Seção anexos
            st.markdown("""
            <div class="caproq-form-section">
                <div class="caproq-form-section-title">📎 Documentos técnicos</div>
                <div class="caproq-form-section-help">Anexe a FDS obrigatória e, quando disponíveis, registro ANVISA, laudos, ficha técnica, catálogo e estudos.</div>
            </div>
            """, unsafe_allow_html=True)
            
            arquivos_gerais = st.file_uploader("Arquivos anexados (Registro ANVISA, Laudo Técnico, Ficha Técnico, Fabricante):", accept_multiple_files=True, key=f"up_arquivos_gerais_{v}")
            fds_obrigatorio = st.file_uploader("Anexar FDS (Obrigatório) *", key=f"up_fds_obrigatorio_{v}")
            arquivo_estudos = st.file_uploader("Anexo arquivo de estudos científicos e de custo-efetividade:", key=f"up_arquivo_estudos_{v}")
    
            st.markdown("""
            <div class="caproq-form-section">
                <div class="caproq-form-section-title">✅ Revisão e envio</div>
                <div class="caproq-form-section-help">Revise as respostas e os anexos. Após o envio, o chamado será encaminhado automaticamente às alçadas técnicas.</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botão de envio padrão - Aciona a validação em 1 clique
            enviar_formulario = st.form_submit_button("Enviar solicitação para avaliação", use_container_width=True, type="primary")
            
        # Controle interno de salvamento final
        executar_envio_final = False

        # Dispara imediatamente após o primeiro clique
        if enviar_formulario:
            # Validação dos campos padrões obrigatórios
            campos_vazios = [campo["label"] for campo in CONFIG_CAMPOS if campo["obrigatorio"] and not respostas_formulario.get(campo["label"])]
            
            if not fds_obrigatorio:
                campos_vazios.append("Anexar FDS")
            
            pergunta_estudos_label = "O produto apresenta estudos científicos e de custo-efetividade comparado com o utilizado atualmente no HMV? Caso sim, anexe o arquivo abaixo."
            resposta_estudos = respostas_formulario.get(pergunta_estudos_label, "")
            
            if resposta_estudos == "Sim" and not arquivo_estudos:
                campos_vazios.append("Anexo arquivo de estudos científicos e de custo-efetividade (Obrigatório quando a resposta for SIM)")
            
            if campos_vazios:
                ui.render_feedback("Campos pendentes: " + "; ".join(campos_vazios), kind="error", title="Revise os campos obrigatórios", icon="📋")
            else:
                # Salva os dados no Session State de forma direta
                st.session_state["dados_base_coletados"] = {
                    "respostas": respostas_formulario,
                    "arquivos_gerais": arquivos_gerais,
                    "fds_obrigatorio": fds_obrigatorio,
                    "arquivo_estudos": arquivo_estudos,
                    "resposta_estudos": resposta_estudos,
                    "valor_produto_teste": valor_produto_teste
                }
                
                # Se for um produto convencional (NÃO teste), encaminha para gravação direto
                if valor_produto_teste == "NÃO":
                    executar_envio_final = True

        # SEGUNDA ETAPA DINÂMICA: Aparece instantaneamente se for Produto de Teste
        if "dados_base_coletados" in st.session_state and st.session_state["dados_base_coletados"]["valor_produto_teste"] == "SIM":
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("""
                <div class="caproq-test-banner">
                    <div class="caproq-test-title">🧪 Informações complementares do produto de teste</div>
                    <div class="caproq-test-copy">O formulário principal foi validado. Complete os dados operacionais e de contato abaixo para concluir o envio.</div>
                </div>
                """, unsafe_allow_html=True)
                
                motivo_teste = st.selectbox(
                    "Classificação do item no HMV: *",
                    options=["", "Produto novo/lançamento", "Melhoramento do produto", "Produto existente não usado no HMV", "Produto similar ao usado no HMV", "Suprir a falta de um produto"],
                    key=f"final_motivo_teste_{v}"
                )
                
                c1, c2, c3 = st.columns(3)
                with c1: consumo_mes = st.text_input("Consumo estimado/mês: *", key=f"final_consumo_mes_{v}")
                with c2: qtd_teste = st.text_input("Quantidade do teste: *", key=f"final_qtd_teste_{v}")
                with c3: setores_teste = st.text_input("Setores do teste: *", key=f"final_setores_teste_{v}")
                
                st.markdown("<hr style='border: 0; border-top: 1px dashed #d3d3d3; margin: 15px 0;'>", unsafe_allow_html=True)
                st.markdown("<p style='color: #2b2b2b; font-weight: bold; margin-top:0;'>👤 Informações de contato do solicitante</p>", unsafe_allow_html=True)
                
                c4, c5, c6 = st.columns(3)
                with c4: setor_solicitante = st.text_input("Setor: *", key=f"final_setor_solicitante_{v}")
                with c5: ramal_solicitante = st.text_input("Fone/ramal do setor: *", key=f"final_ramal_solicitante_{v}")
                with c6: responsavel_area = st.text_input("Gerente ou coordenador da área: *", key=f"final_responsavel_area_{v}")

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Confirmar e concluir envio do produto teste", use_container_width=True, type="primary"):
                    if not all([motivo_teste, consumo_mes, qtd_teste, setores_teste, setor_solicitante, ramal_solicitante, responsavel_area]):
                        ui.render_feedback("Preencha todos os campos adicionais do Produto Teste antes de enviar a solicitação.", kind="error", title="Dados do Produto Teste incompletos", icon="🧪")
                    else:
                        st.session_state["dados_base_coletados"]["respostas"].update({
                            "Motivo_Teste": motivo_teste,
                            "Consumo_Mes": consumo_mes,
                            "Qtd_Teste": qtd_teste,
                            "Setores_Teste": setores_teste,
                            "Setor_Solicitante": setor_solicitante,
                            "Ramal_Solicitante": ramal_solicitante,
                            "Responsavel_Area": responsavel_area
                        })
                        executar_envio_final = True

        if executar_envio_final and "dados_base_coletados" in st.session_state:
            cache = st.session_state["dados_base_coletados"]
            resp_form = cache["respostas"]
            v_prod_teste = cache["valor_produto_teste"]
            resp_estudos = cache["resposta_estudos"]
            
            with st.spinner("Processando anexos e enviando para o Google Drive..."):
                proximo_id = int(df_dados["ID"].max() + 1) if not df_dados.empty and "ID" in df_dados.columns else 1
                
                link_fds = upload_para_google_drive(cache["fds_obrigatorio"], pasta_id=PASTA_DRIVE_ID)
                if not link_fds:
                    link_fds = f"https://drive.google.com/drive/folders/{PASTA_DRIVE_ID}"
                    
                link_estudos = "Não aplicável"
                if resp_estudos == "Sim" and cache["arquivo_estudos"]:
                    link_estudos = upload_para_google_drive(cache["arquivo_estudos"], pasta_id=PASTA_DRIVE_ID)
                    if not link_estudos:
                        link_estudos = f"https://drive.google.com/drive/folders/{PASTA_DRIVE_ID}"
                
                links_gerais = []
                if cache["arquivos_gerais"]:
                    for arq in cache["arquivos_gerais"]:
                        lnk = upload_para_google_drive(arq, pasta_id=PASTA_DRIVE_ID)
                        if lnk:
                            links_gerais.append(lnk)
                link_gerais_str = ", ".join(links_gerais) if links_gerais else "Nenhum arquivo adicional"

                resp_form["Arquivos anexados"] = link_gerais_str
                resp_form["Anexar FDS"] = link_fds
                resp_form["Anexo arquivo de estudos científicos e de custo-efetividade."] = link_estudos

                resp_form.pop("Este produto é um Produto de Teste / Piloto?", None)

                dados_estruturais = {
                    "ID": proximo_id,
                    "Nome solicitante": user_name,
                    "Status_Final": "Em análise",
                    "Produto_Teste": v_prod_teste,
                    "Motivo_Teste": resp_form.get("Motivo_Teste", ""),
                    "Consumo_Mes_Teste": resp_form.get("Consumo_Mes", ""),
                    "Quantidade_Teste": resp_form.get("Qtd_Teste", ""),
                    "Setor_Destino_Teste": resp_form.get("Setores_Teste", ""),
                    "Setor_Solicitante": resp_form.get("Setor_Solicitante", ""),
                    "Ramal_Solicitante": resp_form.get("Ramal_Solicitante", ""),
                    "Responsavel_Area": resp_form.get("Responsavel_Area", "")
                }
                
                for info in ALCADAS_INFO.values():
                    dados_estruturais[info["coluna_sheets"]] = "Pendente"
                
                registro_completo = {**resp_form, **dados_estruturais}
                nova_linha = pd.DataFrame([registro_completo])
                
                df_dados = pd.concat([df_dados, nova_linha], ignore_index=True)
                conn.update(data=df_dados)
                st.session_state["df_dados_cache"] = df_dados.copy()
                st.session_state["df_dados_cache_timestamp"] = time.time()
                st.session_state["df_dados"] = df_dados
                
                txt_descricao = resp_form.get("Descrição completa do produto", "Não informado")
                txt_apresentacao = resp_form.get("Apresentação/volume", "Não informado")
                txt_area_uso = resp_form.get("Área onde será utilizado e indicação detalhada de uso do produto", "Não informado")
                txt_fabricante = resp_form.get("Fabricante/fornecedor", "Não informado")
                txt_sem_produto = resp_form.get("Explique como o procedimento/atividade atual é realizado SEM este produto:", "Não informado")
                link_fds_email = resp_form.get(
                    "Anexar FDS",
                    "",
                )

                link_anexos_email = resp_form.get(
                    "Link_Anexo",
                    resp_form.get(
                        "Arquivos anexados",
                        "",
                    ),
                )

                botoes_documentos_email = bloco_botoes_arquivos(
                    link_fds=link_fds_email,
                    link_anexos=link_anexos_email,
                )
                
                URL_DO_APLICATIVO = "https://formulariocompras.streamlit.app"
                
                detalhes_novo_chamado = f"""
                <div style="margin-top:20px;padding:16px;background:#f8f9fa;
                            border-left:4px solid #005691;border-radius:4px;">
                  <p style="margin:0 0 8px;"><b>Chamado:</b> #{proximo_id}</p>
                  <p style="margin:0 0 8px;"><b>Solicitante:</b> {user_name} ({user_email})</p>
                  <p style="margin:0 0 8px;"><b>Produto de teste:</b> {v_prod_teste}</p>
                  <p style="margin:0 0 8px;"><b>Produto:</b> {txt_descricao}</p>
                  <p style="margin:0 0 8px;"><b>Apresentação/volume:</b> {txt_apresentacao}</p>
                  <p style="margin:0 0 8px;"><b>Área de uso:</b> {txt_area_uso}</p>
                  <p style="margin:0;"><b>Fabricante:</b> {txt_fabricante}</p>
                </div>
                
                {botoes_documentos_email}
                """

                emails_admin = set(
                    emails_unicos(ADMINS)
                )
                
                disparos_abertura = set()
                
                for info_alcada in ALCADAS_INFO.values():
                    emails_da_area = emails_unicos(
                        info_alcada.get("emails", [])
                    )
                
                    for aprovador_email in emails_da_area:
                
                        if aprovador_email in emails_admin:
                            continue
                
                        chave_disparo = (
                            aprovador_email,
                            info_alcada["label"],
                        )
                
                        if chave_disparo in disparos_abertura:
                            continue
                
                        disparos_abertura.add(chave_disparo)
                
                        html_novo_chamado = template_email_caproq(
                            titulo=(
                                f"Nova solicitação para "
                                f"{info_alcada['label']}"
                            ),
                            mensagem=(
                                "Um novo chamado CAPROQ aguarda a avaliação "
                                f"da área <b>{info_alcada['label']}</b>. "
                                "O prazo de referência para esta alçada é de "
                                f"<b>{info_alcada['prazo_util']} dias úteis</b>."
                            ),
                            detalhes=detalhes_novo_chamado,
                            destaque="#005691",
                        )
                
                        enviar_email(
                            destinatario=aprovador_email,
                            assunto=(
                                "CAPROQ: Nova solicitação · "
                                f"{info_alcada['label']} · "
                                f"#{proximo_id}"
                            ),
                            corpo_html=html_novo_chamado,
                        )

                labels_alcadas = ", ".join(
                    info["label"]
                    for info in ALCADAS_INFO.values()
                )
                
                detalhes_admin = detalhes_novo_chamado + f"""
                <div style="
                    margin-top:16px;
                    padding:14px;
                    background:#eef5f9;
                    border-radius:4px;
                    font-size:14px;
                    line-height:1.5;
                ">
                    <b>Áreas participantes:</b>
                    {labels_alcadas}
                </div>
                """
                
                for admin_email in sorted(emails_admin):
                
                    html_admin = template_email_caproq(
                        titulo="Nova solicitação CAPROQ",
                        mensagem=(
                            "Um novo chamado foi aberto e encaminhado "
                            "às áreas técnicas. Acesse o painel para mais informações."
                        ),
                        detalhes=detalhes_admin,
                        destaque="#005691",
                    )
                
                    enviar_email(
                        destinatario=admin_email,
                        assunto=(
                            f"CAPROQ: Novo chamado #{proximo_id}"
                        ),
                        corpo_html=html_admin,
                    )

                st.session_state["form_version"] += 1
                
                if "dados_base_coletados" in st.session_state:
                    del st.session_state["dados_base_coletados"]
                
                ui.render_feedback(f"A solicitação #{proximo_id} foi enviada para avaliação técnica. Você receberá atualizações por e-mail.", kind="success", title="Solicitação enviada com sucesso", icon="🚀")
                time.sleep(2)
                st.rerun()
        
    # 9.3. Aba status
    with tab_status:

        if not df_dados.empty and "Endereço de e-mail" in df_dados.columns:
            meus_pedidos = df_dados[
                df_dados["Endereço de e-mail"].astype(str).str.strip().str.lower()
                == str(user_email).strip().lower()
            ].copy()

            if meus_pedidos.empty:
                st.markdown("""
                <div class="caproq-empty-state">
                    <div class="caproq-empty-icon">📭</div>
                    <div class="caproq-empty-title">Nenhum chamado encontrado</div>
                    <div class="caproq-empty-text">Você ainda não enviou solicitações pelo CAPROQ. Utilize a aba <b>Nova solicitação</b> para iniciar um processo de avaliação.</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Normalização e ordenação das solicitações do usuário
                coluna_data_usuario = None
                for coluna_candidata in ["Carimbo de data/hora", "Timestamp", "Data_Abertura"]:
                    if coluna_candidata in meus_pedidos.columns:
                        coluna_data_usuario = coluna_candidata
                        break

                if coluna_data_usuario:
                    meus_pedidos["_data_ordem_usuario"] = pd.to_datetime(
                        meus_pedidos[coluna_data_usuario], errors="coerce", dayfirst=True
                    )
                    meus_pedidos = meus_pedidos.sort_values(
                        "_data_ordem_usuario", ascending=False, na_position="last"
                    )
                elif "ID" in meus_pedidos.columns:
                    meus_pedidos["_id_ordem_usuario"] = pd.to_numeric(
                        meus_pedidos["ID"], errors="coerce"
                    )
                    meus_pedidos = meus_pedidos.sort_values(
                        "_id_ordem_usuario", ascending=False, na_position="last"
                    )

                status_series = meus_pedidos.get(
                    "Status_Final", pd.Series(index=meus_pedidos.index, dtype="object")
                ).fillna("Em análise").astype(str)

                total_usuario = len(meus_pedidos)
                em_analise_usuario = int((status_series == "Em análise").sum())
                aprovados_usuario = int(status_series.isin(["Aprovado", "Aprovado com ressalva"]).sum())
                reprovados_usuario = int((status_series == "Reprovado").sum())

                m1, m2, m3, m4 = st.columns(4)
                metricas_usuario = [
                    (m1, "Total de chamados", total_usuario, "Solicitações registradas"),
                    (m2, "Em andamento", em_analise_usuario, "Ainda em avaliação"),
                    (m3, "Aprovados", aprovados_usuario, "Com ou sem ressalvas"),
                    (m4, "Reprovados", reprovados_usuario, "Decisão final registrada"),
                ]
                for coluna_metrica, rotulo_metrica, valor_metrica, ajuda_metrica in metricas_usuario:
                    with coluna_metrica:
                        st.markdown(
                            f"""
                            <div class="caproq-my-metric">
                                <div class="caproq-my-metric-label">{escape(str(rotulo_metrica))}</div>
                                <div class="caproq-my-metric-value">{escape(str(valor_metrica))}</div>
                                <div class="caproq-my-metric-help">{escape(str(ajuda_metrica))}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

                filtro_col1, filtro_col2, filtro_col3 = st.columns([1.6, 1, 1])
                with filtro_col1:
                    busca_meus_chamados = st.text_input(
                        "Buscar nos meus chamados",
                        placeholder="Número, produto ou fornecedor",
                        key="busca_meus_chamados",
                    ).strip()
                with filtro_col2:
                    opcoes_status_usuario = ["Todos"] + sorted(
                        [s for s in status_series.unique().tolist() if s and s != "nan"]
                    )
                    filtro_status_usuario = st.selectbox(
                        "Status",
                        opcoes_status_usuario,
                        key="filtro_status_meus_chamados",
                    )
                with filtro_col3:
                    ordem_usuario = st.selectbox(
                        "Ordenação",
                        ["Mais recentes", "Mais antigos", "Maior número", "Menor número"],
                        key="ordem_meus_chamados",
                    )

                meus_pedidos_filtrados = meus_pedidos.copy()

                if filtro_status_usuario != "Todos":
                    meus_pedidos_filtrados = meus_pedidos_filtrados[
                        meus_pedidos_filtrados.get("Status_Final", "Em análise")
                        .fillna("Em análise")
                        .astype(str)
                        == filtro_status_usuario
                    ]

                if busca_meus_chamados:
                    termo_usuario = busca_meus_chamados.lower()
                    mascara_busca_usuario = pd.Series(False, index=meus_pedidos_filtrados.index)
                    for coluna_busca_usuario in [
                        "ID",
                        "Descrição completa do produto",
                        "Fabricante/fornecedor",
                        "Área onde será utilizado e indicação detalhada de uso do produto",
                    ]:
                        if coluna_busca_usuario in meus_pedidos_filtrados.columns:
                            mascara_busca_usuario = mascara_busca_usuario | (
                                meus_pedidos_filtrados[coluna_busca_usuario]
                                .fillna("")
                                .astype(str)
                                .str.lower()
                                .str.contains(termo_usuario, regex=False)
                            )
                    meus_pedidos_filtrados = meus_pedidos_filtrados[mascara_busca_usuario]

                if ordem_usuario in ["Mais recentes", "Mais antigos"] and coluna_data_usuario:
                    meus_pedidos_filtrados = meus_pedidos_filtrados.sort_values(
                        "_data_ordem_usuario",
                        ascending=(ordem_usuario == "Mais antigos"),
                        na_position="last",
                    )
                elif "ID" in meus_pedidos_filtrados.columns:
                    meus_pedidos_filtrados["_id_ordem_exibicao"] = pd.to_numeric(
                        meus_pedidos_filtrados["ID"], errors="coerce"
                    )
                    meus_pedidos_filtrados = meus_pedidos_filtrados.sort_values(
                        "_id_ordem_exibicao",
                        ascending=(ordem_usuario == "Menor número"),
                        na_position="last",
                    )

                st.caption(
                    f"Exibindo {len(meus_pedidos_filtrados)} de {total_usuario} chamado(s)."
                )

                if meus_pedidos_filtrados.empty:
                    st.markdown("""
                    <div class="caproq-empty-state">
                        <div class="caproq-empty-icon">🔎</div>
                        <div class="caproq-empty-title">Nenhum resultado para os filtros selecionados</div>
                        <div class="caproq-empty-text">Revise o termo de busca ou altere o filtro de status.</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    lista_alcadas = list(ALCADAS_INFO.values())

                    for _, row in meus_pedidos_filtrados.iterrows():
                        status_atual = str(row.get("Status_Final", "Em análise") or "Em análise")
                        try:
                            id_c = int(float(row.get("ID", 0)))
                        except (TypeError, ValueError):
                            id_c = row.get("ID", "—")

                        desc_produto = str(
                            row.get("Descrição completa do produto", "Sem descrição")
                            or "Sem descrição"
                        )
                        titulo_resumido = (
                            desc_produto[:70] + "..."
                            if len(desc_produto) > 70
                            else desc_produto
                        )
                        produto_teste = str(row.get("Produto_Teste", "")).strip().upper() == "SIM"

                        data_abertura_texto = "Não informada"
                        if coluna_data_usuario:
                            data_bruta_usuario = row.get(coluna_data_usuario, "")
                            data_convertida_usuario = pd.to_datetime(
                                data_bruta_usuario, errors="coerce", dayfirst=True
                            )
                            if pd.notna(data_convertida_usuario):
                                data_abertura_texto = data_convertida_usuario.strftime("%d/%m/%Y às %H:%M")
                            elif str(data_bruta_usuario).strip():
                                data_abertura_texto = str(data_bruta_usuario)

                        votos_usuario = []
                        for info_alcada in lista_alcadas:
                            coluna_voto_usuario = info_alcada["coluna_sheets"]
                            voto_usuario = str(row.get(coluna_voto_usuario, "Pendente") or "Pendente")
                            votos_usuario.append((info_alcada, voto_usuario))

                        qtd_concluidas_usuario = sum(
                            1 for _, voto_usuario in votos_usuario
                            if voto_usuario.strip().lower() != "pendente"
                        )
                        qtd_total_alcadas_usuario = len(votos_usuario)
                        percentual_usuario = (
                            round((qtd_concluidas_usuario / qtd_total_alcadas_usuario) * 100)
                            if qtd_total_alcadas_usuario
                            else 0
                        )

                        pendentes_labels_usuario = [
                            info_alcada["label"]
                            for info_alcada, voto_usuario in votos_usuario
                            if voto_usuario.strip().lower() == "pendente"
                        ]

                        if status_atual == "Aprovado":
                            badge_classe = "caproq-my-badge-green"
                            badge_icone = "✓"
                        elif status_atual == "Aprovado com ressalva":
                            badge_classe = "caproq-my-badge-yellow"
                            badge_icone = "!"
                        elif status_atual == "Reprovado":
                            badge_classe = "caproq-my-badge-red"
                            badge_icone = "×"
                        elif status_atual == "Em análise":
                            badge_classe = "caproq-my-badge-blue"
                            badge_icone = "↻"
                        else:
                            badge_classe = "caproq-my-badge-gray"
                            badge_icone = "•"

                        titulo_expander_usuario = (
                            f"Chamado #{id_c} · {titulo_resumido} · {status_atual}"
                        )

                        with st.expander(titulo_expander_usuario, expanded=False):
                            status_badge_html = (
                                f'<span class="caproq-my-badge {badge_classe}">'
                                f'{badge_icone} {escape(status_atual)}</span>'
                            )
                            teste_badge_html = (
                                '<span class="caproq-my-badge caproq-my-badge-blue">🧪 Produto de teste</span>'
                                if produto_teste else
                                '<span class="caproq-my-badge caproq-my-badge-gray">📦 Produto padrão</span>'
                            )
                            st.markdown(
                                f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px'>{status_badge_html}{teste_badge_html}</div>",
                                unsafe_allow_html=True,
                            )

                            fabricante_usuario = str(row.get("Fabricante/fornecedor", "Não informado") or "Não informado")
                            area_uso_usuario = str(
                                row.get(
                                    "Área onde será utilizado e indicação detalhada de uso do produto",
                                    "Não informado",
                                ) or "Não informado"
                            )
                            setor_usuario = str(row.get("Setor", row.get("Setor solicitante", "Não informado")) or "Não informado")

                            st.markdown(
                                f"""
                                <div class="caproq-my-summary">
                                    <div class="caproq-my-summary-item">
                                        <div class="caproq-my-summary-label">Chamado</div>
                                        <div class="caproq-my-summary-value">#{escape(str(id_c))}</div>
                                    </div>
                                    <div class="caproq-my-summary-item">
                                        <div class="caproq-my-summary-label">Abertura</div>
                                        <div class="caproq-my-summary-value">{escape(data_abertura_texto)}</div>
                                    </div>
                                    <div class="caproq-my-summary-item">
                                        <div class="caproq-my-summary-label">Fornecedor</div>
                                        <div class="caproq-my-summary-value">{escape(fabricante_usuario)}</div>
                                    </div>
                                    <div class="caproq-my-summary-item">
                                        <div class="caproq-my-summary-label">Setor</div>
                                        <div class="caproq-my-summary-value">{escape(setor_usuario)}</div>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            if status_atual == "Em análise":
                                if pendentes_labels_usuario:
                                    etapa_atual_usuario = "Aguardando parecer de: " + ", ".join(pendentes_labels_usuario)
                                else:
                                    etapa_atual_usuario = "Avaliações concluídas; aguardando homologação final"
                            else:
                                etapa_atual_usuario = "Processo finalizado"

                            st.markdown(
                                f"""
                                <div class="caproq-my-stage">
                                    <div class="caproq-my-stage-title">Etapa atual</div>
                                    <div class="caproq-my-stage-value">{escape(etapa_atual_usuario)}</div>
                                    <div style="opacity:.65;font-size:.80rem;margin-top:5px">{qtd_concluidas_usuario} de {qtd_total_alcadas_usuario} alçada(s) concluída(s) · {percentual_usuario}% do fluxo técnico</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            st.progress(percentual_usuario / 100 if percentual_usuario else 0)

                            st.markdown("#### 📦 Informações da solicitação")
                            info_col1, info_col2 = st.columns(2)
                            with info_col1:
                                st.markdown("**Descrição completa do produto**")
                                st.write(desc_produto)
                            with info_col2:
                                st.markdown("**Área e indicação de uso**")
                                st.write(area_uso_usuario)

                            st.markdown("#### 🧭 Progresso das alçadas técnicas")
                            placar_html_usuario = '<div class="caproq-my-scoreboard">'
                            for info_alcada, voto_usuario in votos_usuario:
                                voto_lower_usuario = voto_usuario.lower()
                                if voto_usuario == "Pendente":
                                    classe_score_usuario = "caproq-score-pending"
                                    status_score_usuario = "⏳ Pendente"
                                elif voto_lower_usuario.startswith("reprovar") or "reprov" in voto_lower_usuario:
                                    classe_score_usuario = "caproq-score-rejected"
                                    status_score_usuario = "❌ Reprovado"
                                elif "ressalva" in voto_lower_usuario:
                                    classe_score_usuario = "caproq-score-warning"
                                    status_score_usuario = "⚠️ Com ressalva"
                                elif voto_lower_usuario.startswith("aprovar") or "aprovado" in voto_lower_usuario:
                                    classe_score_usuario = "caproq-score-approved"
                                    status_score_usuario = "✅ Aprovado"
                                else:
                                    classe_score_usuario = "caproq-score-pending"
                                    status_score_usuario = voto_usuario

                                label_score_usuario = info_alcada["label"]
                                placar_html_usuario += f"""
                                <div class="caproq-my-score {classe_score_usuario}">
                                    <div class="caproq-my-score-label">{escape(label_score_usuario)}</div>
                                    <div class="caproq-my-score-status">{escape(status_score_usuario)}</div>
                                </div>
                                """
                            placar_html_usuario += "</div>"
                            st.markdown(placar_html_usuario, unsafe_allow_html=True)

                            logs_solicitante = []
                            for info_alcada, voto_conteudo in votos_usuario:
                                if voto_conteudo.strip().lower() != "pendente":
                                    logs_solicitante.append((info_alcada["label"], voto_conteudo))

                            if logs_solicitante:
                                st.markdown("#### 💬 Pareceres já registrados")
                                for label_area, parecer_completo in logs_solicitante:
                                    parecer_lower = parecer_completo.lower()
                                    if "reprovar" in parecer_lower or "reprov" in parecer_lower:
                                        classe_parecer = "caproq-my-opinion-red"
                                    elif "ressalva" in parecer_lower:
                                        classe_parecer = "caproq-my-opinion-yellow"
                                    else:
                                        classe_parecer = "caproq-my-opinion-green"

                                    st.markdown(
                                        f"""
                                        <div class="caproq-my-opinion {classe_parecer}">
                                            <div class="caproq-my-opinion-area">{escape(str(label_area))}</div>
                                            <div class="caproq-my-opinion-text">{escape(str(parecer_completo))}</div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )
                            else:
                                ui.render_empty_state("Pareceres ainda não registrados", "As alçadas técnicas ainda não concluíram avaliações para este chamado.", icon="🕘")

                            if status_atual != "Em análise":
                                st.markdown("#### 🏁 Decisão final")
                                obs_admin_usuario = str(row.get("obs_admin", "") or "").strip()
                                if status_atual == "Aprovado":
                                    ui.render_feedback("A solicitação foi aprovada na homologação final.", kind="success", title="Homologação aprovada", icon="✅")
                                elif status_atual == "Aprovado com ressalva":
                                    ui.render_feedback("A solicitação foi aprovada com ressalvas na homologação final.", kind="warning", title="Homologação com ressalvas", icon="⚠️")
                                elif status_atual == "Reprovado":
                                    ui.render_feedback("A solicitação foi reprovada na homologação final.", kind="error", title="Homologação reprovada", icon="⛔")
                                else:
                                    ui.render_feedback(f"Decisão registrada: {status_atual}", kind="info", title="Situação da homologação", icon="ℹ️")

                                if obs_admin_usuario:
                                    st.markdown("**Considerações finais da homologação**")
                                    st.write(obs_admin_usuario)
        else:
            st.markdown("""
            <div class="caproq-empty-state">
                <div class="caproq-empty-icon">⚠️</div>
                <div class="caproq-empty-title">Não foi possível carregar os chamados</div>
                <div class="caproq-empty-text">A base de solicitações está vazia ou não possui a coluna de e-mail necessária para identificar seus registros.</div>
            </div>
            """, unsafe_allow_html=True)
