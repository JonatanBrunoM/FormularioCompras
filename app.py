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
# 3. Configurações de E-mail e Banco de Dados
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
# 7. Interface principal (leituras com fallbacks de segurança)
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
# 8. Distribuição de abas por Perfil
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
        
        tab_pendentes, tab_hist_aprovador, tab_logs, tab_indicadores = st.tabs([
            "Minhas pendências", 
            "Histórico de decisões",
            "Log de atividades",
            "Indicadores"
        ])
        
        with tab_pendentes:
            st.markdown("### Solicitações pendentes de seu parecer")
            if pendentes.empty:
                st.success("Nenhuma solicitação pendente para você no momento.")
            else:
                for _, row in pendentes.iterrows():
                    id_chamado = row["ID"]
                    with st.container(border=True):
                        st.markdown(f"#### Chamado #{id_chamado} - {row['Titulo']}")
                        st.markdown(f"**Solicitante:** {row['Remetente_Nome']} (`{row['Remetente_Email']}`)")
                        
                        with st.expander("🔍 Visualizar detalhes da solicitação", expanded=False):
                            st.markdown("---")
                            st.markdown("##### 📝 Descrição do pedido:")
                            st.write(row['Descricao'])
                            st.markdown("##### 💡 Justificativa:")
                            st.write(row['Justificativa'])
                            
                            if "Link_Anexo" in row and row["Link_Anexo"] != "Nenhum arquivo anexado":
                                document_icon = "📂"
                                st.markdown("##### 📎 Documentação adjunta:")
                                st.link_button(f"{document_icon} Abrir anexo no Google Drive", row["Link_Anexo"], use_container_width=True)
                            st.markdown("---")
                        
                        if f"recusando_{id_chamado}" not in st.session_state:
                            st.session_state[f"recusando_{id_chamado}"] = False
                        if f"ressalvando_{id_chamado}" not in st.session_state:
                            st.session_state[f"ressalvando_{id_chamado}"] = False
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # --- EXIBIÇÃO DOS BOTÕES ---
                        if not st.session_state[f"recusando_{id_chamado}"] and not st.session_state[f"ressalvando_{id_chamado}"]:
                            col_ap, col_res, col_rep = st.columns([2.5, 3.2, 2.3])
                            
                            if col_ap.button("👍 Aprovar", key=f"ap_{id_chamado}", use_container_width=True):
                                df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Aprovado"

                                fuso_br = datetime.timezone(datetime.timedelta(hours=-3))
                                timestamp_atual = datetime.datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                                nota_atual = str(df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0]).replace("nan", "").replace("None", "")
                                nova_nota = f" | {timestamp_atual} - {user_name} aprovou a solicitação."
                                df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = nota_atual + nova_nota

                                linha_atualizada = df_dados[df_dados["ID"] == id_chamado].iloc[0]
                                votos = [linha_atualizada["Voto_Aprovador1"], linha_atualizada["Voto_Aprovador2"], linha_atualizada["Voto_Aprovador3"]]

                                if votos.count("Aprovado") == 3:
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Aprovado"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0] + f" | {timestamp_atual} - Sistema: Chamado finalizado com aprovação total."

                                    html_sucesso = f"""
                                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                                        <h3 style='color: #005691;'>HOSPITAL MOINHOS DE VENTO</h3>
                                        <p style='color: #2b2b2b; font-size: 1.1em;'>✅ <b>Chamado #{id_chamado}</b> foi totalmente APROVADO!</p>
                                        <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                                        <p><b>Título do Projeto:</b> {row['Titulo']}</p>
                                        <p><b>Solicitante:</b> {row['Remetente_Nome']} ({row['Remetente_Email']})</p>
                                        <br>
                                        <p style='color: #6c757d; font-size: 0.9em;'>Todos os 3 membros do comitê CAPROQ deram parecer positivo técnico.</p>
                                    </div>
                                    """
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"CAPROQ: Solicitação Aprovada! - #{id_chamado}", corpo_html=html_sucesso)
                                    for aprovador_email in APROVADORES:
                                        enviar_email(destinatario=aprovador_email, assunto=f"CAPROQ: Chamado #{id_chamado} Finalizado (Aprovado)", corpo_html=html_sucesso)
                            
                                conn.update(data=df_dados)
                                st.success("Voto registrado com sucesso!")
                                time.sleep(1)
                                st.rerun()
                            
                            if col_res.button("⚠️ Aprovar c/ Ressalva", key=f"res_gatilho_{id_chamado}", use_container_width=True):
                                st.session_state[f"ressalvando_{id_chamado}"] = True
                                st.rerun()
                                
                            if col_rep.button("👎 Reprovar", key=f"rep_gatilho_{id_chamado}", use_container_width=True):
                                st.session_state[f"recusando_{id_chamado}"] = True
                                st.rerun()

                        elif st.session_state[f"ressalvando_{id_chamado}"]:
                            st.markdown("⚠️ **Descreva a ressalva técnica ou financeira proposta abaixo:**")
                            ressalva_texto = st.text_input("Ressalva (Obrigatório):", key=f"input_res_{id_chamado}")
                            col_conf_res, col_canc_res = st.columns([3, 7])
                            
                            if col_conf_res.button("Confirmar Ressalva", key=f"conf_res_{id_chamado}", use_container_width=True):
                                if ressalva_texto.strip():
                                    df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Aprovado com ressalva"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Aprovado com ressalva"
                                    
                                    fuso_br = datetime.timezone(datetime.timedelta(hours=-3))
                                    timestamp_atual = datetime.datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                                    nota_atual = str(df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0]).replace("nan", "").replace("None", "")
                                    nova_nota = f" | {timestamp_atual} - {user_name} inseriu uma Ressalva: {ressalva_texto}"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = nota_atual + nova_nota
                                    
                                    html_ressalva = f"""
                                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                                        <h3 style='color: #E6A23C;'>HOSPITAL MOINHOS DE VENTO</h3>
                                        <p style='color: #2b2b2b; font-size: 1.1em;'>⚠️ O <b>Chamado #{id_chamado}</b> foi finalizado com <b>RESSALVA</b>.</p>
                                        <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                                        <p><b>Título do Projeto:</b> {row['Titulo']}</p>
                                        <p><b>Solicitante:</b> {row['Remetente_Nome']} ({row['Remetente_Email']})</p>
                                        <p><b>Ressalva Técnica:</b> {ressalva_texto}</p>
                                    </div>
                                    """
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"CAPROQ: Solicitação com Ressalva - #{id_chamado}", corpo_html=html_ressalva)
                                    for aprovador_email in APROVADORES:
                                        enviar_email(destinatario=aprovador_email, assunto=f"CAPROQ: Chamado #{id_chamado} Finalizado com Ressalva", corpo_html=html_ressalva)
                                    
                                    conn.update(data=df_dados)
                                    st.session_state[f"ressalvando_{id_chamado}"] = False
                                    st.rerun()
                                    
                            if col_canc_res.button("Cancelar", key=f"canc_res_{id_chamado}", use_container_width=True):
                                st.session_state[f"ressalvando_{id_chamado}"] = False
                                st.rerun()

                        elif st.session_state[f"recusando_{id_chamado}"]:
                            st.markdown("❌ **Explique o motivo da recusa abaixo:**")
                            motivo = st.text_input("Motivo da Reprovação (Obrigatório):", key=f"input_motivo_{id_chamado}")
                            col_conf, col_canc = st.columns([3, 7])
                            
                            if col_conf.button("Confirmar eficiência", key=f"conf_rep_{id_chamado}", use_container_width=True):
                                if motivo.strip():
                                    df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Reprovado"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Reprovado"
                                    
                                    fuso_br = datetime.timezone(datetime.timedelta(hours=-3))
                                    timestamp_atual = datetime.datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                                    nota_atual = str(df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0]).replace("nan", "").replace("None", "")
                                    nova_nota = f" | {timestamp_atual} - {user_name} REPROVOU o chamado. Motivo: {motivo}"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = nota_atual + nova_nota
                                    
                                    html_reprovado = f"""
                                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                                        <h3 style='color: #D93025;'>HOSPITAL MOINHOS DE VENTO</h3>
                                        <p style='color: #2b2b2b; font-size: 1.1em;'>❌ O <b>Chamado #{id_chamado}</b> foi <b>REPROVADO</b>.</p>
                                        <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                                        <p><b>Título do Projeto:</b> {row['Titulo']}</p>
                                        <p><b>Solicitante:</b> {row['Remetente_Nome']} ({row['Remetente_Email']})</p>
                                        <p><b>Motivo do Indeferimento:</b> {motivo}</p>
                                    </div>
                                    """
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"CAPROQ: Solicitação Recusada - #{id_chamado}", corpo_html=html_reprovado)
                                    for aprovador_email in APROVADORES:
                                        enviar_email(destinatario=aprovador_email, assunto=f"CAPROQ: Chamado #{id_chamado} Finalizado (Reprovado)", corpo_html=html_reprovado)
                                    
                                    conn.update(data=df_dados)
                                    st.session_state[f"recusando_{id_chamado}"] = False
                                    st.rerun()
                                    
                            if col_canc.button("Cancelar", key=f"canc_rep_{id_chamado}", use_container_width=True):
                                st.session_state[f"recusando_{id_chamado}"] = False
                                st.rerun()

        with tab_hist_aprovador:
            st.markdown("### Histórico avançado de decisões")
            st.markdown("Visualize as suas decisões anteriores combinadas com a posição atual do painel.")
            
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
            st.markdown("### Log geral de atividades")
            st.markdown("Histórico completo de movimentações dos chamados.")
            
            if df_dados.empty:
                st.info("Nenhum chamado registrado para gerar logs.")
            else:
                for _, row in df_dados.iterrows():
                    id_c = int(row['ID'])
                    titulo_c = row['Titulo']
                    status_final = row['Status_Final']
                    historico_notas = str(row.get("Motivo_Recusa", "")).strip()
                    
                    with st.expander(f"📜 Logs do chamado #{id_c} - {titulo_c} (Status: {status_final})"):
                        st.markdown(f"**Resumo das configurações do chamado:**")
                        st.write(f"• **Solicitante original:** {row['Remetente_Nome']} (`{row['Remetente_Email']}`)")
                        st.write(f"• **Situação das aprovações:** A1: `{row['Voto_Aprovador1']}` | A2: `{row['Voto_Aprovador2']}` | A3: `{row['Voto_Aprovador3']}`")
                        st.markdown("---")
                        st.markdown("**Linha do tempo de eventos:**")
                        
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
            st.markdown("### Painel analítico")
            
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
    tab_novo, tab_status = st.tabs(["Nova solicitação de compra", "Status e histórico dos meus pedidos"])
    
    with tab_novo:
        st.markdown("### Formulário de requisição padrão")
        st.markdown("Preencha as informações abaixo para iniciar o processo.")
    
        PASTA_DRIVE_ID = "1YM8-vbxx0nMKD_5b0xZ8plr_iw7I9k7R" 
    
        # --- CONFIGURAÇÃO DINÂMICA DOS CAMPOS (Mapeamento do Sheets) ---
        CONFIG_CAMPOS = [
            # SEÇÃO 1: Identificação do Produto e Fornecedor
            {"id": "descricao", "label": "Descrição completa do produto", "tipo": "area_texto", "secao": "📦 Dados do Produto", "obrigatorio": True},
            {"id": "apresentacao", "label": "Apresentação/volume", "tipo": "texto", "secao": "📦 Dados do Produto", "obrigatorio": True},
            {"id": "area_uso", "label": "Área onde será utilizado e indicação detalhada de uso do produto", "tipo": "area_texto", "secao": "📦 Dados do Produto", "obrigatorio": True},
            {"id": "fabricante", "label": "Fabricante/fornecedor", "tipo": "texto", "secao": "📦 Dados do Produto", "obrigatorio": True},
            {"id": "contato_fornecedor", "label": "Informações de contato do fornecedor (nome, e-mail e telefone)", "tipo": "area_texto", "secao": "📦 Dados do Produto", "obrigatorio": True},
            
            # SEÇÃO 2: Dependências e Processos
            {"id": "insumos_associados", "label": "Equipamentos e/ou insumos associados ao uso do produto?", "tipo": "texto", "secao": "⚙️ Processos e Dependências", "obrigatorio": False},
            {"id": "insumos_quais", "label": "Caso SIM, responder quais seriam?", "tipo": "texto", "secao": "⚙️ Processos e Dependências", "obrigatorio": False},
            {"id": "sem_produto", "label": "Explique como o procedimento/atividade atual é realizado SEM este produto:", "tipo": "area_texto", "secao": "⚙️ Processos e Dependências", "obrigatorio": True},
            
            # SEÇÃO 3: Avaliação de Impacto e Riscos
            {"id": "reducao_tempo", "label": "O produto contribui para a redução de tempo de execução dos procedimentos?", "tipo": "selecao_tripla", "secao": "📊 Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": "reducao_acidentes", "label": "O produto proposto contribui para a redução do risco de acidentes de trabalho?", "tipo": "selecao_tripla", "secao": "📊 Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": "seguranca_paciente", "label": "O produto favorece a segurança do paciente e dos profissionais?", "tipo": "selecao_tripla", "secao": "📊 Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": "reducao_infeccao", "label": "O produto proposto contribui para a redução de risco de infecção hospitalar?", "tipo": "selecao_tripla", "secao": "📊 Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": "requerido_legislacao", "label": "O item é requerido pela legislação, padrões de qualidade e segurança adotados pela instituição?", "tipo": "selecao_tripla", "secao": "📊 Avaliação de Impacto e Segurança", "obrigatorio": True},
            {"id": "residuo_perigoso", "label": "O item solicitado gera resíduo perigoso?", "tipo": "selecao_tripla", "secao": "📊 Avaliação de Impacto e Segurança", "obrigatorio": True},
            
            # SEÇÃO 4: Estudos e Viabilidade
            {"id": "estudos_cientificos", "label": "O produto apresenta estudos científicos e de custo-efetividade comparado com o utilizado atualmente no HMV? Caso sim, anexe o arquivo abaixo.", "tipo": "selecao_binaria", "secao": "🔬 Estudos e Viabilidade", "obrigatorio": True},
        ]
    
        respostas_formulario = {}
        
        # Captura automática dos metadados das colunas A e B
        fuso_br = datetime.timezone(datetime.timedelta(hours=-3))
        timestamp_criacao = datetime.datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
        
        respostas_formulario["Carimbo de data/hora"] = timestamp_criacao
        respostas_formulario["Endereço de e-mail"] = user_email
    
        with st.form("form_requisicao", clear_on_submit=False):
            secao_atual = ""
            
            # Renderização automática das seções e perguntas
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
                    respostas_formulario[campo["label"]] = st.selectbox(label_final, options=["", "SIM", "NÃO", "NÃO SE APLICA"], key=campo["id"])
                elif campo["tipo"] == "selecao_binaria":
                    respostas_formulario[campo["label"]] = st.selectbox(label_final, options=["", "SIM", "NÃO"], key=campo["id"])
    
            # --- SEÇÃO EXCLUSIVA DE ANEXOS ---
            # --- SEÇÃO EXCLUSIVA DE ANEXOS ---
            st.markdown("<br><h4 style='color: #005691;'>📎 Arquivos e Documentações</h4>", unsafe_allow_html=True)
            st.markdown("---")
            
            # Colunas D e E
            arquivos_gerais = st.file_uploader("Arquivos anexados (Registro ANVISA, Laudo Técnico, Ficha Técnica, Fabricante):", accept_multiple_files=True)
            fds_obrigatorio = st.file_uploader("Anexar FDS (Obrigatório) *")
            
            # --- CORREÇÃO AQUI: Criamos uma caixinha de seleção dedicada para os estudos dentro dos anexos
            pergunta_estudos = st.checkbox("Desejo anexar arquivos de estudos científicos e de custo-efetividade")
            
            arquivo_estudos = None
            if pergunta_estudos:
                arquivo_estudos = st.file_uploader("Anexo arquivo de estudos científicos e de custo-efetividade. *")
    
            st.markdown("---")
            enviar = st.form_submit_button("Enviar solicitação", use_container_width=True)
            
            if enviar:
                # 1. Validação dinâmica de campos de texto vazios
                campos_vazios = [campo["label"] for campo in CONFIG_CAMPOS if campo["obrigatorio"] and not respostas_formulario[campo["label"]]]
                
                # 2. Validação dos anexos obrigatórios estruturais
                if not fds_obrigatorio:
                    campos_vazios.append("Anexar FDS")
                if possui_estudos == "SIM" and not arquivo_estudos:
                    campos_vazios.append("Anexo arquivo de estudos científicos e de custo-efetividade.")
                    
                if campos_vazios:
                    st.error(f"❌ Por favor, preencha ou anexe os seguintes campos obrigatórios:\n" + "\n".join([f"• {c}" for c in campos_vazios]))
                else:
                    with st.spinner("Processando anexos e enviando para o Google Drive..."):
                        # Cálculo automático do próximo ID incremental
                        proximo_id = int(df_dados["ID"].max() + 1) if not df_dados.empty and "ID" in df_dados.columns else 1
                        
                        # Upload 1: FDS Obrigatório
                        link_fds = upload_para_google_drive(fds_obrigatorio, pasta_id=PASTA_DRIVE_ID)
                        if not link_fds:
                            link_fds = f"https://drive.google.com/drive/folders/{PASTA_DRIVE_ID}"
                            
                        # Upload 2: Estudos Científicos (Se selecionado)
                        link_estudos = "Não aplicável"
                        if possui_estudos == "SIM" and arquivo_estudos:
                            link_estudos = upload_para_google_drive(arquivo_estudos, pasta_id=PASTA_DRIVE_ID)
                            if not link_estudos:
                                link_estudos = f"https://drive.google.com/drive/folders/{PASTA_DRIVE_ID}"
                        
                        # Upload 3: Múltiplos Arquivos Gerais
                        links_gerais = []
                        if arquivos_gerais:
                            for arq in arquivos_gerais:
                                lnk = upload_para_google_drive(arq, pasta_id=PASTA_DRIVE_ID)
                                if lnk:
                                    links_gerais.append(lnk)
                        link_gerais_str = ", ".join(links_gerais) if links_gerais else "Nenhum arquivo adicional"
    
                        # Vincula os links resultantes diretamente às chaves/colunas corretas do dicionário
                        respostas_formulario["Arquivos anexados"] = link_gerais_str
                        respostas_formulario["Anexar FDS"] = link_fds
                        respostas_formulario["Anexo arquivo de estudos científicos e de custo-efetividade."] = link_estudos
    
                        # Geração do log e metadados estruturais do sistema
                        log_inicial = f"{timestamp_criacao} - {user_name} ({user_email}) abriu a solicitação de compra."
                        
                        # Montagem do dicionário base estendido com as colunas estruturais e de voto (7 Aprovadores)
                        dados_estruturais = {
                            "ID": proximo_id,
                            "Remetente_Nome": user_name,
                            "Voto_Aprovador1": "Pendente",
                            "Voto_Aprovador2": "Pendente",
                            "Voto_Aprovador3": "Pendente",
                            "Voto_Aprovador4": "Pendente",
                            "Voto_Aprovador5": "Pendente",
                            "Voto_Aprovador6": "Pendente",
                            "Voto_Aprovador7": "Pendente",
                            "Status_Final": "Em análise",
                            "Motivo_Recusa": log_inicial
                        }
                        
                        # Mescla as respostas coletadas do formulário com as colunas estruturais em um único registro
                        registro_completo = {**respostas_formulario, **dados_estruturais}
                        
                        nova_linha = pd.DataFrame([registro_completo])
                        
                        # Concatena e salva na base de dados (Google Sheets)
                        df_dados = pd.concat([df_dados, nova_linha], ignore_index=True)
                        conn.update(data=df_dados)
                        
                        st.success("✅ Solicitação enviada com absoluto sucesso!")
                        st.balloons()
                    
                    # ==============================================================================
                    # 9. Disparo de e-mails para os aprovadores
                    # ==============================================================================
                    desc_resumida = respostas_formulario.get("Descrição completa do produto", "")[:60] + "..."
                    fabricante_resumido = respostas_formulario.get("Fabricante/fornecedor", "Não Informado")
                    
                    html_novo_chamado = f"""
                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                        <h3 style='color: #005691;'>HOSPITAL MOINHOS DE VENTO</h3>
                        <p style='color: #2b2b2b; font-size: 1.1em;'>🔔 <b>Nova Solicitação Pendente - CAPROQ</b></p>
                        <p style='color: #2b2b2b;'>Um novo chamado de padronização foi aberto e aguarda a sua avaliação técnica.</p>
                        <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                        <p><b>Chamado:</b> #{proximo_id}</p>
                        <p><b>Produto:</b> {desc_resumida}</p>
                        <p><b>Fabricante/Fornecedor:</b> {fabricante_resumido}</p>
                        <p><b>Solicitante:</b> {user_name} ({user_email})</p>
                        <br>
                        <p style='color: #6c757d; font-size: 0.9em;'>Acesse o painel interno para registrar o seu parecer.</p>
                    </div>
                    """
                    
                    for aprovador_email in APROVADORES:
                        enviar_email(
                            destinatario=aprovador_email, 
                            assunto=f"CAPROQ: Nova Solicitação Pendente - #{proximo_id}", 
                            corpo_html=html_novo_chamado
                        )
                    # ==============================================================================
                    
                    st.success(f"🎉 Solicitação #{proximo_id} enviada com sucesso para análise!")
                    time.sleep(1)
                    st.rerun()

    with tab_status:
        st.markdown("### Seus pedidos e andamento")
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
