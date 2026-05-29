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
        
        # Configuração dos metadados do arquivo
        file_metadata = {'name': arquivo_streamlit.name}
        if pasta_id:
            file_metadata['parents'] = [pasta_id]
            
        # CORRIGIDO: Adicionado o ponto correto em io.BytesIO
        arquivo_bytes = io.BytesIO(arquivo_streamlit.getvalue())
        media = MediaIoBaseUpload(arquivo_bytes, mimetype=arquivo_streamlit.type, resumable=True)
        
        # Executa o upload
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        return file.get('webViewLink') # Retorna o link direto do arquivo no Drive
    except Exception as e:
        st.error(f"Erro ao fazer upload para o Drive: {e}")
        return None

# ==============================================================================
# 1. Configuração Básica da Página e Design Adaptável
# ==============================================================================
st.set_page_config(
    page_title="Workflow de Aprovações - Hospital Moinhos",
    page_icon="logomini.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Inteligente: Limpa caixas voadoras e força comportamento padrão na sidebar
st.markdown("""
<style>
    /* ==========================================
       1. LIMPEZA DE CAIXAS VOADORAS E ELEMENTOS FANTASMAS
       ========================================== */
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

    /* ==========================================
       2. CENTRALIZAÇÃO E ESTILO DO LOGIN
       ========================================== */
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

    /* RESET CRÍTICO DA SIDEBAR: Mata qualquer herança de centralização do loginbox */
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
       3. SIDEBAR E COMPONENTES INTERNOS
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
# 2. Configurações de E-mail e Banco de Dados
# ==============================================================================
APROVADORES = ["jonatan231196@gmail.com", "debora.bairros@hmv.org.br", "sandro.carmo@hmv.org.br"]

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

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        df = conn.read(ttl=0)
        df = df.dropna(how="all")
        if not df.empty:
            if "Motivo_Recusa" in df.columns:
                df["Motivo_Recusa"] = df["Motivo_Recusa"].astype(str).replace("nan", "").replace("None", "")
            if "ID" in df.columns:
                df["ID"] = df["ID"].astype(int)
        return df
    except Exception as e:
        st.error(f"Erro ao conectar com a planilha: {e}")
        return pd.DataFrame()

# --- LOGIN GOOGLE E GERENCIAMENTO DE COOKIES ---
cookie_manager = stx.CookieManager()

if "connected" not in st.session_state:
    st.session_state.connected = False
if "cookies_carregados" not in st.session_state:
    st.session_state.cookies_carregados = False

# Resgata cookies de forma segura
cookie_email = cookie_manager.get(cookie="moinhos_user_email")
cookie_name = cookie_manager.get(cookie="moinhos_user_name")
cookie_picture = cookie_manager.get(cookie="moinhos_user_picture")

# Fluxo de Autenticação via Cookies (Auto-Login)
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
        
        validade = datetime.datetime.now() + datetime.timedelta(days=30)
        cookie_manager.set(cookie="moinhos_user_email", val=st.session_state.email, expires_at=validade)
        cookie_manager.set(cookie="moinhos_user_name", val=st.session_state.name, expires_at=validade)
        cookie_manager.set(cookie="moinhos_user_picture", val=st.session_state.picture, expires_at=validade)
        
        st.query_params.clear()
        st.rerun()
    except Exception:
        st.query_params.clear()

# ==============================================================================
# 3. Tela de Login Corporativa Ajustada e Centralizada
# ==============================================================================
if not st.session_state.connected:
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    
    with col_l2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        
        if os.path.exists("logomoinhos.png"):
            img_col1, img_col2, img_col3 = st.columns([1, 2, 1])
            with img_col2:
                st.image("logomoinhos.png", use_container_width=True)
        
        st.markdown("<h3 style='text-align: center; margin-top: 20px; font-size: 1.3em; color: #005691; font-weight: 600;'>Workflow de Aprovações</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6c757d; font-size: 0.9em; margin-top: -5px;'>Portal de Governança e Alçadas Corporativas</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        auth_url = (
            f"https://accounts.google.com/o/oauth2/auth?"
            f"response_type=code&client_id={st.secrets.get('GOOGLE_CLIENT_ID','')}&"
            f"redirect_uri={st.secrets.get('GOOGLE_REDIRECT_URI','')}&"
            f"scope=https://www.googleapis.com/auth/userinfo.profile%20https://www.googleapis.com/auth/userinfo.email%20openid%20https://www.googleapis.com/auth/drive.file&prompt=select_account"
        )
        
        b_col1, b_col2, b_col3 = st.columns([0.5, 2, 0.5])
        with b_col2:
            st.link_button("🔑 Entrar com o Google", auth_url, use_container_width=True)
            
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==============================================================================
# 4. Sidebar Inteligente e Fluida
# ==============================================================================
st.sidebar.markdown("<h3 style='font-size: 1.2em; margin-bottom: 5px; color: #005691;'>Hospital Moinhos</h3>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color: #6c757d; font-size: 0.85em; margin-top:-10px; margin-bottom: 15px;'>Portal de Suprimentos Corporativos</p>", unsafe_allow_html=True)

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

st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
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
# 5. Interface Principal (Leituras com Fallbacks de Segurança)
# ==============================================================================
df_dados = carregar_dados()

user_email = st.session_state.get('email', '')
user_name = st.session_state.get('name', 'Usuário')
is_aprovador = user_email in APROVADORES

col_header1, col_header2 = st.columns([1, 5])
if os.path.exists("logomoinhos.png"):
    col_header1.image("logomoinhos.png", width=150)

with col_header2:
    st.title("Central de Aprovações de Compras")
    st.markdown("<p style='color: #6c757d; font-size: 1.1em; margin-top: -15px;'>Fluxo de governança e consenso por alçada de aprovação</p>", unsafe_allow_html=True)

# ==============================================================================
# 6. Distribuição de Abas por Perfil (Substituir da Linha 525 até o Final)
# ==============================================================================
if is_aprovador:
    st.markdown("---")
    num_aprovador = APROVADORES.index(user_email) + 1
    coluna_voto = f"Voto_Aprovador{num_aprovador}"
    
    if not df_dados.empty and coluna_voto in df_dados.columns:
        pendentes = df_dados[(df_dados[coluna_voto] == "Pendente") & (df_dados["Status_Final"] == "Em análise")]
        historico_aprovador = df_dados[df_dados[coluna_voto].isin(["Aprovado", "Reprovado", "Aprovado com ressalva"])]
        
        m1, m2, m3 = st.columns(3)
        with m1: st.metric("Suas Pendências", len(pendentes))
        with m2: st.metric("Aprovados pelo Fluxo", len(df_dados[df_dados["Status_Final"] == "Aprovado"]))
        with m3: st.metric("Reprovados pelo Fluxo", len(df_dados[df_dados["Status_Final"] == "Reprovado"]))
        
        st.markdown("---")
        
        # Criação das Abas Oficiais do Aprovador
        tab_pendentes, tab_hist_aprovador, tab_logs, tab_indicadores = st.tabs([
            "📥 Minhas Pendências", 
            "📊 Histórico de Decisões",
            "📜 Log de Atividades",
            "📈 Indicadores de Governança"
        ])
        
        # ----------------------------------------------------------------------
        # ABA 1: MINHAS PENDÊNCIAS
        # ----------------------------------------------------------------------
        with tab_pendentes:
            st.markdown("### Solicitações Pendentes de seu Parecer")
            if pendentes.empty:
                st.success("🎈 Excelente! Nenhuma solicitação corporativa pendente para você no momento.")
            else:
                for _, row in pendentes.iterrows():
                    id_chamado = row["ID"]
                    with st.container(border=True):
                        st.markdown(f"#### Chamado #{id_chamado} - {row['Titulo']}")
                        st.markdown(f"**Solicitante:** {row['Remetente_Nome']} (`{row['Remetente_Email']}`)")
                        
                        with st.expander("🔍 Visualizar Detalhes da Solicitação", expanded=False):
                            st.markdown("---")
                            st.markdown("##### 📝 Descrição do Pedido:")
                            st.write(row['Descricao'])
                            st.markdown("##### 💡 Justificativa Corporativa:")
                            st.write(row['Justificativa'])
                            
                            if "Link_Anexo" in row and row["Link_Anexo"] != "Nenhum arquivo anexado":
                                document_icon = "📂"
                                st.markdown("##### 📎 Documentação Adjunta:")
                                st.link_button(f"{document_icon} Abrir Anexo no Google Drive", row["Link_Anexo"], use_container_width=True)
                            st.markdown("---")
                        
                        if f"recusando_{id_chamado}" not in st.session_state:
                            st.session_state[f"recusando_{id_chamado}"] = False
                        if f"ressalvando_{id_chamado}" not in st.session_state:
                            st.session_state[f"ressalvando_{id_chamado}"] = False
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # --- CONTROLE DOS BOTÕES DE AÇÃO (Aprovar / Ressalva / Reprovar) ---
                        if not st.session_state[f"recusando_{id_chamado}"] and not st.session_state[f"ressalvando_{id_chamado}"]:
                            col_ap, col_res, col_rep = st.columns([2.5, 3.2, 2.3])
                            
                            if col_ap.button("👍 Aprovar", key=f"ap_{id_chamado}", use_container_width=True):
                                df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Aprovado"
                                timestamp_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                nota_atual = str(df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0]).replace("nan", "").replace("None", "")
                                nova_nota = f" | {timestamp_atual} - {user_name} aprovou a solicitação."
                                df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = nota_atual + nova_nota
                                
                                linha_alt = df_dados[df_dados["ID"] == id_chamado].iloc[0]
                                votos = [linha_alt["Voto_Aprovador1"], linha_alt["Voto_Aprovador2"], linha_alt["Voto_Aprovador3"]]
                                
                                if votos.count("Aprovado") == 3:
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Aprovado"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0] + f" | {timestamp_atual} - Sistema: Chamado finalizado com Aprovação Total."
                                    
                                    html_email = f"<div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'><h3 style='color: #008D4C;'>HOSPITAL MOINHOS DE VENTO</h3><p>O chamado <b>#{id_chamado} - {row['Titulo']}</b> foi totalmente APROVADO.</p></div>"
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"HOSPITAL MOINHOS: Solicitação Aprovada! - #{id_chamado}", corpo_html=html_email)
                                else:
                                    html_email = f"<div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'><h3 style='color: #005691;'>HOSPITAL MOINHOS DE VENTO</h3><p>O aprovador <b>{user_name}</b> votou a favor do chamado #{id_chamado}.</p></div>"
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"HOSPITAL MOINHOS: Novo voto registrado no Chamado #{id_chamado}", corpo_html=html_email)
                                
                                conn.update(data=df_dados)
                                st.rerun()
                                
                            if col_res.button("⚠️ Aprovar c/ Ressalva", key=f"res_gatilho_{id_chamado}", use_container_width=True):
                                st.session_state[f"ressalvando_{id_chamado}"] = True
                                st.rerun()
                                
                            if col_rep.button("👎 Reprovar", key=f"rep_gatilho_{id_chamado}", use_container_width=True):
                                st.session_state[f"recusando_{id_chamado}"] = True
                                st.rerun()
                        
                        # --- MODAL DE CONFIRMAÇÃO DE RESSALVA ---
                        elif st.session_state[f"ressalvando_{id_chamado}"]:
                            st.markdown("⚠️ **Descreva a ressalva técnica ou financeira proposta abaixo:**")
                            ressalva_texto = st.text_input("Ressalva (Obrigatório):", key=f"input_res_{id_chamado}")
                            col_conf_res, col_canc_res = st.columns([3, 7])
                            
                            if col_conf_res.button("Confirmar Ressalva", key=f"conf_res_{id_chamado}", use_container_width=True):
                                if ressalva_texto.strip():
                                    df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Aprovado com ressalva"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Aprovado com ressalva"
                                    timestamp_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                    nota_atual = str(df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0]).replace("nan", "").replace("None", "")
                                    nova_nota = f" | {timestamp_atual} - {user_name} inseriu uma Ressalva: {ressalva_texto}"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = nota_atual + nova_nota
                                    
                                    html_ressalva = f"<div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'><h3 style='color: #E6A23C;'>HOSPITAL MOINHOS DE VENTO</h3><p>O chamado #{id_chamado} recebeu ressalvas de {user_name}: <i>{ressalva_texto}</i></p></div>"
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"HOSPITAL MOINHOS: Ressalva aplicada ao Chamado #{id_chamado}", corpo_html=html_ressalva)
                                    
                                    conn.update(data=df_dados)
                                    st.session_state[f"ressalvando_{id_chamado}"] = False
                                    st.rerun()
                                    
                            if col_canc_res.button("Cancelar", key=f"canc_res_{id_chamado}", use_container_width=True):
                                st.session_state[f"ressalvando_{id_chamado}"] = False
                                st.rerun()

                        # --- MODAL DE CONFIRMAÇÃO DE REPROVAÇÃO ---
                        elif st.session_state[f"recusando_{id_chamado}"]:
                            st.markdown("❌ **Explique o motivo da recusa abaixo:**")
                            motivo = st.text_input("Motivo da Reprovação (Obrigatório):", key=f"input_motivo_{id_chamado}")
                            col_conf, col_canc = st.columns([3, 7])
                            
                            if col_conf.button("Confirmar Rejeição", key=f"conf_rep_{id_chamado}", use_container_width=True):
                                if motivo.strip():
                                    df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Reprovado"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Reprovado"
                                    timestamp_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                    nota_atual = str(df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0]).replace("nan", "").replace("None", "")
                                    nova_nota = f" | {timestamp_atual} - {user_name} REPROVOU o chamado. Motivo: {motivo}"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = nota_atual + nova_nota
                                    
                                    html_reprovado = f"<div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'><h3 style='color: #D93025;'>HOSPITAL MOINHOS DE VENTO</h3><p>O chamado #{id_chamado} foi reprovado por {user_name}. Motivo: {motivo}</p></div>"
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"HOSPITAL MOINHOS: Solicitação Recusada - #{id_chamado}", corpo_html=html_reprovado)
                                    
                                    conn.update(data=df_dados)
                                    st.session_state[f"recusando_{id_chamado}"] = False
                                    st.rerun()
                                    
                            if col_canc.button("Cancelar", key=f"canc_rep_{id_chamado}", use_container_width=True):
                                st.session_state[f"recusando_{id_chamado}"] = False
                                st.rerun()

        # ----------------------------------------------------------------------
        # ABA 2: HISTÓRICO DE DECISÕES
        # ----------------------------------------------------------------------
        with tab_hist_aprovador:
            st.markdown("### Histórico Avançado de Decisões")
            if historico_aprovador.empty:
                st.info("Você ainda não registrou votos em chamados anteriores.")
            else:
                for _, row in historico_aprovador.iterrows():
                    id_c = int(row['ID'])
                    voto_proprio = row[coluna_voto]
                    status_final = row['Status_Final']
                    cor_voto = "#008D4C" if voto_proprio == "Aprovado" else "#D93025" if voto_proprio == "Reprovado" else "#E6A23C"
                    
                    with st.expander(f"📋 Chamado #{id_c} - {row['Titulo']} (Seu Voto: {voto_proprio} | Final: {status_final})"):
                        col1, col2 = st.columns([6, 4])
                        with col1:
                            st.markdown(f"**Seu Parecer:** <span style='color:{cor_voto}; font-weight:bold;'>{voto_proprio}</span>", unsafe_allow_html=True)
                            st.write(f"**Solicitante:** {row['Remetente_Nome']} ({row['Remetente_Email']})")
                            st.write(f"**Descrição:** {row['Descricao']}")
                        with col2:
                            st.markdown("**Status das Alçadas:**")
                            for idx in range(3):
                                v_status = row[f"Voto_Aprovador{idx+1}"]
                                icon = "✅" if v_status == "Aprovado" else "❌" if v_status == "Reprovado" else "⚠️" if v_status == "Aprovado com ressalva" else "⏳"
                                st.markdown(f"{icon} Aprovador {idx+1}: `{v_status}`")

        # ----------------------------------------------------------------------
        # ABA 3: LOG DE ATIVIDADES
        # ----------------------------------------------------------------------
        with tab_logs:
            st.markdown("### 📜 Log Geral de Atividades e Auditoria")
            for _, row in df_dados.iterrows():
                id_c = int(row['ID'])
                status_c = row['Status_Final']
                with st.expander(f"📜 Trilha do Chamado #{id_c} - {row['Titulo']} (Status: {status_c})"):
                    st.write(row.get("Motivo_Recusa", "Sem notas de auditoria registradas."))

        # ----------------------------------------------------------------------
        # ABA 4: INDICADORES
        # ----------------------------------------------------------------------
        with tab_indicadores:
            st.markdown("### 📈 Indicadores de Governança")
            st.metric("Total de Chamados na Base", len(df_dados))
            st.success("Métricas e gráficos adicionais de SLAs podem ser injetados aqui.")

# ==============================================================================
# INTERFACE DO SOLICITANTE COMUM (Controle do bloco Condicional principal 'else')
# ==============================================================================
else:
    st.markdown("---")
    st.subheader("📝 Nova Solicitação de Compra")
    st.markdown("Utilize o portal abaixo para abrir uma nova requisição de suprimentos estratégicos.")
    
    with st.form("form_solicitacao", clear_on_submit=True):
        titulo = st.text_input("Título do Chamado (Curto e objetivo):")
        descricao = st.text_area("Descrição do Pedido (Especificações técnicas):")
        justificativa = st.text_area("Justificativa Corporativa (Retorno ou Necessidade):")
        arquivo = st.file_uploader("Anexar Documentação/Cotações (Opcional):", type=["pdf", "docx", "xlsx", "png", "jpg"])
        
        submetido = st.form_submit_button("🚀 Enviar para Conselho de Aprovação")
        if submetido:
            if titulo.strip() and descricao.strip() and justificativa.strip():
                # Aqui entra a sua lógica de upload pro drive e gravação no sheets
                st.success("✨ Solicitação registrada com sucesso no ecossistema de governança!")
            else:
                st.error("❌ Por favor, preencha todos os campos obrigatórios do formulário.")
                        
                        # ==============================================================================
                        # CORRIGIDO: FLUXO PRINCIPAL DE PARECERES E NOTIFICAÇÕES POR E-MAIL
                        # ==============================================================================
                        if not st.session_state[f"recusando_{id_chamado}"] and not st.session_state[f"ressalvando_{id_chamado}"]:
                            col_ap, col_res, col_rep = st.columns([2.5, 3.2, 2.3])
                            
                            # --- BOTÃO APROVAR ---
                            if col_ap.button("👍 Aprovar", key=f"ap_{id_chamado}", use_container_width=True):
                                # 1. Atualiza o voto do usuário atual localmente
                                df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Aprovado"
                                
                                timestamp_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                nota_atual = str(df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0]).replace("nan", "").replace("None", "")
                                nova_nota = f" | {timestamp_atual} - {user_name} aprovou a solicitação."
                                df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = nota_atual + nova_nota
                                
                                # Re-coleta todos os votos da linha atualizada para checar o panorama geral
                                linha_alt = df_dados[df_dados["ID"] == id_chamado].iloc[0]
                                votos = [linha_alt["Voto_Aprovador1"], linha_alt["Voto_Aprovador2"], linha_alt["Voto_Aprovador3"]]
                                
                                # CONDICIONAL INTELIGENTE DE E-MAIL:
                                if votos.count("Aprovado") == 3:
                                    # Cenário A: Todos aprovaram, encerra o chamado
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Aprovado"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0] + f" | {timestamp_atual} - Sistema: Chamado finalizado com Aprovação Total."
                                    
                                    html_email = f"""
                                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                                        <h3 style='color: #008D4C;'>HOSPITAL MOINHOS DE VENTO</h3>
                                        <p style='color: #333333; font-size: 1.1em;'><b>✅ Solicitação Totalmente APROVADA!</b></p>
                                        <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                                        <p>O chamado <b>#{id_chamado} - {row['Titulo']}</b> recebeu o parecer positivo de todas as alçadas de auditoria e foi liberado.</p>
                                    </div>
                                    """
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"HOSPITAL MOINHOS: Solicitação Aprovada! - #{id_chamado}", corpo_html=html_email)
                                else:
                                    # Cenário B: Aprovação intermediária (ainda faltam votos)
                                    html_email = f"""
                                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                                        <h3 style='color: #005691;'>HOSPITAL MOINHOS DE VENTO</h3>
                                        <p style='color: #333333;'><b>⏳ Atualização do Processo - Chamado #{id_chamado}</b></p>
                                        <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                                        <p>O aprovador <b>{user_name}</b> votou a favor da sua solicitação: <i>{row['Titulo']}</i>.</p>
                                        <p>O chamado segue em análise aguardando o parecer dos demais membros do comitê.</p>
                                    </div>
                                    """
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"HOSPITAL MOINHOS: Novo voto registrado no Chamado #{id_chamado}", corpo_html=html_email)
                                
                                conn.update(data=df_dados)
                                st.rerun()
                                
                            if col_res.button("⚠️ Aprovar c/ Ressalva", key=f"res_gatilho_{id_chamado}", use_container_width=True):
                                st.session_state[f"ressalvando_{id_chamado}"] = True
                                st.rerun()
                                
                            if col_rep.button("👎 Reprovar", key=f"rep_gatilho_{id_chamado}", use_container_width=True):
                                st.session_state[f"recusando_{id_chamado}"] = True
                                st.rerun()
                                
                        # --- MODAL DE CONFIRMAÇÃO DE RESSALVA ---
                        elif st.session_state[f"ressalvando_{id_chamado}"]:
                            st.markdown("⚠️ **Descreva a ressalva técnica ou financeira proposta abaixo:**")
                            ressalva_texto = st.text_input("Ressalva (Obrigatório):", key=f"input_res_{id_chamado}")
                            col_conf_res, col_canc_res = st.columns([3, 7])
                            
                            if col_conf_res.button("Confirmar Ressalva", key=f"conf_res_{id_chamado}", use_container_width=True):
                                if ressalva_texto.strip():
                                    df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Aprovado com ressalva"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Aprovado com ressalva"
                                    
                                    timestamp_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                    nota_atual = str(df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0]).replace("nan", "").replace("None", "")
                                    nova_nota = f" | {timestamp_atual} - {user_name} inseriu uma Ressalva: {ressalva_texto}"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = nota_atual + nova_nota
                                    
                                    # ADICIONADO: Disparo de e-mail notificando a ressalva aplicada
                                    html_ressalva = f"""
                                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                                        <h3 style='color: #E6A23C;'>HOSPITAL MOINHOS DE VENTO</h3>
                                        <p style='color: #333333;'><b>⚠️ Solicitação Aprovada com Ressalvas - Chamado #{id_chamado}</b></p>
                                        <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                                        <p>A sua solicitação <b>{row['Titulo']}</b> recebeu um parecer condicional por parte de <b>{user_name}</b>.</p>
                                        <p><b>Ressalva apresentada:</b> <br><i style='color: #555555;'>"{ressalva_texto}"</i></p>
                                    </div>
                                    """
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"HOSPITAL MOINHOS: Ressalva aplicada ao Chamado #{id_chamado}", corpo_html=html_ressalva)
                                    
                                    conn.update(data=df_dados)
                                    st.session_state[f"ressalvando_{id_chamado}"] = False
                                    st.rerun()
                                    
                            if col_canc_res.button("Cancelar", key=f"canc_res_{id_chamado}", use_container_width=True):
                                st.session_state[f"ressalvando_{id_chamado}"] = False
                                st.rerun()

                        # --- MODAL DE CONFIRMAÇÃO DE REPROVAÇÃO ---
                        elif st.session_state[f"recusando_{id_chamado}"]:
                            st.markdown("❌ **Explique o motivo da recusa abaixo:**")
                            motivo = st.text_input("Motivo da Reprovação (Obrigatório):", key=f"input_motivo_{id_chamado}")
                            col_conf, col_canc = st.columns([3, 7])
                            
                            if col_conf.button("Confirmar Rejeição", key=f"conf_rep_{id_chamado}", use_container_width=True):
                                if motivo.strip():
                                    df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Reprovado"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Reprovado"
                                    
                                    timestamp_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                    nota_atual = str(df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0]).replace("nan", "").replace("None", "")
                                    nova_nota = f" | {timestamp_atual} - {user_name} REPROVOU o chamado. Motivo: {motivo}"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = nota_atual + nova_nota
                                    
                                    # ADICIONADO: Disparo de e-mail notificando a reprovação imediata
                                    html_reprovado = f"""
                                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                                        <h3 style='color: #D93025;'>HOSPITAL MOINHOS DE VENTO</h3>
                                        <p style='color: #333333;'><b>❌ Solicitação REPROVADA - Chamado #{id_chamado}</b></p>
                                        <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                                        <p>Lamentamos informar que a sua solicitação de compra <b>{row['Titulo']}</b> foi recusada por <b>{user_name}</b>.</p>
                                        <p><b>Justificativa da Recusa:</b> <br><i style='color: #555555;'>"{motivo}"</i></p>
                                    </div>
                                    """
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"HOSPITAL MOINHOS: Solicitação Recusada - #{id_chamado}", corpo_html=html_reprovado)
                                    
                                    conn.update(data=df_dados)
                                    st.session_state[f"recusando_{id_chamado}"] = False
                                    st.rerun()
                                    
                            if col_canc.button("Cancelar", key=f"canc_rep_{id_chamado}", use_container_width=True):
                                id_chamado = row["ID"]
                                st.session_state[f"recusando_{id_chamado}"] = False
                                st.rerun()

        with tab_hist_aprovador:
            st.markdown("### Histórico Avançado de Decisões")
            st.markdown("Visualize as suas decisões anteriores combinadas com a posição atual do painel de governança.")
            
            if historico_aprovador.empty:
                st.info("Você ainda não registrou votos em chamados anteriores.")
            else:
                for _, row in historico_aprovador.iterrows():
                    id_c = int(row['ID'])
                    voto_proprio = row[coluna_voto]
                    status_final = row['Status_Final']
                    
                    cor_voto = "#008D4C" if voto_proprio == "Aprovado" else "#D93025" if voto_proprio == "Reprovado" else "#E6A23C"
                    
                    with st.expander(f"📋 Chamado #{id_c} - {row['Titulo']} (Seu Voto: {voto_proprio} | Final: {status_final})"):
                        col1, col2 = st.columns([6, 4])
                        
                        with col1:
                            st.markdown(f"**Seu Parecer:** <span style='color:{cor_voto}; font-weight:bold;'>{voto_proprio}</span>", unsafe_allow_html=True)
                            st.write(f"**Solicitante:** {row['Remetente_Nome']} ({row['Remetente_Email']})")
                            st.write(f"**Descrição:** {row['Descricao']}")
                        
                        with col2:
                            st.markdown("**Status das Alçadas:**")
                            for idx in range(3):
                                v_status = row[f"Voto_Aprovador{idx+1}"]
                                p_email = APROVADORES[idx]
                                icon = "✅" if v_status == "Aprovado" else "❌" if v_status == "Reprovado" else "⚠️" if v_status == "Aprovado com ressalva" else "⏳"
                                st.markdown(f"{icon} Aprovador {idx+1}: `{v_status}`")

        with tab_logs:
            st.markdown("### 📜 Log Geral de Atividades e Auditoria")
            st.markdown("Trilha de auditoria completa em dropdown. Cada chamado exibe o histórico cronológico de interações desde a sua abertura.")
            
            if df_dados.empty:
                st.info("Nenhum chamado registrado para gerar logs.")
            else:
                for _, row in df_dados.iterrows():
                    id_c = int(row['ID'])
                    titulo_c = row['Titulo']
                    status_final = row['Status_Final']
                    historico_notas = str(row.get("Motivo_Recusa", "")).strip()
                    
                    with st.expander(f"📜 Logs do Chamado #{id_c} - {titulo_c} (Status: {status_final})"):
                        st.markdown(f"**Resumo das Configurações do Chamado:**")
                        st.write(f"• **Solicitante Original:** {row['Remetente_Nome']} (`{row['Remetente_Email']}`)")
                        st.write(f"• **Situação das Alçadas:** A1: `{row['Voto_Aprovador1']}` | A2: `{row['Voto_Aprovador2']}` | A3: `{row['Voto_Aprovador3']}`")
                        st.markdown("---")
                        st.markdown("**Linha do Tempo de Eventos:**")
                        
                        if historico_notas and historico_notas.lower() not in ["nan", "none", ""]:
                            notas_separadas = historico_notas.split(" | ")
                            for nota in notas_separadas:
                                if not nota.strip():
                                    continue
                                if "REPROVOU" in nota or "Sistema: Chamado finalizado com Reprovação" in nota:
                                    st.error(f"🔴 {nota}")
                                elif "Ressalva" in nota or "Aprovado com ressalva" in nota:
                                    st.warning(f"🟡 {nota}")
                                elif "abriu a solicitação" in nota or "Solicitação Criada" in nota:
                                    st.success(f"🟢 {nota}")
                                else:
                                    st.info(f"ℹ️ {nota}")
                        else:
                            st.caption("ℹ️ Chamado aguardando ações ou criado antes da implementação da trilha de tempo real.")

        with tab_indicadores:
            st.markdown("### 📈 Painel Analítico de Governança")
            
            if df_dados.empty:
                st.info("Dados insuficientes para gerar indicadores gráficos.")
            else:
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                total_chamados = len(df_dados)
                finalizados_ap = len(df_dados[df_dados["Status_Final"] == "Aprovado"])
                finalizados_rep = len(df_dados[df_dados["Status_Final"] == "Reprovado"])
                em_analise = len(df_dados[df_dados["Status_Final"] == "Em análise"])
                
                with kpi1: st.metric("Total de Chamados", total_chamados)
                with kpi2: st.metric("Aprovados Totais", finalizados_ap)
                with kpi3: st.metric("Reprovados Totais", finalizados_rep)
                with kpi4: st.metric("Em Análise", em_analise)
                
                st.markdown("---")
                
                graf1, graf2 = st.columns(2)
                
                with graf1:
                    st.markdown("##### 📊 Status Finais do Sistema")
                    status_counts = df_dados["Status_Final"].value_counts().reset_index()
                    status_counts.columns = ["Status", "Quantidade"]
                    st.bar_chart(data=status_counts, x="Status", y="Quantidade", use_container_width=True)
                    
                with graf2:
                    st.markdown("##### 🏢 Volumetria por Perfil de Votos (Sua Alçada)")
                    voto_counts = df_dados[coluna_voto].value_counts().reset_index()
                    voto_counts.columns = ["Seu Parecer", "Quantidade"]
                    st.bar_chart(data=voto_counts, x="Seu Parecer", y="Quantidade", use_container_width=True)
                    
                st.markdown("##### 📅 Volume de Chamados em Andamento no Fluxo")
                df_dados['Mês'] = datetime.datetime.now().strftime("%m/%Y")
                mes_counts = df_dados["Mês"].value_counts().reset_index()
                mes_counts.columns = ["Período", "Total de Requisições"]
                st.line_chart(data=mes_counts, x="Período", y="Total de Requisições", use_container_width=True)
    else:
        st.info("Nenhuma estrutura de dados mapeada.")

else:
    st.markdown("---")
    tab_novo, tab_status = st.tabs(["📝 Nova Solicitação de Compra", "📊 Status e Histórico dos meus Pedidos"])
    
    with tab_novo:
        st.markdown("### Formulário de Requisição Padrão")
        st.markdown("Preencha as informações abaixo para iniciar o processo de governança.")
        
        PASTA_DRIVE_ID = "1YM8-vbxx0nMKD_5b0xZ8plr_iw7I9k7R" 
        
        with st.form("form_requisicao", clear_on_submit=True):
            st.markdown("<h4 style='color: #005691;'>Identificação da Demanda</h4>", unsafe_allow_html=True)
            titulo = st.text_input("Título do Projeto/Solicitação de Compra:", placeholder="Ex: Aquisição de novos desfibriladores - UTI Leste")
            
            st.markdown("<br><h4 style='color: #005691;'>Especificações Técnicas</h4>", unsafe_allow_html=True)
            centro_custo = st.selectbox(
                "Centro de Custo / Setor Destinado:",
                options=["Selecione uma opção...", "UTI Adulto", "UTI Pediátrica", "Centro Cirúrgico", "Pronto Atendimento"]
            )
            
            observacoes_tecnicas = st.text_input("Especificação Resumida ou Part Number (Opcional):")
            
            arquivo_anexo = st.file_uploader(
                "Anexar Arquivos (Orçamentos, Projetos ou Laudos Técnicos):",
                type=["pdf", "docx", "xlsx", "png", "jpg"]
            )
            
            st.markdown("<br><h4 style='color: #005691;'>Detalhamento</h4>", unsafe_allow_html=True)
            descricao = st.text_area("Descrição detalhada da demanda:", height=150)
            justificativa = st.text_area("Justificativa / Impacto para o Hospital:", height=100)
            
            st.markdown("---")
            enviar = st.form_submit_button("🚀 Enviar Solicitação para Governanças", use_container_width=True)
            
            if enviar:
                if titulo and descricao:
                    proximo_id = int(df_dados["ID"].max() + 1) if not df_dados.empty and "ID" in df_dados.columns else 1
                    cc_selecionado = centro_custo if centro_custo != "Selecione uma opção..." else "Não informado"
                    
                    link_drive_arquivo = "Nenhum arquivo anexado"
                    
                    if arquivo_anexo is not None:
                        with st.spinner("Fazendo upload do anexo para a pasta segura no Google Drive..."):
                            link_drive_arquivo = upload_para_google_drive(arquivo_anexo, pasta_id=PASTA_DRIVE_ID)
                            if not link_drive_arquivo:
                                link_drive_arquivo = f"https://drive.google.com/drive/folders/{PASTA_DRIVE_ID}"
                    
                    # Gera o carimbo de data e hora de criação do log
                    timestamp_criacao = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                    log_inicial = f"{timestamp_criacao} - {user_name} ({user_email}) abriu a solicitação de compra."
                    
                    nova_linha = pd.DataFrame([{
                        "ID": proximo_id,
                        "Remetente_Nome": user_name,
                        "Remetente_Email": user_email,
                        "Titulo": f"[{cc_selecionado}] {titulo}",
                        "Descricao": descricao, 
                        "Justificativa": justificativa,
                        "Link_Anexo": link_drive_arquivo, 
                        "Voto_Aprovador1": "Pendente",
                        "Voto_Aprovador2": "Pendente",
                        "Voto_Aprovador3": "Pendente",
                        "Status_Final": "Em análise",
                        "Motivo_Recusa": log_inicial
                    }])
                    
                    df_dados = pd.concat([df_dados, nova_linha], ignore_index=True)
                    conn.update(data=df_dados)
                    st.success(f"🎉 Solicitação #{proximo_id} enviada com sucesso para análise!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Por favor, preencha o Título e a Descrição do chamado.")

    with tab_status:
        st.markdown("### Seus Pedidos e Andamento")
        if not df_dados.empty and "Remetente_Email" in df_dados.columns:
            meus_pedidos = df_dados[df_dados["Remetente_Email"] == user_email]
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
                    
                    with st.expander(f"📋 Chamado #{id_c} - {row['Titulo']} [{status_atual}]"):
                        st.markdown(f"Status Final: <span style='color: {cor_status}; font-weight: bold;'>{status_atual}</span>", unsafe_allow_html=True)
                        st.write(f"**Descrição:** {row['Descricao']}")
                        
                        st.markdown("---")
                        st.markdown("<b>Linha do tempo dos avaliadores:</b>", unsafe_allow_html=True)
                        
                        v1, v2, v3 = st.columns(3)
                        for idx, ap_col in enumerate([v1, v2, v3]):
                            ap_email = APROVADORES[idx]
                            voto = row[f"Voto_Aprovador{idx+1}"]
                            with ap_col:
                                if voto == "Pendente": st.caption(f"⏳ **Em análise**\n`{ap_email}`")
                                elif voto == "Aprovado": st.success(f"✅ **Aprovado**\n`{ap_email}`")
                                elif voto == "Aprovado com ressalva": st.warning(f"⚠️ **Com Ressalva**\n`{ap_email}`")
                                else: st.error(f"❌ **Reprovado**\n`{ap_email}`")
                        
                        historico_notas = str(row.get("Motivo_Recusa", "")).strip()
                        if historico_notas and historico_notas.lower() not in ["nan", "none", ""]:
                            st.markdown("---")
                            st.markdown("##### 📋 Histórico de Apontamentos da Governança")
                            notas_separadas = historico_notas.split(" | ")
                            for nota in notas_separadas:
                                if "REPROVOU" in nota: st.error(f"🔴 {nota}")
                                elif "Ressalva" in nota: st.warning(f"🟡 {nota}")
                                else: st.info(f"ℹ️ {nota}")
        else:
            st.info("Nenhuma solicitação encontrada.")
