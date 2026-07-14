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

def carregar_dados():
    try:
        df = conn.read(ttl=0)
        df = df.dropna(how="all")
        if not df.empty:
            if "ID" in df.columns:
                df["ID"] = df["ID"].astype(int)
        return df
    except Exception as e:
        st.error(f"Erro ao conectar com a planilha de dados: {e}")
        return pd.DataFrame()

# --- 3.2. CARREGAMENTO DINÂMICO DE USUÁRIOS E PERMISSÕES (Aba 'Usuarios') ---
try:
    df_usuarios = conn.read(worksheet="Usuarios", ttl=10)
except Exception as e:
    st.error(f"Erro ao conectar com a tabela de usuários: {e}")
    df_usuarios = pd.DataFrame()

st.session_state["user_nome"] = "Novo Solicitante"
st.session_state["user_perfil"] = "Solicitante"
st.session_state["user_alcadas"] = []
st.session_state["is_admin"] = False
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
                st.error("❌ Seu usuário está inativo no sistema. Procure o administrador.")
                st.stop()

# --- 3.3. DICIONÁRIO DE ALÇADAS ATUALIZADO (Integração Dinâmica) ---
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

# --- 3.4. DISPARO DE E-MAIL ---
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
    st.sidebar.markdown("⚙️ **Painel Administrativo**")
    
    if st.session_state.get("pagina_atual") == "painel_principal":
        if st.sidebar.button("⚙️ Gerenciar Aprovadores", use_container_width=True):
            st.session_state["pagina_atual"] = "gerenciar_aprovadores"
            st.rerun()
            
    elif st.session_state.get("pagina_atual") == "gerenciar_aprovadores":
        if st.sidebar.button("⬅️ Voltar ao Painel", use_container_width=True):
            st.session_state["pagina_atual"] = "painel_principal"
            st.rerun()

st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
if st.sidebar.button("Sair do Sistema", use_container_width=True):
    try:
        cookie_manager.set(cookie="moinhos_user_email", val="", key="logout_email")
        cookie_manager.set(cookie="moinhos_user_name", val="", key="logout_name")
        cookie_manager.set(cookie="moinhos_user_picture", val="", key="logout_picture")
    except Exception:
        pass
    
    for key in list(st.session_state.keys()):
        del st.session_state[key]
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

