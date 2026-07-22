import streamlit as st
import requests
import pandas as pd
import smtplib
import os
import extra_streamlit_components as stx
import datetime
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google_auth_oauthlib.flow import Flow
from streamlit_gsheets import GSheetsConnection
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

if "form_count" not in st.session_state:
    st.session_state["form_count"] = 0
    
# ==============================================================================
# 1. Configuração upload de arquivos
# ==============================================================================
def upload_para_google_drive(arquivo_streamlit, pasta_id=None):
    """
    Faz o upload de um arquivo do Streamlit para uma pasta específica do Google Drive.
    Usa os tokens de autenticação salvos na sessão do usuário.
    """
    try:
        if "google_credentials" not in st.session_state:
            st.error("Credenciais do Google não encontradas para o upload.")
            return None
            
        creds = st.session_state["google_credentials"]
        service = build('drive', 'v3', credentials=creds)
        
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

st.markdown("""
<style>
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: none !important;
        background-color: transparent !important;
    }
    
    [data-testid="column"] {
        background-color: transparent !important;
    }

    [data-testid="stImage"], [data-testid="stImage"] img, [data-testid="stImage"] div {
        border-radius: 0px !important;
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
    }
    
    [data-testid="stImage"] button {
        display: none !important;
    }

    .login-box {
        text-align: center !important;
        margin: 0 auto !important;
        width: 100% !important;
        max-width: 450px;
    }

    [data-testid="stMainInterface"] .login-box > div, 
    [data-testid="stMainInterface"] .login-box [data-testid="stMarkdown"] {
        display: flex !important;
        justify-content: center !important;
        text-align: center !important;
    }

    [data-testid="stSidebar"] div, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p {
        text-align: left !important;
        display: block !important;
    }

    .login-box a {
        background: transparent !important;
        color: #005691 !important;
        border: none !important;
        box-shadow: none !important;
        font-weight: bold !important;
        font-size: 1.2em !important;
        text-transform: uppercase !important;
        text-decoration: none !important;
        display: inline-flex !important;
        justify-content: center !important;
        align-items: center !important;
        margin: 20px auto 0 auto !important;
        padding: 10px 0 !important;
    }
    
    .login-box a:hover {
        color: #003D66 !important;
        text-decoration: underline !important;
    }

    /* ==========================================
        2.1 SIDEBAR E COMPONENTES INTERNOS
       ========================================== */
    .sidebar-user-card {
        padding: 12px;
        border-radius: 8px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        background-color: transparent !important;
    }
    
    .foto-perfil {
        border-radius: 50%;
        border: 2px solid #005691;
    }

    h1, h2, h3, h4, h5 { 
        color: #005691 !important; 
        font-weight: 600 !important; 
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. Definição de Alçadas, Conexão e Validação de Usuários (Via Google Sheets)
# ==============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

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
@st.cache_data(ttl=300)
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
            and (agora - horario_cache) < 300
        )

        if cache_valido:
            return st.session_state["df_usuarios_cache"].copy()

        df = conn.read(
            worksheet="Usuarios",
            ttl=300
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
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "painel_principal"

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

    if st.session_state["user_nome"] == "Novo Solicitante":
        email_atual_seguro = ""
        if "email" in st.session_state:
            email_atual_seguro = st.session_state["email"]
        elif 'user_email' in locals():
            email_atual_seguro = user_email

        if email_atual_seguro:
            user_row = df_usuarios[df_usuarios["Email"].str.lower() == email_atual_seguro.lower()]
            
            if not user_row.empty:
                usuario_info = user_row.iloc[0]
                status_ativo = str(usuario_info.get("Ativo", "Não")).strip().lower() == "sim"
                
                if status_ativo:
                    st.session_state["user_nome"] = usuario_info.get("Nome", "Usuário")
                    st.session_state["user_perfil"] = usuario_info.get("Perfil", "Solicitante")
                    st.session_state["is_admin"] = str(usuario_info.get("Admin", "Não")).strip().lower() == "sim"
                    st.session_state["user_ativo"] = True
                    
                    alcada_raw = str(usuario_info.get("Alcada", "Nenhum"))
                    if alcada_raw and alcada_raw.lower() != "nenhum":
                        st.session_state["user_alcadas"] = [a.strip() for a in alcada_raw.split(",")]
                    else:
                        st.session_state["user_alcadas"] = []
                else:
                    st.session_state["user_ativo"] = False

if not st.session_state["user_ativo"]:
    st.error("❌ Seu usuário está inativo no sistema. Procure o administrador.")
    st.stop()

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
cookie_manager = stx.CookieManager()

if "connected" not in st.session_state:
    st.session_state.connected = False
if "cookies_carregados" not in st.session_state:
    st.session_state.cookies_carregados = False

cookie_email = cookie_manager.get(cookie="moinhos_user_email")
cookie_name = cookie_manager.get(cookie="moinhos_user_name")
cookie_picture = cookie_manager.get(cookie="moinhos_user_picture")

if cookie_email and not st.session_state.connected:
    st.session_state.connected = True
    st.session_state.email = cookie_email
    st.session_state.name = cookie_name
    st.session_state.picture = cookie_picture
    st.session_state.cookies_carregados = True
    st.rerun()

if cookie_email is None and not st.session_state.cookies_carregados:
    time.sleep(0.2)
    st.session_state.cookies_carregados = True
    st.rerun()

client_config = {
    "web": {
        "client_id": st.secrets.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": st.secrets.get("GOOGLE_CLIENT_SECRET", ""),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [st.secrets.get("GOOGLE_REDIRECT_URI", "")],
    }
}

query_params = st.query_params
if "code" in query_params and not st.session_state.get('connected'):
    try:
        flow = Flow.from_client_config(
            client_config,
            scopes=[
                'https://www.googleapis.com/auth/userinfo.profile', 
                'https://www.googleapis.com/auth/userinfo.email', 
                'openid', 
                'https://www.googleapis.com/auth/drive.file'
            ],
            redirect_uri=st.secrets["GOOGLE_REDIRECT_URI"]
        )
        flow.fetch_token(code=query_params["code"])
        credentials = flow.credentials
        
        st.session_state["google_credentials"] = credentials
        
        user_info_service = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"}
        ).json()
        
        st.session_state.connected = True
        st.session_state.name = user_info_service.get("name")
        st.session_state.email = user_info_service.get("email")
        st.session_state.picture = user_info_service.get("picture")
        
        fuso_brasilia = datetime.timezone(datetime.timedelta(hours=-3))
        validade = datetime.datetime.now(fuso_brasilia) + datetime.timedelta(hours=5)
        cookie_manager.set(cookie="moinhos_user_email", val=st.session_state.email, expires_at=validade)
        cookie_manager.set(cookie="moinhos_user_name", val=st.session_state.name, expires_at=validade)
        cookie_manager.set(cookie="moinhos_user_picture", val=st.session_state.picture, expires_at=validade)
        
        st.query_params.clear()
        st.rerun()
    except Exception:
        st.query_params.clear()

# ==============================================================================
# 5. Confirgurações tela de Login                     
# ==============================================================================
if not st.session_state.connected:
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    
    with col_l2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        
        if os.path.exists("logomoinhos.png"):
            img_col1, img_col2, img_col3 = st.columns([1, 2, 1])
            with img_col2:
                st.image("logomoinhos.png", use_container_width=True)
        
        st.markdown("<h3 style='text-align: center; margin-top: 20px; font-size: 1.3em; color: #005691; font-weight: 600;'>CAPROQ</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6c757d; font-size: 0.9em; margin-top: -5px;'>Solicitação de Padronização de Produtos Químicos</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        auth_url = (
            f"https://accounts.google.com/o/oauth2/auth?"
            f"response_type=code&client_id={st.secrets.get('GOOGLE_CLIENT_ID','')}&"
            f"redirect_uri={st.secrets.get('GOOGLE_REDIRECT_URI','')}&"
            f"scope=https://www.googleapis.com/auth/userinfo.profile%20https://www.googleapis.com/auth/userinfo.email%20openid%20https://www.googleapis.com/auth/drive.file&prompt=select_account"
        )
        
        b_col1, b_col2, b_col3 = st.columns([0.5, 2, 0.5])
        with b_col2:
            st.link_button("Entrar com o Google", auth_url, use_container_width=True)
            
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==============================================================================
# 6. Configurações da sidebar    
# ==============================================================================
st.sidebar.markdown("<h3 style='font-size: 1.2em; margin-bottom: 5px; color: #005691;'>Hospital Moinhos de Vento</h3>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color: #6c757d; font-size: 0.85em; margin-top:-10px; margin-bottom: 15px;'>Formulário - CAPROQ</p>", unsafe_allow_html=True)

user_name = st.session_state.get('name') or 'Usuário'
user_email = st.session_state.get('email') or ''
user_picture = st.session_state.get('picture') or 'https://cdn-icons-png.flaticon.com/512/149/149071.png'

avatar_html = f"""
<div class="sidebar-user-card" style="display: flex; align-items: center; gap: 12px; padding: 12px; border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px;">
    <img src="{user_picture}" 
         onerror="this.onerror=null; this.src='https://cdn-icons-png.flaticon.com/512/149/149071.png';" 
         style="width: 45px; height: 45px; border-radius: 50%; object-fit: cover; border: 2px solid #005691;">
    <div style="display: flex; flex-direction: column; overflow: hidden; text-align: left;">
        <span style="font-weight: bold; color: #31333F; font-size: 0.95em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; text-align: left;">
            {user_name}
        </span>
        <span style="font-size: 0.8em; color: #6c757d; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; text-align: left;">
            {user_email}
        </span>
    </div>
</div>
"""
st.sidebar.markdown(avatar_html, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Menu de Configurações para Administradores <<<
# ------------------------------------------------------------------------------
if st.session_state.get("is_admin", False):
    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    pagina = st.session_state.get("pagina_atual")

    if pagina == "painel_principal":

        if st.sidebar.button("⚙️ Gerenciar Aprovadores", use_container_width=True):
            st.session_state["pagina_atual"] = "gerenciar_aprovadores"
            st.rerun()

        if st.sidebar.button("🛡️ Homologação Final", use_container_width=True):
            st.session_state["pagina_atual"] = "homologacao_final"
            st.rerun()

    elif pagina == "gerenciar_aprovadores":

        if st.sidebar.button("⬅️ Voltar ao Painel", use_container_width=True):
            st.session_state["pagina_atual"] = "painel_principal"
            st.rerun()

    elif pagina == "homologacao_final":

        if st.sidebar.button("⬅️ Voltar ao Painel", use_container_width=True):
            st.session_state["pagina_atual"] = "painel_principal"
            st.rerun()

st.sidebar.markdown("<br>", unsafe_allow_html=True)

if st.sidebar.button(
    "🚪 Sair",
    use_container_width=True,
    key="botao_sair_sidebar"
):
    st.session_state.clear()
    st.rerun()

# ==============================================================================
# 7. Tela principal
# ==============================================================================
df_dados = carregar_dados()

user_email = st.session_state.get('email', '')
user_name = st.session_state.get('name', 'Usuário')
is_aprovador = user_email in APROVADORES

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
if is_aprovador:
    
    if st.session_state.get("is_admin", False) and st.session_state.get("pagina_atual") == "gerenciar_aprovadores":
        st.markdown("---")
        st.title("⚙️ Configurações de usuários, aprovadores e alçadas")
        st.markdown("Gerencie os acessos, perfis e alçadas técnicas diretamente integrados à aba **Usuarios** da sua planilha.")
        st.markdown("---")
        
        df_usuarios = carregar_dados_usuarios()

        if not df_usuarios.empty:
            df_usuarios["Email"] = df_usuarios["Email"].astype(str).str.strip().str.lower()
            df_usuarios["Ativo"] = df_usuarios["Ativo"].astype(str).str.strip().str.upper()
            df_usuarios["Admin"] = df_usuarios["Admin"].astype(str).str.strip().str.upper()
        
        st.subheader("👥 Usuários cadastrados na planilha")
        if not df_usuarios.empty:
            st.dataframe(
                df_usuarios, 
                column_config={
                    "Email": st.column_config.TextColumn("E-mail"),
                    "Nome": st.column_config.TextColumn("Nome Completo"),
                    "Perfil": st.column_config.TextColumn("Perfil"),
                    "Alcada": st.column_config.TextColumn("Alçadas Associadas"),
                    "Admin": st.column_config.TextColumn("Administrador (SIM/NÃO)"),
                    "Ativo": st.column_config.TextColumn("Status Ativo (SIM/NÃO)"),
                    "Data_Cadastro": st.column_config.TextColumn("Data de Cadastro")
                },
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.warning("⚠️ Nenhum usuário encontrado na aba 'Usuarios' do Google Sheets.")
        
        st.markdown("---")
        
        tab_salvar_usuario, tab_excluir_usuario = st.tabs([
            "💾 Cadastrar / Alterar Usuário", 
            "❌ Remover Usuário"
        ])
        
        lista_alcadas_disponiveis = [ALCADAS_INFO[chave].get("label", chave) for chave in ALCADAS_INFO.keys()]
        
        with tab_salvar_usuario:
            st.markdown("### Salvar ou Atualizar informações de usuário")
            st.caption("Caso o e-mail digitado já exista, o cadastro correspondente será updated.")
            
            with st.form("form_usuario_sheets"):
                email_input = st.text_input("E-mail do usuário (Chave única):").strip().lower()
                nome_input = st.text_input("Nome completo:")
                perfil_input = st.selectbox("Perfil de acesso:", ["Aprovador", "Solicitante", "Visualizador"])
                
                st.markdown("**Selecione as alçadas técnicas deste usuário:**")
                alcadas_selecionadas = []
                
                col_checkboxes = st.columns(2)
                for idx, nome_alcada in enumerate(lista_alcadas_disponiveis):
                    col_index = idx % 2
                    with col_checkboxes[col_index]:
                        if st.checkbox(nome_alcada, key=f"check_alcada_{nome_alcada}"):
                            alcadas_selecionadas.append(nome_alcada)
                
                col_status1, col_status2 = st.columns(2)
                with col_status1:
                    is_admin_input = st.selectbox("É Administrador?", ["NÃO", "SIM"])
                with col_status2:
                    is_ativo_input = st.selectbox("Usuário Ativo?", ["SIM", "NÃO"])
                
                botao_salvar_usr = st.form_submit_button("Salvar Usuário na Planilha", use_container_width=True)
                
                if botao_salvar_usr:
                    if not email_input or "@" not in email_input:
                        st.error("❌ Forneça um e-mail válido para identificação.")
                    elif not nome_input.strip():
                        st.error("❌ O nome do usuário não pode ficar em branco.")
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
                            "Data_Cadastro": data_atual_str
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
                            st.success(msg_sucesso)
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar dados na aba 'Usuarios': {e}")

        # 2. EXCLUIR USUÁRIO
        with tab_excluir_usuario:
            st.markdown("### Remover usuário do sistema")
            st.warning("⚠️ Esta ação removerá o usuário da base de dados do sistema.")
            
            if not df_usuarios.empty:
                emails_exclusao = df_usuarios["Email"].tolist()
                with st.form("form_excluir_usuario"):
                    email_excluir = st.selectbox("Selecione o e-mail para remover:", options=emails_exclusao)
                    confirmar_exclusao = st.checkbox("Confirmo que desejo apagar o registro deste usuário.")
                    botao_excluir_usr = st.form_submit_button("Excluir", use_container_width=True)
                    
                    if botao_excluir_usr:
                        if not confirmar_exclusao:
                            st.error("❌ Marque a caixa de confirmação para poder prosseguir.")
                        else:
                            df_usuarios = df_usuarios[df_usuarios["Email"] != email_excluir]
                            try:
                                conn.update(worksheet="Usuarios", data=df_usuarios)
                                st.session_state["df_usuarios_cache"] = df_usuarios.copy()
                                st.session_state["df_usuarios_cache_timestamp"] = time.time()
                                st.success(f"🗑️ Usuário `{email_excluir}` removido com sucesso!")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao salvar as alterações de exclusão no Sheets: {e}")
            else:
                st.info("Nenhum usuário cadastrado para remoção.")
                        
    # --------------------------------------------------------------------------
    # PAINEL DE CONTROLE PRINCIPAL
    # --------------------------------------------------------------------------
    elif st.session_state.get("pagina_atual") == "painel_principal":
        st.markdown("---")
        
        colunas_permitidas_usuario = []
        is_user_admin = user_email in ADMINS
        
        for letra_col, info_alcada in ALCADAS_INFO.items():
            nome_coluna_sheets = info_alcada["coluna_sheets"]
            emails_alcada = info_alcada.get("emails", [])
            if not isinstance(emails_alcada, list):
                emails_alcada = [emails_alcada]
            if "email" in info_alcada and info_alcada["email"] not in emails_alcada:
                emails_alcada.append(info_alcada["email"])
                
            if is_user_admin or user_email in emails_alcada:
                colunas_permitidas_usuario.append(nome_coluna_sheets)

        if not df_dados.empty:
            colunas_validas = [c for c in colunas_permitidas_usuario if c in df_dados.columns]
            
            if colunas_validas:
                condicao_pendente = (df_dados["Status_Final"] == "Em análise") & (
                    df_dados[colunas_validas].eq("Pendente").any(axis=1)
                )
                pendentes = df_dados[df_dados["Status_Final"].astype(str).str.contains("Em análise", na=False)]
                
                condicao_historico = df_dados[colunas_validas].apply(
                    lambda col: col.astype(str).str.startswith(("Aprovar", "Reprovar"), na=False)
                ).any(axis=1)
                
                historico_aprovador = df_dados[condicao_historico]
            else:
                pendentes = pd.DataFrame()
                historico_aprovador = pd.DataFrame()
            
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("Suas Pendências de Área", len(pendentes))
            with m2: st.metric("Aprovados Gerais no Sheets", len(df_dados[df_dados["Status_Final"] == "Aprovado"]))
            with m3: st.metric("Reprovados Gerais no Sheets", len(df_dados[df_dados["Status_Final"] == "Reprovado"]))
            
            st.markdown("---")
            
            tab_pendentes, tab_hist_aprovador, tab_logs, tab_indicadores = st.tabs([
                "Minhas pendências", 
                "Histórico de decisões",
                "Log de atividades",
                "Indicadores"
            ])
            
            # ----------------------------------------------------------------------
            # 8.1. Aba "Minhas pendências"
            # ----------------------------------------------------------------------
            with tab_pendentes:
                st.markdown("### Solicitações aguardando seu parecer técnico")
                if pendentes.empty:
                    st.success("Nenhuma solicitação pendente para a sua alçada técnica no momento.")
                else:
                    for _, row in pendentes.iterrows():
                        id_chamado = row["ID"]
                        
                        # Definição uniforme da descrição do produto
                        col_prod = "Descrição completa do produto" if "Descrição completa do produto" in row else "Descrição do produto" if "Descrição do produto" in row else "Descricao_Produto"
                        descricao_produto = str(row.get(col_prod, "Sem descrição"))
                        
                        with st.container(border=True):
                            st.markdown(f"#### Chamado #{id_chamado} — {descricao_produto}")
                            st.markdown(f"**Solicitante:** {row.get('Nome solicitante', row.get('Nome', 'Não informado'))} (`{row.get('Endereço de e-mail', '')}`)")
                            
                            with st.expander("🔍 Visualizar detalhes completos da solicitação", expanded=True):
                                st.markdown("---")
                                st.markdown("Dados Preenchidos no Formulário:")
                                
                                col_detalhe1, col_detalhe2 = st.columns(2)
                                with col_detalhe1:
                                    st.markdown(f"**Descrição do Produto:** {descricao_produto}")
                                    st.markdown(f"**Apresentação/Volume:** {row.get('Apresentação/volume', 'N/A')}")
                                    st.markdown(f"**Fabricante/Fornecedor:** {row.get('Fabricante/fornecedor', 'N/A')}")
                                    st.markdown(f"**Área e Indicação de Uso:** {row.get('Área onde será utilizado e indicação detalhada de uso do produto', 'N/A')}")

                                with col_detalhe2:
                                    st.markdown(f"**Contato do Fornecedor:** {row.get('Informações de contato do fornecedor (nome, e-mail e telefone)', 'N/A')}")
                                    st.markdown(f"**Uso atual SEM o produto:** {row.get('Explique como o procedimento/atividade atual é realizado SEM este produto:', 'N/A')}")
                                    st.markdown(f"**Gera resíduo perigoso?:** {row.get('O item solicitado gera resíduo perigoso?', 'N/A')}")
                                    st.markdown(f"**Possui estudos científicos?:** {row.get('O produto apresenta estudos científicos e de custo-efetividade comparado com o utilizado atualmente no HMV? Caso sim, anexe o arquivo abaixo.', 'N/A')}")

                                if "Arquivos anexados" in row and row["Arquivos anexados"] not in ["Nenhum arquivo anexado", "Nenhum arquivo adicional", ""]:
                                    st.markdown("**Documentação Adicional:**")
                                link_anexo = row.get("Link_Anexo", row.get("Arquivos anexados", ""))
                                
                                if isinstance(link_anexo, str) and link_anexo.strip() not in ["", "nan", "None", "Nenhum arquivo anexado", "Nenhum arquivo adicional"]:
                                    st.link_button("Abrir anexos no Google Drive", link_anexo, use_container_width=True)
                                else:
                                    st.caption("Nenhum arquivo adicional anexado.")
                                
                                if "Anexar FDS" in row and row["Anexar FDS"] not in ["", "Não aplicável"]:
                                    st.markdown("**Ficha de Dados de Segurança (FDS):**")
                                    st.link_button("Abrir FDS", row["Anexar FDS"], use_container_width=True)
                                st.markdown("---")
                            
                            st.markdown("<br><b>Seu parecer técnico:</b>", unsafe_allow_html=True)
                            
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
                                                    st.error(f"Por favor, preencha o campo Parecer. Ele é obrigatório para decisões de '{voto_opcao}'.")
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

                                                    st.success("Seu parecer técnico foi computado com sucesso!")
                                                    time.sleep(1.2)
                                                    st.rerun()

            # ----------------------------------------------------------------------
            # 8.2. Aba "Histórico de decisões"
            # ----------------------------------------------------------------------
            with tab_hist_aprovador:
                st.markdown("### 📋 Acompanhamento e histórico de deliberações")
                st.caption("Veja abaixo o andamento detalhado e os prazos de resposta de cada alçada técnica.")
                
                if historico_aprovador.empty:
                    st.info("Sua alçada técnica atual ainda não emitiu votos históricos no sistema.")
                else:
                    for _, row in historico_aprovador.iterrows():
                        id_c = int(row['ID'])
                        desc_h = row.get("Descrição completa do produto", "Sem descrição")
                        
                        carimbo_original = row.get('Carimbo de data/hora', row.get('Timestamp', ''))
                        
                        with st.expander(f"📦 Chamado #{id_c} — {desc_h} (Status Geral: {row['Status_Final']})"):
                            dt_abertura = None
                            if carimbo_original and str(carimbo_original).strip() not in ["nan", "None", ""]:
                                try:
                                    data_limpa = str(carimbo_original).split()[0]
                                    dt_abertura = pd.to_datetime(data_limpa, dayfirst=True)
                                except:
                                    dt_abertura = None

                            if dt_abertura:
                                st.markdown(f"⏱️ **Data de Abertura:** {dt_abertura.strftime('%d/%m/%Y')}")
                            else:
                                st.markdown("⚠️ *Data de abertura não identificada para cálculo de prazos.*")
                            
                            st.markdown("---")
                            st.markdown("**Situação por Alçada Técnica:**")
                            
                            for letra_col, info in ALCADAS_INFO.items():
                                c_nome = info["coluna_sheets"]
                                
                                if c_nome in df_dados.columns:
                                    v_status = str(row[c_nome]).strip()
                                    
                                    with st.container(border=True):
                                        col_info_area, col_prazo_status = st.columns([2, 1])
                                        
                                        with col_info_area:
                                            st.markdown(f"📌 **{info['label']}**")
                                            
                                            if v_status == "Pendente":
                                                st.markdown("⏳ **Parecer:** *Aguardando deliberação*")
                                            else:
                                                st.markdown(f"💬 **Parecer registrado:**\n`{v_status}`")
                                                
                                        with col_prazo_status:
                                            if row['Status_Final'] == "Reprovado" and v_status == "Pendente":
                                                st.error("🛑 Fluxo encerrado (Chamado recusado)")
                                            
                                            elif v_status == "Pendente" and dt_abertura:
                                                prazo_definido = info.get("prazo_util", 5)
                                                
                                                hoje = pd.Timestamp.now().normalize()
                                                abertura_norm = dt_abertura.normalize()
                                                
                                                dias_passados_uteis = len(pd.date_range(start=abertura_norm, end=hoje, freq='B')) - 1
                                                dias_restantes_uteis = prazo_definido - dias_passados_uteis
                                                
                                                if dias_restantes_uteis > 1:
                                                    st.warning(f"⏰ Restam **{dias_restantes_uteis} dias úteis**")
                                                elif dias_restantes_uteis == 1:
                                                    st.warning("⚠️ Resta **1 dia útil!**")
                                                elif dias_restantes_uteis == 0:
                                                    st.error("🚨 **Prazo vence HOJE!**")
                                                else:
                                                    st.error(f"❌ **Atrasado há {abs(dias_restantes_uteis)} dias úteis**")
                                                    
                                            elif v_status == "Pendente":
                                                st.caption("Prazo indisponível")
                                            else:
                                                st.success("✅ Concluído")

            # ----------------------------------------------------------------------
            # 8.3. Aba "Log de atividades"
            # ----------------------------------------------------------------------
            with tab_logs:
                st.markdown("### 📜 Linha de Tempo e Auditoria Geral dos Processos")
                st.caption("Abaixo consta o histórico completo desde a abertura do chamado para fins de conformidade e auditoria.")
                
                for _, row in df_dados.iterrows():
                    id_c = int(row['ID'])
                    desc_l = row.get("Descrição completa do produto", "Sem descrição")
                    solicitante_nome = row.get('Nome solicitante', row.get('Nome', 'Não informado'))
                    solicitante_email = row.get('Endereço de e-mail', 'Não informado')
                    carimbo_abertura = row.get('Carimbo de data/hora', row.get('Timestamp', 'Data não registrada'))
                    
                    with st.expander(f"🕒 Chamado #{id_c} — {desc_l} | Status Atual: {row['Status_Final']}"):
                        st.info(f"🔹 **[Abertura do Processo]** — Cadastrado em `{carimbo_abertura}` por **{solicitante_nome}** (`{solicitante_email}`)")
                        
                        logs_encontrados = False
                        st.markdown("**Pareceres e Tramitações Técnicas:**")
                        
                        for info in ALCADAS_INFO.values():
                            c_nome = info["coluna_sheets"]
                            if c_nome in df_dados.columns and row[c_nome] != "Pendente":
                                voto_detalhado = str(row[c_nome])
                                logs_encontrados = True
                                
                                if "Reprovar" in voto_detalhado:
                                    st.error(f"🔴 **{info['label']}:** {voto_detalhado}")
                                elif "ressalva" in voto_detalhado.lower():
                                    st.warning(f"🟡 **{info['label']}:** {voto_detalhado}")
                                else:
                                    st.success(f"🟢 **{info['label']}:** {voto_detalhado}")
                        
                        if not logs_encontrados:
                            st.caption("⏳ Nenhuma alçada técnica emitiu parecer para este chamado até o momento (Aguardando deliberações).")
                            
                        if row['Status_Final'] in ["Aprovado", "Reprovado"]:
                            cor_status = "🟢" if row['Status_Final'] == "Aprovado" else "🔴"
                            st.markdown(f"{cor_status} **[Fim do Fluxo]** Processo finalizado com o status de **{row['Status_Final']}**.")

            # ----------------------------------------------------------------------
            # 8.4. Aba "Indicadores"
            # ----------------------------------------------------------------------
            with tab_indicadores:
                st.markdown("### Painel analítico (CAPROQ)")
                st.markdown("Confira os indicadores de desempenho, volumetria e distribuição de pareceres do comitê.")
                
                col_data = None
                for c in df_dados.columns:
                    if "data" in c.lower() or "timestamp" in c.lower() or "hora" in c.lower():
                        col_data = c
                        break
                
                if col_data:
                    df_dados[col_data] = pd.to_datetime(df_dados[col_data], errors='coerce', dayfirst=True)
                    hoje = pd.Timestamp.now()
                    
                    df_semana = df_dados[df_dados[col_data] >= (hoje - pd.Timedelta(days=7))]
                    df_mes = df_dados[df_dados[col_data] >= (hoje - pd.Timedelta(days=30))]
                    df_ano = df_dados[df_dados[col_data] >= (hoje - pd.Timedelta(days=365))]
                    
                    qtd_semana = len(df_semana)
                    qtd_mes = len(df_mes)
                    qtd_ano = len(df_ano)
                else:
                    qtd_semana = qtd_mes = qtd_ano = len(df_dados)
                
                st.markdown("**Volumetria temporal de requisições**")
                kpi_t1, kpi_t2, kpi_t3, kpi_t4 = st.columns(4)
                with kpi_t1: st.metric("Últimos 7 dias (Semanal)", qtd_semana)
                with kpi_t2: st.metric("Últimos 30 dias (Mensal)", qtd_mes)
                with kpi_t3: st.metric("Último Ano (Anual)", qtd_ano)
                with kpi_t4: st.metric("Total Histórico", len(df_dados))
                
                st.markdown("---")
                
                st.markdown("**Distribuição estatística de deliberações (Mensal)**")
                col_graph1, col_graph2 = st.columns(2)
                
                df_recorte_mensal = df_mes if col_data else df_dados
                
                with col_graph1:
                    st.markdown("Status final dos processos")
                    status_finais = df_recorte_mensal["Status_Final"].value_counts().reset_index()
                    status_finais.columns = ["Status", "Quantidade"]
                    
                    if not status_finais.empty:
                        import plotly.express as px
                        fig_status = px.pie(
                            status_finais, 
                            names="Status", 
                            values="Quantidade", 
                            hole=0.4,
                            color="Status",
                            color_discrete_map={"Aprovado": "#2ecc71", "Em análise": "#f1c40f", "Reprovado": "#e74c3c"}
                        )
                        fig_status.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
                        st.plotly_chart(fig_status, use_container_width=True)
                    else:
                        st.caption("Sem dados para exibir este mês.")
                        
                with col_graph2:
                    st.markdown("Tipos de decisões técnicas")
                    aprovacoes_puras = 0
                    com_ressalva = 0
                    recusas = 0
                    
                    for _, r in df_recorte_mensal.iterrows():
                        status = str(r.get("Status_Final", ""))
                        
                        if status == "Reprovado":
                            recusas += 1
                        elif status == "Aprovado":
                            contem_ressalva = False
                            for info in ALCADAS_INFO.values():
                                c_n = info["coluna_sheets"]
                                if c_n in df_recorte_mensal.columns and "ressalva" in str(r.get(c_n, "")).lower():
                                    contem_ressalva = True
                                    break
                            if contem_ressalva:
                                com_ressalva += 1
                            else:
                                aprovacoes_puras += 1
                    
                    df_decisoes = pd.DataFrame({
                        "Decisão": ["Aprovação", "Aprovação com ressalva", "Recusa"],
                        "Quantidade": [aprovacoes_puras, com_ressalva, recusas]
                    })
                    
                    if df_decisoes["Quantidade"].sum() > 0:
                        import plotly.express as px
                        fig_decisoes = px.pie(
                            df_decisoes, 
                            names="Decisão", 
                            values="Quantidade", 
                            hole=0.4,
                            color="Decisão",
                            color_discrete_map={"Aprovação": "#27ae60", "Aprovação com ressalva": "#3498db", "Recusa": "#c0392b"}
                        )
                        fig_decisoes.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
                        st.plotly_chart(fig_decisoes, use_container_width=True)
                    else:
                        st.caption("Sem deliberações registradas este mês.")

                st.markdown("---")
                
                # 8.5. Separação de dados por área
                st.markdown("**Performance de fluxo por alçada (Histórico)**")
                
                dados_areas = []
                for letra_col, info in ALCADAS_INFO.items():
                    col_voto = info["coluna_sheets"]
                    if col_voto in df_dados.columns:
                        votos_serie = df_dados[col_voto].astype(str)
                        
                        concluidos = sum(votos_serie.str.startswith(("Aprovar", "Reprovar")))
                        pendentes_qtd = sum(votos_serie == "Pendente")
                        
                        dados_areas.append({
                            "Sigla": info["label"].split(" - ")[0],
                            "Área Técnica": info["label"].split(" - " )[-1],
                            "Concluídos": concluidos,
                            "Pendentes": pendentes_qtd
                        })
                
                if dados_areas:
                    df_areas = pd.DataFrame(dados_areas)
                    
                    st.dataframe(
                        df_areas, 
                        column_config={
                            "Sigla": st.column_config.TextColumn("Coluna Sheets"),
                            "Área Técnica": st.column_config.TextColumn("Área Comitê"),
                            "Concluídos": st.column_config.NumberColumn("Pareceres emitidos", format="%d ✅"),
                            "Pendentes": st.column_config.NumberColumn("Demandas em aberto", format="%d ⏳"),
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    import plotly.express as px
                    fig_barras_areas = px.bar(
                        df_areas, 
                        x="Área Técnica", 
                        y=["Concluídos", "Pendentes"],
                        title="Volume de Trabalho por Alçada (Emitidos vs Pendentes)",
                        barmode="group",
                        color_discrete_sequence=["#2ecc71", "#e67e22"]
                    )
                    # ... [Código anterior do Bloco 8.5 (Indicadores / Plotly)] ...

                    fig_barras_areas.update_layout(xaxis_title="Área Técnica", yaxis_title="Quantidade de Chamados", height=300)
                    st.plotly_chart(fig_barras_areas, use_container_width=True)
                else:
                    st.caption("Mapeamento de colunas das alçadas não localizado na planilha atual.")

    # ==============================================================================
    # 9. Segunda Etapa: Homologação e Decisão Final (Exclusivo Administradores)
    # ==============================================================================
    if (
        st.session_state.get("is_admin", False)
        and st.session_state.get("pagina_atual") == "homologacao_final"
    ):
        st.markdown("---")
        st.title("🛡️ Painel de Homologação e Decisão Final (Admin)")
        st.markdown(
            "Analise os pareceres técnicos das alçadas e registre a "
            "deliberação final do comitê."
        )

        if df_dados.empty:
            st.info("💡 Não há dados disponíveis para homologação.")
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

            if chamados_para_decisao.empty:
                st.info(
                    "💡 No momento, não há chamados pendentes de homologação "
                    "final ou com status de reunião definida."
                )
            else:
                st.warning(
                    f"⚠️ Existem {len(chamados_para_decisao)} solicitações "
                    "aguardando sua deliberação final."
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

                    with st.container(border=True):
                        st.markdown(
                            f"### Chamado #{id_chamado} — {descricao_produto}"
                        )
                        st.markdown(
                            f"**Status dos Aprovadores:** `{status_apr}`"
                        )

                        eh_produto_teste = (
                            str(row.get("Produto_Teste", "NÃO"))
                            .strip()
                            .upper()
                            == "SIM"
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

                        st.markdown("---")
                        st.markdown("**📋 Pareceres técnicos registrados:**")

                        cols_votos = st.columns(len(ALCADAS_INFO))

                        for idx, (_, info) in enumerate(ALCADAS_INFO.items()):
                            col_voto = info["coluna_sheets"]
                            voto_atual = row.get(col_voto, "Pendente")

                            with cols_votos[idx]:
                                if (
                                    "Aprovar" in str(voto_atual)
                                    and "ressalva"
                                    not in str(voto_atual).lower()
                                ):
                                    st.success(
                                        f"**{info['label']}:**\n🟢 Aprovado"
                                    )
                                elif "ressalva" in str(voto_atual).lower():
                                    st.warning(
                                        f"**{info['label']}:**\n🟡 Com Ressalva"
                                    )
                                elif "Reprovar" in str(voto_atual):
                                    st.error(
                                        f"**{info['label']}:**\n🔴 Recusado"
                                    )
                                else:
                                    st.caption(
                                        f"**{info['label']}:**\n⚪ {voto_atual}"
                                    )

                        with st.expander(
                            "💬 Ver detalhes dos pareceres escritos pelas alçadas"
                        ):
                            for _, info in ALCADAS_INFO.items():
                                voto_detalhado = row.get(
                                    info["coluna_sheets"], "Pendente"
                                )
                                st.markdown(
                                    f"**{info['label']}:** {voto_detalhado}"
                                )

                        if eh_produto_teste:
                            st.markdown("---")
                            st.markdown(
                                "#### 🧪 Avaliação Técnica do Produto Teste"
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

                        st.markdown("---")
                        st.markdown(
                            "#### ✅ Encerramento e Homologação Final"
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

                        st.markdown("---")
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
    st.markdown("---")
    
    tab_novo, tab_status = st.tabs(["Nova solicitação de compra", "Status e histórico dos meus pedidos"])
    
    with tab_novo:
        st.markdown("Formulário de requisição padrão")
        st.markdown("Preencha as informações abaixo para iniciar o processo.")
        
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
            
            st.markdown("<br><h4 style='color: #005691;'>Processos e Dependências (Fase Inicial)</h4>", unsafe_allow_html=True)
            st.markdown("---")
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
                    st.markdown(f"<br><h4 style='color: #005691;'>{secao_atual}</h4>", unsafe_allow_html=True)
                    st.markdown("---")
                
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
            st.markdown("<br><h4 style='color: #005691;'>Arquivos e Documentações</h4>", unsafe_allow_html=True)
            st.markdown("---")
            
            arquivos_gerais = st.file_uploader("Arquivos anexados (Registro ANVISA, Laudo Técnico, Ficha Técnico, Fabricante):", accept_multiple_files=True, key=f"up_arquivos_gerais_{v}")
            fds_obrigatorio = st.file_uploader("Anexar FDS (Obrigatório) *", key=f"up_fds_obrigatorio_{v}")
            arquivo_estudos = st.file_uploader("Anexo arquivo de estudos científicos e de custo-efetividade:", key=f"up_arquivo_estudos_{v}")
    
            st.markdown("---")
            
            # Botão de envio padrão - Aciona a validação em 1 clique
            enviar_formulario = st.form_submit_button("Enviar solicitação", use_container_width=True)
            
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
                st.error(f"❌ Por favor, preencha ou anexe os seguintes campos obrigatórios do formulário principal:\n" + "\n".join([f"• {c}" for c in campos_vazios]))
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
                st.markdown("<h4 style='color: #005691; margin-top:0;'>📦 Informações Complementares: Produto Teste / Piloto</h4>", unsafe_allow_html=True)
                st.warning("⚠️ **Identificamos que este é um Produto de Teste.** Preencha os detalhes finais abaixo para concluir o chamado:")
                
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
                        st.error("❌ Todos os campos adicionais do Produto Teste precisam ser preenchidos antes de salvar.")
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
                            "às áreas técnicas. Este é o aviso único e "
                            "consolidado destinado aos administradores."
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
                
                st.success(f"🎉 Solicitação #{proximo_id} enviada com sucesso para análise!")
                time.sleep(2)
                st.rerun()
        
    # 9.3. Aba status
    with tab_status:
        st.markdown("Seus pedidos e andamento")
        if not df_dados.empty and "Endereço de e-mail" in df_dados.columns:
            meus_pedidos = df_dados[df_dados["Endereço de e-mail"] == user_email]
            if meus_pedidos.empty:
                st.info("Você ainda não enviou nenhuma solicitação.")
            else:
                for _, row in meus_pedidos.iterrows():
                    status_atual = row['Status_Final']
                    id_c = int(row['ID'])
                    
                    cor_status = "#495057"
                    if status_atual == "Aprovado": cor_status = "#008D4C"
                    elif status_atual == "Aprovado com ressalva": cor_status = "#E6A23C"
                    elif status_atual == "Reprovado": cor_status = "#D93025"
                    elif status_atual == "Em análise": cor_status = "#005691"
                    
                    desc_produto = row.get("Descrição completa do produto", "Sem Descrição")
                    titulo_resumido = desc_produto[:50] + "..." if len(desc_produto) > 50 else desc_produto
                
                    tag_teste = " [PRODUTO DE TESTE]" if str(row.get("Produto_Teste", "")).upper() == "SIM" else ""
                    
                    with st.expander(f"📋 Chamado #{id_c} - {titulo_resumido}{tag_teste} [{status_atual}]"):
                        st.markdown(f"Status Final: <span style='color: {cor_status}; font-weight: bold;'>{status_atual}</span>", unsafe_allow_html=True)
                        
                        if tag_teste:
                            st.warning("📦 **Atenção:** Este item foi cadastrado como Produto de Teste / Piloto.")
                        
                        st.write(f"**Descrição Completa:** {desc_produto}")
                        st.write(f"**Área de Uso:** {row.get('Área onde será utilizado e indicação detalhada de uso do produto', 'Não informado')}")
                        st.write(f"**Fabricante/Fornecedor:** {row.get('Fabricante/fornecedor', 'Não informado')}")
                        
                        st.markdown("---")
                        st.markdown("<b>Acompanhamento técnico por alçada comitê:</b>", unsafe_allow_html=True)
                        
                        lista_alcadas = list(ALCADAS_INFO.values())
                        colunas_visualizacao = st.columns(len(lista_alcadas)) if lista_alcadas else st.columns(1)
                        
                        for idx, alc_col in enumerate(colunas_visualizacao):
                            if idx < len(lista_alcadas):
                                info_alcada = lista_alcadas[idx]
                                nome_col_sheets = info_alcada["coluna_sheets"]
                                label_curto = info_alcada["label"].split(" - ")[0]
                                
                                voto_bruto = str(row.get(nome_col_sheets, "Pendente"))
                                
                                with alc_col:
                                    if voto_bruto == "Pendente":
                                        st.caption(f"⏳ **Pendente**\n`{label_curto}`")
                                    elif voto_bruto.startswith("Reprovar"):
                                        st.caption(f"❌ **Reprovado**\n`{label_curto}`")
                                    elif "ressalva" in voto_bruto.lower():
                                        st.caption(f"⚠️ **Ressalva**\n`{label_curto}`")
                                    elif voto_bruto.startswith("Aprovar"):
                                        st.caption(f"✅ **Aprovado**\n`{label_curto}`")
                                    else:
                                        st.caption(f"ℹ️ **{voto_bruto}**\n`{label_curto}`")
                        
                        logs_solicitante = []
                        for info_alcada in lista_alcadas:
                            nome_col_sheets = info_alcada["coluna_sheets"]
                            voto_conteudo = str(row.get(nome_col_sheets, "Pendente"))
                            if nome_col_sheets in df_dados.columns and voto_conteudo != "Pendente":
                                logs_solicitante.append((info_alcada["label"], voto_conteudo))
                                
                        if logs_solicitante:
                            st.markdown("---")
                            st.markdown("<b>Histórico de pareceres registrados:</b>", unsafe_allow_html=True)
                            for label_area, parecer_completo in logs_solicitante:
                                if "Reprovar" in parecer_completo:
                                    st.error(f"🔴 **{label_area}:** {parecer_completo}")
                                elif "ressalva" in parecer_completo.lower():
                                    st.warning(f"🟡 **{label_area}:** {parecer_completo}")
                                else:
                                    st.info(f"🟢 **{label_area}:** {parecer_completo}")
        else:
            st.info("Nenhuma solicitação encontrada.")
