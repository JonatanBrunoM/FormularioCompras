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
# 3. Configurações de E-mail e Banco de Dados
# ==============================================================================
ADMINS = [
    "jonatan231196@gmail.com",
    "debora.bairros@hmv.org.br",
    "sandro.carmo@hmv.org.br"
]

MAPA_PERMISSOES = {
    "V": ADMINS,  
    "W": ["jonatan231196@gmail.com"],  # Segurança Ocupacional
    "X": ["carolina.jagielski@hmv.org.br"],      # Saúde Ocupacional
    "Y": ["sandro.carmo@hmv.org.br"],                    # SCI
    "Z": ["gustavo.oliveira@hmv.org.br"],     # Engenharia Clínica
    "AA": ["gps.lidya@hmv.org.br"],     # Gestão Ambiental
    "AB": ["debora.bairros@hmv.org.br"]     # Prevenção de Incêndio
}

TODOS_SUB_APROVADORES = [email for lista in MAPA_PERMISSOES.values() for email in lista]
APROVADORES = list(set(ADMINS + TODOS_SUB_APROVADORES))

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
# 8. Tela aprovadores
# ==============================================================================
if is_aprovador:
    st.markdown("---")
    
    ALCADAS_INFO = {
        "Voto_Aprovador1": {"letra": "V", "label": "V - Padronização (suprimentos)", "prazo": "Fluxo Contínuo"},
        "Voto_Aprovador2": {"letra": "W", "label": "W - Segurança Ocupacional", "prazo": "7 dias úteis"},
        "Voto_Aprovador3": {"letra": "X", "label": "X - Saúde Ocupacional", "prazo": "7 dias úteis"},
        "Voto_Aprovador4": {"letra": "Y", "label": "Y - SCI", "prazo": "5 dias úteis"},
        "Voto_Aprovador5": {"letra": "Z", "label": "Z - Engenharia clínica e eletromecânica", "prazo": "5 dias úteis"},
        "Voto_Aprovador6": {"letra": "AA", "label": "AA - Gestão Ambiental", "prazo": "5 dias úteis"},
        "Voto_Aprovador7": {"letra": "AB", "label": "AB - Prevenção de Incêndio", "prazo": "5 dias úteis"}
    }
    
    colunas_permitidas_usuario = []
    is_user_admin = user_email in ADMINS
    
    for col_voto, letra_col in zip(ALCADAS_INFO.keys(), ["V", "W", "X", "Y", "Z", "AA", "AB"]):
        if is_user_admin or user_email in MAPA_PERMISSOES.get(letra_col, []):
            colunas_permitidas_usuario.append(col_voto)

    if not df_dados.empty:
        condicao_pendente = (df_dados["Status_Final"] == "Em análise") & (
            df_dados[colunas_permitidas_usuario].eq("Pendente").any(axis=1)
        )
        pendentes = df_dados[condicao_pendente]
        
        condicao_historico = df_dados[colunas_permitidas_usuario].isin(["Aprovado", "Reprovado"]).any(axis=1)
        historico_aprovador = df_dados[condicao_historico]
        
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
        
        # 8.1. Aba "Minhas pendências"
        with tab_pendentes:
            st.markdown("### Solicitações aguardando seu parecer técnico")
            if pendentes.empty:
                st.success("Nenhuma solicitação pendente para a sua alçada técnica no momento.")
            else:
                for _, row in pendentes.iterrows():
                    id_chamado = row["ID"]
                    
                    descricao_produto = row.get("Descrição completa do produto", "Sem descrição do produto")
                    
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
                        
                        st.markdown("<br>Seus Seu parecer:", unsafe_allow_html=True)
                        
                        for col_voto, info in ALCADAS_INFO.items():
                            if col_voto in colunas_permitidas_usuario and row[col_voto] == "Pendente":
                                with st.container(border=True):
                                    st.markdown(f"**Alçada:** `{info['label']}` | **Prazo:** `{info['prazo']}`")
                                    
                                    key_voto = f"voto_escolha_{id_chamado}_{col_voto}"
                                    key_parecer = f"parecer_text_{id_chamado}_{col_voto}"
                                    
                                    voto_selecionado = st.radio(
                                        "Decisão da Alçada:",
                                        options=["Aprovar", "Reprovar"],
                                        format_func=lambda x: "👍  Aprovar" if x == "Aprovar" else "👎 Reprovar",
                                        index=None,
                                        horizontal=True,
                                        key=key_voto
                                    )
                                    
                                    if voto_selecionado:
                                        parecer_texto = st.text_area(f"Parecer técnico para {info['letra']} (Obrigatório):", key=key_parecer)
                                        
                                        if st.button(f"Confirmar parecer {info['letra']}", key=f"btn_salvar_{id_chamado}_{col_voto}", type="primary"):
                                            if not parecer_texto.strip():
                                                st.error("Por favor, preencha o campo Parecer antes de confirmar.")
                                            else:
                                                valor_final_voto = "Aprovado" if voto_selecionado == "Aprovar" else "Reprovado"
                                                df_dados.loc[df_dados["ID"] == id_chamado, col_voto] = valor_final_voto
                                                
                                                fuso_br = datetime.timezone(datetime.timedelta(hours=-3))
                                                timestamp_atual = datetime.datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                                                nota_atual = str(df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"].values[0]).replace("nan", "").replace("None", "")
                                                
                                                nova_nota = f" | {timestamp_atual} - {user_name} ({info['letra']}) avaliou como {valor_final_voto.upper()}. Parecer: {parecer_texto}"
                                                df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = nota_atual + nova_nota
                                                
                                                linha_atualizada = df_dados[df_dados["ID"] == id_chamado].iloc[0]
                                                todos_votos = [linha_atualizada[c] for c in ALCADAS_INFO.keys()]
                                                
                                                if "Reprovado" in todos_votos:
                                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Reprovado"
                                                    html_fim = f"<h3>CAPROQ: Chamado #{id_chamado} Indeferido</h3><p>O processo foi encerrado pois recebeu parecer desfavorável na alçada técnica: {info['label']}.</p><p><b>Parecer:</b> {parecer_texto}</p>"
                                                    enviar_email(destinatario=row["Endereço de e-mail"], assunto=f"CAPROQ: Processo Encerrado (Reprovado) - #{id_chamado}", corpo_html=html_fim)
                                                
                                                elif todos_votos.count("Aprovado") == 7:
                                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Aprovado"
                                                    html_fim = f"<h3>CAPROQ: Chamado #{id_chamado} Homologado!</h3><p>A solicitação foi integralmente aprovada por todas as 7 alçadas do comitê técnico.</p>"
                                                    enviar_email(destinatario=row["Endereço de e-mail"], assunto=f"CAPROQ: Homologação Concluída - #{id_chamado}", corpo_html=html_fim)
                                                
                                                conn.update(data=df_dados)
                                                st.success("Seu parecer técnico foi computado com sucesso!")
                                                time.sleep(1.2)
                                                st.rerun()

        # 8.2. Aba "Histórico de aprovações"
        with tab_hist_aprovador:
            st.markdown("Seus pareceres anteriores registrados")
            if historico_aprovador.empty:
                st.info("Sua alçada técnica atual ainda não emitiu votos históricos no sistema.")
            else:
                for _, row in historico_aprovador.iterrows():
                    id_c = int(row['ID'])
                    desc_h = row.get("Descrição completa do produto", "Sem descrição")
                    with st.expander(f"📋 Chamado #{id_c} — {desc_h} (Status Final: {row['Status_Final']})"):
                        st.markdown("**Status detalhado de cada alçada técnica neste chamado:**")
                        
                        col_h1, col_h2 = st.columns(2)
                        with col_h1:
                            for col_voto, info in list(ALCADAS_INFO.items())[:4]:
                                v_status = row[col_voto]
                                icon = "✅" if v_status == "Aprovado" else "❌" if v_status == "Reprovado" else "⏳"
                                st.markdown(f"{icon} **{info['letra']}:** `{v_status}`")
                        with col_h2:
                            for col_voto, info in list(ALCADAS_INFO.items())[4:]:
                                v_status = row[col_voto]
                                icon = "✅" if v_status == "Aprovado" else "❌" if v_status == "Reprovado" else "⏳"
                                st.markdown(f"{icon} **{info['letra']}:** `{v_status}`")

        # 8.3. Aba "Log de registros"
        with tab_logs:
            st.markdown("Logs e registros")
            for _, row in df_dados.iterrows():
                id_c = int(row['ID'])
                desc_l = row.get("Descrição completa do produto", "Sem descrição")
                historico_notes = str(row.get("Motivo_Recusa", "")).strip()
                
                with st.expander(f"Linha de Tempo — Chamado #{id_c} — {desc_l} (Status: {row['Status_Final']})"):
                    if historico_notes and historico_notes.lower() not in ["nan", "none", ""]:
                        notas_separadas = historico_notes.split(" | ")
                        for nota in notas_separadas:
                            if not nota.strip(): continue
                            if "REPROVOU" in nota or "Indeferido" in nota:
                                st.error(f"🔴 {nota}")
                            elif "aprovou" in nota or "AVALIOU COMO APROVADO" in nota or "Criada" in nota:
                                st.success(f"🟢 {nota}")
                            else:
                                f"ℹ️ {nota}"
                    else:
                        st.caption("Sem registros históricos gravados neste evento.")

        # 8.4. Aba "Painel analítico"
        with tab_indicadores:
            st.markdown("Painel analítico (CAPROQ)")
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
            
            st.markdown("Volumetria temporal de requisições")
            kpi_t1, kpi_t2, kpi_t3, kpi_t4 = st.columns(4)
            with kpi_t1: st.metric("Últimos 7 dias (Semanal)", qtd_semana)
            with kpi_t2: st.metric("Últimos 30 dias (Mensal)", qtd_mes)
            with kpi_t3: st.metric("Último Ano (Anual)", qtd_ano)
            with kpi_t4: st.metric("Total Histórico", len(df_dados))
            
            st.markdown("---")
            
            st.markdown("Distribuição estatística de deliberações (Mensal)")
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
                    historico = str(r.get("Motivo_Recusa", "")).lower()
                    
                    if status == "Reprovado":
                        recusas += 1
                    elif status == "Aprovado":
                        if "ressalva" in historico or "ajuste" in historico or "pendente" in historico:
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
            
            # 8.5. Aba "Separação de dados por área"
            st.markdown("Performance de fluxo por alçada (Histórico)")
            
            dados_areas = []
            for col_voto, info in ALCADAS_INFO.items():
                if col_voto in df_dados.columns:
                    votos = df_dados[col_voto].value_counts()
                    dados_areas.append({
                        "Alçada": info["letra"],
                        "Nome": info["label"].split(" - ")[-1],
                        "Concluídos": votos.get("Aprovado", 0) + votos.get("Reprovado", 0),
                        "Pendentes": votos.get("Pendente", 0)
                    })
            
            if dados_areas:
                df_areas = pd.DataFrame(dados_areas)
                
                st.dataframe(
                    df_areas, 
                    column_config={
                        "Alçada": st.column_config.TextColumn("Sigla"),
                        "Nome": st.column_config.TextColumn("Área Técnica"),
                        "Concluídos": st.column_config.NumberColumn("Pareceres emitidos", format="%d ✅"),
                        "Pendentes": st.column_config.NumberColumn("Demandas em aberto", format="%d ⏳"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                import plotly.express as px
                fig_barras_areas = px.bar(
                    df_areas, 
                    x="Nome", 
                    y=["Concluídos", "Pendentes"],
                    title="Volume de Trabalho por Alçada (Emitidos vs Pendentes)",
                    barmode="group",
                    color_discrete_sequence=["#2ecc71", "#e67e22"]
                )
                fig_barras_areas.update_layout(xaxis_title="Área Técnica", yaxis_title="Quantidade de Chamados", height=300)
                st.plotly_chart(fig_barras_areas, use_container_width=True)
            else:
                st.info("Mapeamento de colunas das alçadas não localizado na planilha atual.")

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
            
            if enviar:
                campos_vazios = [campo["label"] for campo in CONFIG_CAMPOS if campo["obrigatorio"] and not respostas_formulario[campo["label"]]]
                
                if not fds_obrigatorio:
                    campos_vazios.append("Anexar FDS")
                
                pergunta_estudos_label = "O produto apresenta estudos científicos e de custo-efetividade comparado com o utilizado atualmente no HMV? Caso sim, anexe o arquivo abaixo."
                resposta_estudos = respostas_formulario.get(pergunta_estudos_label, "")
                
                if resposta_estudos == "Sim" and not arquivo_estudos:
                    campos_vazios.append("Anexo arquivo de estudos científicos e de custo-efetividade (Obrigatório quando a resposta for SIM)")
                
                if campos_vazios:
                    st.error(f"❌ Por favor, preencha ou anexe os seguintes campos obrigatórios:\n" + "\n".join([f"• {c}" for c in campos_vazios]))
                else:
                    with st.spinner("Processando anexos e enviando para o Google Drive..."):
                        proximo_id = int(df_dados["ID"].max() + 1) if not df_dados.empty and "ID" in df_dados.columns else 1
                        
                        # Upload dos arquivos obrigatórios e opcionais
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
        
                        log_inicial = f"{timestamp_criacao} - {user_name} ({user_email}) abriu a solicitação de compra."
                        
                        dados_estruturais = {
                            "ID": proximo_id,
                            "Nome solicitante": user_name,
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
                        
                        registro_completo = {**respostas_formulario, **dados_estruturais}
                        nova_linha = pd.DataFrame([registro_completo])
                        
                        df_dados = pd.concat([df_dados, nova_linha], ignore_index=True)
                        conn.update(data=df_dados)
                        st.session_state["df_dados"] = df_dados
                        
                        txt_descricao = respostas_formulario.get("Descrição completa do produto", "Não informado")
                        txt_apresentacao = respostas_formulario.get("Apresentação/volume", "Não informado")
                        txt_area_uso = respostas_formulario.get("Área onde será utilizado e indicação detalhada de uso do produto", "Não informado")
                        txt_fabricante = respostas_formulario.get("Fabricante/fornecedor", "Não informado")
                        txt_sem_produto = respostas_formulario.get("Explique como o procedimento/atividade actual é realizado SEM este produto:", "Não informado")
                        
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

    # 9.2. Aba status
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
                        st.markdown("<b>Linha do tempo dos avaliadores:</b>", unsafe_allow_html=True)
                        
                        colunas_aprovadores = st.columns(7)
                        
                        for idx, ap_col in enumerate(colunas_aprovadores):
                            if idx < len(APROVADORES):
                                ap_email = APROVADORES[idx]
                                voto = row.get(f"Voto_Aprovador{idx+1}", "Pendente")
                                
                                with ap_col:
                                    if voto == "Pendente": 
                                        st.caption(f"⏳ **Pendente**\n`Aprovador {idx+1}`")
                                    elif voto == "Aprovado": 
                                        st.caption(f"✅ **Aprovado**\n`Aprovador {idx+1}`")
                                    elif voto == "Aprovado com ressalva": 
                                        st.caption(f"⚠️ **Ressalva**\n`Aprovador {idx+1}`")
                                    else: 
                                        st.caption(f"❌ **Reprovado**\n`Aprovador {idx+1}`")
                        
                        historico_notas = str(row.get("Motivo_Recusa", "")).strip()
                        if historico_notas and historico_notas.lower() not in ["nan", "none", ""]:
                            st.markdown("---")
                            st.markdown("Histórico de apontamentos")
                            notas_separadas = historico_notas.split(" | ")
                            for nota in notas_separadas:
                                if "REPROVOU" in nota: st.error(f"🔴 {nota}")
                                elif "Ressalva" in nota: st.warning(f"🟡 {nota}")
                                else: st.info(f"ℹ️ {nota}")
        else:
            st.info("Nenhuma solicitação encontrada.")