# ==============================================================================
# 8. Tela aprovadores e Gerenciamento de Usuários (Persistido no Sheets)
# ==============================================================================
if is_aprovador:
    
    # --------------------------------------------------------------------------
    # NOVO: Se for Admin e a página selecionada for a de Gerenciamento de Aprovadores
    # --------------------------------------------------------------------------
    if st.session_state.get("is_admin", False) and st.session_state.get("pagina_atual") == "gerenciar_aprovadores":
        st.markdown("---")
        st.title("⚙️ Configurações de Usuários, Aprovadores e Alçadas")
        st.markdown("Gerencie os acessos, perfis e alçadas técnicas diretamente integrados à aba **Usuarios** da sua planilha.")
        st.markdown("---")
        
        # 1. LEITURA DOS DADOS DA NOVA ABA "Usuarios"
        try:
            # Lendo a aba de Usuários via conexão gsheets já existente
            df_usuarios = conn.read(worksheet="Usuarios")
        except Exception as e:
            st.error("❌ Erro ao ler a aba 'Usuarios' no Google Sheets. Verifique se o nome da aba está correto.")
            st.info("As colunas esperadas na aba são: Email, Nome, Perfil, Alcada, Admin, Ativo, Data_Cadastro")
            df_usuarios = pd.DataFrame(columns=["Email", "Nome", "Perfil", "Alcada", "Admin", "Ativo", "Data_Cadastro"])

        # Garante tratamento de strings e preenchimentos vazios
        if not df_usuarios.empty:
            df_usuarios["Email"] = df_usuarios["Email"].astype(str).str.strip().str.lower()
            df_usuarios["Ativo"] = df_usuarios["Ativo"].astype(str).str.strip().str.upper()
            df_usuarios["Admin"] = df_usuarios["Admin"].astype(str).str.strip().str.upper()
        
        # --- VISUALIZAÇÃO ATUAL DOS USUÁRIOS NO SHEETS ---
        st.subheader("👥 Usuários Cadastrados na Planilha")
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
        
        # --- OPERAÇÕES (TABS) ---
        tab_salvar_usuario, tab_excluir_usuario = st.tabs([
            "💾 Cadastrar / Alterar Usuário", 
            "❌ Remover Usuário"
        ])
        
        # Lista de Alçadas disponíveis no sistema para gerar os Checkboxes
        lista_alcadas_disponiveis = [ALCADAS_INFO[chave].get("label", chave) for chave in ALCADAS_INFO.keys()]
        
        # 1. CADASTRAR OU ALTERAR USUÁRIO (Preenchimento amigável com Checkboxes)
        with tab_salvar_usuario:
            st.markdown("### Salvar ou Atualizar Informações de Usuário")
            st.caption("Caso o e-mail digitado já exista, o cadastro correspondente será atualizado.")
            
            with st.form("form_usuario_sheets"):
                email_input = st.text_input("E-mail do Usuário (Chave Única):").strip().lower()
                nome_input = st.text_input("Nome Completo:")
                perfil_input = st.selectbox("Perfil de Acesso:", ["Aprovador", "Solicitante", "Visualizador"])
                
                # Interface de Checkboxes para selecionar alçadas
                st.markdown("**Selecione as Alçadas Técnicas deste usuário:**")
                alcadas_selecionadas = []
                
                # Renderiza em colunas os checkboxes para ficar visualmente limpo
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
                        # Converte a lista de alçadas selecionadas em uma string separada por vírgulas
                        string_alcadas = ", ".join(alcadas_selecionadas) if alcadas_selecionadas else "Nenhuma"
                        
                        fuso_br = datetime.timezone(datetime.timedelta(hours=-3))
                        data_atual_str = datetime.datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                        
                        # Nova linha estruturada exatamente com as colunas da aba
                        nova_linha = {
                            "Email": email_input,
                            "Nome": nome_input,
                            "Perfil": perfil_input,
                            "Alcada": string_alcadas,
                            "Admin": is_admin_input,
                            "Ativo": is_ativo_input,
                            "Data_Cadastro": data_atual_str
                        }
                        
                        # Se já existir o e-mail na base, atualiza. Caso contrário, adiciona.
                        if not df_usuarios.empty and email_input in df_usuarios["Email"].values:
                            # Atualiza a linha correspondente
                            idx_existente = df_usuarios[df_usuarios["Email"] == email_input].index[0]
                            for col, valor in nova_linha.items():
                                df_usuarios.at[idx_existente, col] = valor
                            msg_sucesso = f"🔄 Cadastro do usuário `{email_input}` atualizado com sucesso!"
                        else:
                            # Adiciona nova linha
                            df_nova_linha = pd.DataFrame([nova_linha])
                            df_usuarios = pd.concat([df_usuarios, df_nova_linha], ignore_index=True)
                            msg_sucesso = f"🎉 Usuário `{email_input}` cadastrado com sucesso!"
                        
                        # Grava de volta na aba "Usuarios" do Google Sheets
                        try:
                            conn.update(worksheet="Usuarios", data=df_usuarios)
                            st.success(msg_sucesso)
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar dados na aba 'Usuarios': {e}")

        # 2. EXCLUIR USUÁRIO
        with tab_excluir_usuario:
            st.markdown("### Remover Usuário da Planilha")
            st.warning("⚠️ Esta ação removerá permanentemente o usuário da base de dados no Sheets.")
            
            if not df_usuarios.empty:
                emails_exclusao = df_usuarios["Email"].tolist()
                with st.form("form_excluir_usuario"):
                    email_excluir = st.selectbox("Selecione o E-mail para Remover:", options=emails_exclusao)
                    confirmar_exclusao = st.checkbox("Confirmo que desejo apagar o registro deste usuário.")
                    botao_excluir_usr = st.form_submit_button("Excluir Permanente", use_container_width=True)
                    
                    if botao_excluir_usr:
                        if not confirmar_exclusao:
                            st.error("❌ Marque a caixa de confirmação para poder prosseguir.")
                        else:
                            df_usuarios = df_usuarios[df_usuarios["Email"] != email_excluir]
                            try:
                                conn.update(worksheet="Usuarios", data=df_usuarios)
                                st.success(f"🗑️ Usuário `{email_excluir}` removido com sucesso!")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao salvar as alterações de exclusão no Sheets: {e}")
            else:
                st.info("Nenhum usuário cadastrado para remoção.")
                        
    # --------------------------------------------------------------------------
    # PAINEL DE CONTROLE PRINCIPAL ORIGINAL (Sem alterações no seu fluxo operacional)
    # --------------------------------------------------------------------------
    else:
        st.markdown("---")
        
        colunas_permitidas_usuario = []
        is_user_admin = user_email in ADMINS
        
        for letra_col, info_alcada in ALCADAS_INFO.items():
            nome_coluna_sheets = info_alcada["coluna_sheets"]
            # Suporte para validação se "emails" for uma lista ou se "email" for uma string
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
            
            # Indicadores do Topo
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
                        descricao_produto = str(row.get("Descrição completa do produto", "Sem descrição"))
                        
                        with st.container(border=True):
                            st.markdown(f"#### Chamado #{id_chamado} — {descricao_produto}")
                            st.markdown(f"**Solicitante:** {row.get('Nome solicitante', row.get('Nome', 'Não informado'))} (`{row.get('Endereço de e-mail', '')}`)")
                            
                            with st.expander("🔍 Visualizar detalhes completos da solicitação", expanded=True):
                                st.markdown("---")
                                st.markdown("Dados Preenchidos no Formulário:")
                                
                                col_detalhe1, col_detalhe2 = st.columns(2)
                                with col_detalhe1:
                                    st.markdown(f"**Descrição do Produto:** {row.get('Descrição completa do produto', 'N/A')}")
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
                                                    aprovados_count = sum(1 for v in todos_votos_valores if v.startswith(("Aprovar", "Aprovar com ressalva")))
                                                    
                                                    if reprovados_count > 0:
                                                        df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Reprovado"
                                                        html_fim = f"<h3>CAPROQ: Chamado #{id_chamado} Indeferido</h3><p>O processo foi encerrado pois recebeu parecer desfavorável na alçada técnica: {info['label']}.</p><p><b>Parecer registrado:</b> {parecer_texto}</p>"
                                                        enviar_email(destinatario=row["Endereço de e-mail"], assunto=f"CAPROQ: Processo Encerrado (Reprovado) - #{id_chamado}", corpo_html=html_fim)
                                                    
                                                    elif aprovados_count == len(ALCADAS_INFO):
                                                        df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Aprovado"
                                                        html_fim = f"<h3>CAPROQ: Chamado #{id_chamado} Homologado!</h3><p>A solicitação foi integralmente aprovada (com ou sem ressalvas) por todas as alçadas do comitê técnico.</p>"
                                                        enviar_email(destinatario=row["Endereço de e-mail"], assunto=f"CAPROQ: Homologação Concluída - #{id_chamado}", corpo_html=html_fim)
                                                    
                                                    conn.update(data=df_dados)
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
                    fig_barras_areas.update_layout(xaxis_title="Área Técnica", yaxis_title="Quantidade de Chamados", height=300)
                    st.plotly_chart(fig_barras_areas, use_container_width=True)
                else:
                    st.caption("Mapeamento de colunas das alçadas não localizado na planilha atual.")

else:

# ==============================================================================
# 9. Tela solicitantes
# ==============================================================================
    st.markdown("---")
    
    tab_novo, tab_status = st.tabs(["Nova solicitação de compra", "Status e histórico dos meus pedidos"])
    
    with tab_novo:
        st.markdown("Formulário de requisição padrão")
        st.markdown("Preencha as informações abaixo para iniciar o processo.")
        
        PASTA_DRIVE_ID = "1YM8-vbxx0nMKD_5b0xZ8plr_iw7I9k7R"
    
        CONFIG_CAMPOS = [
            # SEÇÃO 1: Identificação do produto e fornecedor
            {"id": "descricao", "label": "Descrição completa do produto", "tipo": "area_texto", "secao": "Dados do Produto", "obrigatorio": True},
            {"id": "apresentacao", "label": "Apresentação/volume", "tipo": "texto", "secao": "Dados do Produto", "obrigatorio": True},
            {"id": "area_uso", "label": "Área onde será utilizado e indicação detalhada de uso do produto", "tipo": "area_texto", "secao": "Dados do Produto", "obrigatorio": True},
            {"id": "fabricante", "label": "Fabricante/fornecedor", "tipo": "texto", "secao": "Dados do Produto", "obrigatorio": True},
            {"id": "contato_fornecedor", "label": "Informações de contato do fornecedor (nome, e-mail e telefone)", "tipo": "area_texto", "secao": "Dados do Produto", "obrigatorio": True},
            
            # SEÇÃO 2: Dependências e processos
            {"id": "insumos_associados", "label": "Equipamentos e/ou insumos associados ao uso do produto? Se SIM, quais?", "tipo": "area_texto", "secao": "Processos e Dependências", "obrigatorio": False},
            {"id": "sem_produto", "label": "Explique como o procedimento/atividade atual é realizado SEM este produto:", "tipo": "area_texto", "secao": "Processos e Dependências", "obrigatorio": True},
            
            # SEÇÃO 3: Avaliação de impacto e riscos
            {"id": "reducao_tempo", "label": "O produto contribui para a redução de tempo de execução dos procedimentos?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": "reducao_acidentes", "label": "O produto proposto contribui para a redução do risco de acidentes de trabalho?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": "seguranca_paciente", "label": "O produto favorece a segurança do paciente e dos profissionais?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": "reducao_infeccao", "label": "O produto proposto contribui para a redução de risco de infecção hospitalar?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": "requerido_legislacao", "label": "O item é requerido pela legislação, padrões de qualidade e segurança adotados pela instituição?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": "residuo_perigoso", "label": "O item solicitado gera resíduo perigoso?", "tipo": "radio_horizontal", "secao": "Avaliação de Impacto e Segurança", "obrigatorio": True},
                
            # SEÇÃO 4: Estudos e viabilidade
            {"id": "estudos_cientificos", "label": "O produto apresenta estudos científicos e de custo-efetividade comparado com o utilizado atualmente no HMV? Caso sim, anexe o arquivo abaixo.", "tipo": "radio_horizontal", "secao": "Estudos e Viabilidade", "obrigatorio": True},
        ]
    
        respostas_formulario = {}
        
        fuso_br = datetime.timezone(datetime.timedelta(hours=-3))
        timestamp_criacao = datetime.datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
        
        respostas_formulario["Carimbo de data/hora"] = timestamp_criacao
        respostas_formulario["Endereço de e-mail"] = user_email
    
        # 9.1. Formulário
        with st.form(key="form_requisicao_fixo", clear_on_submit=True):
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
                    opcoes_radio = ["Sim", "Não"] if campo["id"] == "estudos_cientificos" else ["Sim", "Não", "Não se aplica"]
                    
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
            
            arquivos_gerais = st.file_uploader("Arquivos anexados (Registro ANVISA, Laudo Técnico, Ficha Técnica, Fabricante):", accept_multiple_files=True)
            fds_obrigatorio = st.file_uploader("Anexar FDS (Obrigatório) *")
            arquivo_estudos = st.file_uploader("Anexo arquivo de estudos científicos e de custo-efetividade:")
    
            st.markdown("---")
            enviar = st.form_submit_button("Enviar solicitação", use_container_width=True)
            
        # <-- O bloco do "if enviar" fica aqui, alinhado com o "with st.form"
        if enviar:
            campos_vazios = [campo["label"] for campo in CONFIG_CAMPOS if campo["obrigatorio"] and not respostas_formulario[campo["label"]]]
            
            if not fds_obrigatorio:
                campos_vazios.append("Anexar FDS")
            
            pergunta_estudos_label = "O produto apresenta estudos científicos and de custo-efetividade comparado com o utilizado atualmente no HMV? Caso sim, anexe o arquivo abaixo."
            resposta_estudos = respostas_formulario.get(pergunta_estudos_label, "")
            
            if resposta_estudos == "Sim" and not arquivo_estudos:
                campos_vazios.append("Anexo arquivo de estudos científicos e de custo-efetividade (Obrigatório quando a resposta for SIM)")
            
            if campos_vazios:
                st.error(f"❌ Por favor, preencha ou anexe os seguintes campos obrigatórios:\n" + "\n".join([f"• {c}" for c in campos_vazios]))
            else:
                with st.spinner("Processando anexos e enviando para o Google Drive..."):
                    proximo_id = int(df_dados["ID"].max() + 1) if not df_dados.empty and "ID" in df_dados.columns else 1
                    
                    link_fds = upload_para_google_drive(fds_obrigatorio, pasta_id=PASTA_DRIVE_ID)
                    if not link_fds:
                        link_fds = f"https://drive.google.com/drive/folders/{PASTA_DRIVE_ID}"
                        
                    link_estudos = "Não aplicável"
                    if resposta_estudos == "Sim" and arquivo_estudos:
                        link_estudos = upload_para_google_drive(arquivo_estudos, pasta_id=PASTA_DRIVE_ID)
                        if not link_estudos:
                            link_estudos = f"https://drive.google.com/drive/folders/{PASTA_DRIVE_ID}"
                    
                    links_gerais = []
                    if arquivos_gerais:
                        for arq in arquivos_gerais:
                            lnk = upload_para_google_drive(arq, pasta_id=PASTA_DRIVE_ID)
                            if lnk:
                                links_gerais.append(lnk)
                    link_gerais_str = ", ".join(links_gerais) if links_gerais else "Nenhum arquivo adicional"
    
                    respostas_formulario["Arquivos anexados"] = link_gerais_str
                    respostas_formulario["Anexar FDS"] = link_fds
                    respostas_formulario["Anexo arquivo de estudos científicos e de custo-efetividade."] = link_estudos
    
                    nome_log = st.session_state.get('user_name', user_name) or "Solicitante desconhecido"
                    email_log = st.session_state.get('user_email', user_email) or "E-mail não identificado"
    
                    if str(nome_log).strip() in ["None", ""]:
                        nome_log = "Solicitante"
                    
                    dados_estruturais = {
                        "ID": proximo_id,
                        "Nome solicitante": user_name,
                        "Status_Final": "Em análise"
                    }
                    
                    for info in ALCADAS_INFO.values():
                        dados_estruturais[info["coluna_sheets"]] = "Pendente"
                    
                    registro_completo = {**respostas_formulario, **dados_estruturais}
                    nova_linha = pd.DataFrame([registro_completo])
                    
                    df_dados = pd.concat([df_dados, nova_linha], ignore_index=True)
                    conn.update(data=df_dados)
                    st.session_state["df_dados"] = df_dados
                    
                    txt_descricao = respostas_formulario.get("Descrição completa do produto", "Não informado")
                    txt_apresentacao = respostas_formulario.get("Apresentação/volume", "Não informado")
                    txt_area_uso = respostas_formulario.get("Área onde será utilizado e indicação detalhada de uso do produto", "Não informado")
                    txt_fabricante = respostas_formulario.get("Fabricante/fornecedor", "Não informado")
                    txt_sem_produto = respostas_formulario.get("Explique como o procedimento/atividade atual é realizado SEM este produto:", "Não informado")
                    
                    URL_DO_APLICATIVO = "https://formulariocompras.streamlit.app"
                    
                    html_novo_chamado = f"""
                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 25px; background-color: #ffffff;'>
                        <h3 style='color: #005691; margin-top: 0;'>HOSPITAL MOINHOS DE VENTO</h3>
                        <p style='color: #2b2b2b; font-size: 1.1em;'>🔔 <b>Nova Solicitação Pendente - CAPROQ</b></p>
                        <p style='color: #2b2b2b;'>Um novo chamado de padronização foi aberto e aguarda a sua avaliação técnica de alçada.</p>
                        <hr style='border: 0; border-top: 1px solid #EAEAEA; margin: 15px 0;'>
                        
                        <p style='margin: 8px 0;'><b>ID do Chamado:</b> #{proximo_id}</p>
                        <p style='margin: 8px 0;'><b>Solicitante:</b> {user_name} ({user_email})</p>
                        <p style='margin: 8px 0;'><b>Apresentação/volume:</b> {txt_apresentacao}</p>
                        <p style='margin: 8px 0;'><b>Área de uso:</b> {txt_area_uso}</p>
                        <p style='margin: 8px 0;'><b>Fabricante:</b> {txt_fabricante}</p>
                        
                        <div style='background-color: #F8F9FA; border-left: 4px solid #005691; padding: 12px; margin: 15px 0; border-radius: 4px;'>
                            <p style='margin: 0 0 5px 0; font-weight: bold; color: #555;'>Descrição completa do produto:</p>
                            <p style='margin: 0; white-space: pre-line; color: #333;'>{txt_descricao}</p>
                        </div>
    
                        <div style='background-color: #F8F9FA; border-left: 4px solid #6c757d; padding: 12px; margin: 15px 0; border-radius: 4px;'>
                            <p style='margin: 0 0 5px 0; font-weight: bold; color: #555;'>Justificativa (Uso sem o produto):</p>
                            <p style='margin: 0; white-space: pre-line; color: #333;'>{txt_sem_produto}</p>
                        </div>
                        
                        <div style='margin-top: 20px;'>
                    """
    
                    if link_gerais_str != "Nenhum arquivo adicional":
                        html_novo_chamado += f"""
                            <a href='{links_gerais[0] if links_gerais else "#"}' target='_blank' style='display: inline-block; padding: 10px 18px; background-color: #007bff; color: #ffffff; text-decoration: none; font-weight: bold; border-radius: 6px; font-size: 14px; margin-right: 10px; margin-bottom: 10px;'>📂 Abrir anexo</a>
                        """
    
                    html_novo_chamado += f"""
                            <a href='{URL_DO_APLICATIVO}' target='_blank' style='display: inline-block; padding: 10px 18px; background-color: #005691; color: #ffffff; text-decoration: none; font-weight: bold; border-radius: 6px; font-size: 14px; margin-bottom: 10px;'>Acessar Painel - CAPROQ</a>
                        </div>
                        
                        <hr style='border: 0; border-top: 1px solid #EAEAEA; margin: 20px 0;'>
                        <p style='color: #6c757d; font-size: 0.85em; text-align: center; margin: 0;'>Este é um disparo automático do Sistema de Gestão de Compras Moinhos.<br>Por favor, não responda a este e-mail.</p>
                    </div>
                    """
                    
                    for aprovador_email in APROVADORES:
                        enviar_email(destinatario=aprovador_email, assunto=f"CAPROQ: Nova Solicitação Pendente - #{proximo_id}", corpo_html=html_novo_chamado)
                    
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
                
                    with st.expander(f"📋 Chamado #{id_c} - {titulo_resumido} [{status_atual}]"):
                        st.markdown(f"Status Final: <span style='color: {cor_status}; font-weight: bold;'>{status_atual}</span>", unsafe_allow_html=True)
                        
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
