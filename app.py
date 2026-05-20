import streamlit as st
import requests
import pandas as pd
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google_auth_oauthlib.flow import Flow
from streamlit_gsheets import GSheetsConnection

# ==============================================================================
# 1. Configuração Básica da Página e Design Corporativo
# ==============================================================================
st.set_page_config(
    page_title="Workflow de Aprovações - Hospital Moinhos",
    page_icon="logomini.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Arquitetura CSS Premium para o App
st.markdown("""
<style>
    :root {
        --cor-principal: #005691;
        --cor-secundaria: #008D4C;
        --cinza-texto: #333333;
    }
    
    /* Desativar completamente interações, botões de zoom e download nas imagens */
    [data-testid="stImage"] {
        pointer-events: none !important;
    }
    [data-testid="stImage"] button {
        display: none !important;
    }
    
    /* Títulos e Identidade */
    h1, h2, h3, h4, h5 { color: var(--cor-principal) !important; font-weight: 600 !important; }
    
    /* Estilização Geral de Inputs (Garante contraste em qualquer tema) */
    .stTextInput input, .stTextArea textarea {
        color: var(--cinza-texto) !important;
        background-color: #f8f9fa !important;
        border: 1px solid #ced4da !important;
        border-radius: 6px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--cor-principal) !important;
        box-shadow: 0 0 0 0.2rem rgba(0,86,145,0.25) !important;
    }
    
    /* Customização Robusta do Card do Formulário */
    [data-testid="stForm"] {
        border-radius: 12px !important;
        border: 1px solid #e9ecef !important;
        padding: 30px !important;
        background-color: #ffffff !important;
        box-shadow: 0 4px 16px rgba(0,0,0,0.04) !important;
    }
    
    /* Customização Fina da Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
        border-right: 1px solid #dee2e6 !important;
    }
    .sidebar-user-card {
        padding: 15px;
        background-color: #ffffff;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin-top: 10px;
    }
    .foto-perfil {
        border-radius: 50%;
        border: 2px solid var(--cor-principal);
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    
    /* Box do Layout de Login */
    .login-container {
        max-width: 450px;
        margin: 0 auto;
        padding: 35px;
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        box-shadow: 0 8px 24px rgba(0,0,0,0.05);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. Configurações de E-mail e Banco de Dados (Inalterados)
# ==============================================================================
APROVADORES = ["jonatan231196@gmail.com", "seu_email_real@gmail.com", "seu_email_real@gmail.com"]

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

# --- LOGIN GOOGLE ---
if "connected" not in st.session_state:
    st.session_state.connected = False

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
            scopes=['https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/userinfo.email', 'openid'],
            redirect_uri=st.secrets["GOOGLE_REDIRECT_URI"]
        )
        flow.fetch_token(code=query_params["code"])
        credentials = flow.credentials
        user_info_service = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"}
        ).json()
        st.session_state.connected = True
        st.session_state.name = user_info_service.get("name")
        st.session_state.email = user_info_service.get("email")
        st.session_state.picture = user_info_service.get("picture")
        st.query_params.clear()
        st.rerun()
    except Exception:
        st.query_params.clear()

# ==============================================================================
# 3. Tela de Login Corporativa Clean (Modificada)
# ==============================================================================
if not st.session_state.connected:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    # Criando o container centralizado usando colunas do Streamlit
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        if os.path.exists("logomoinhos.png"):
            st.image("logomoinhos.png", width=220)
        
        st.markdown("<h3 style='margin-top: 15px; font-size: 1.4em;'>Workflow de Aprovações</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color: #6c757d; font-size: 0.95em;'>Acesse o Portal de Governança Institucional</p>", unsafe_allow_html=True)
        st.markdown("<hr style='border: 0; border-top: 1px solid #eee; margin: 20px 0;'>", unsafe_allow_html=True)
        
        auth_url = (
            f"https://accounts.google.com/o/oauth2/auth?"
            f"response_type=code&client_id={st.secrets.get('GOOGLE_CLIENT_ID','')}&"
            f"redirect_uri={st.secrets.get('GOOGLE_REDIRECT_URI','')}&"
            f"scope=https://www.googleapis.com/auth/userinfo.profile%20https://www.googleapis.com/auth/userinfo.email%20openid&prompt=select_account"
        )
        st.link_button("🔑 Acessar com Conta Google", auth_url, type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==============================================================================
# 4. Sidebar Refinada (Modificada)
# ==============================================================================
st.sidebar.markdown("<h3 style='font-size: 1.2em; margin-bottom: 5px;'>Hospital Moinhos</h3>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color: #6c757d; font-size: 0.85em; margin-top:-10px;'>Portal de Suprimentos Corporativos</p>", unsafe_allow_html=True)

# Bloco com Card de informações do Usuário conectado
st.sidebar.markdown('<div class="sidebar-user-card">', unsafe_allow_html=True)
if st.session_state.get("picture"):
    st.sidebar.markdown(f'<img src="{st.session_state.picture}" class="foto-perfil" width="55">', unsafe_allow_html=True)
st.sidebar.markdown(f"<p style='margin-top:10px; margin-bottom:2px; font-weight:bold; color:#333;'>{st.session_state.name}</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<code style='font-size:0.8em; color:#6c757d;'>{st.session_state.email}</code>", unsafe_allow_html=True)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==============================================================================
# 5. Interface Principal (Com Logos Estáticas)
# ==============================================================================
df_dados = carregar_dados()
user_email = st.session_state.email
user_name = st.session_state.name
is_aprovador = user_email in APROVADORES

# Layout de cabeçalho estável e fixo
col_header1, col_header2 = st.columns([1, 4])
if os.path.exists("logomoinhos.png"):
    col_header1.image("logomoinhos.png", width=160)

with col_header2:
    st.title("Central de Aprovações de Compras")
    st.markdown("<p style='color: #6c757d; font-size: 1.1em; margin-top: -15px;'>Fluxo de governança e consenso por alçada de aprovação</p>", unsafe_allow_html=True)

# ==============================================================================
# 6. Fluxos de Alçada (Aprovadores vs Remetentes)
# ==============================================================================
if is_aprovador:
    st.markdown("---")
    num_aprovador = APROVADORES.index(user_email) + 1
    coluna_voto = f"Voto_Aprovador{num_aprovador}"
    
    if not df_dados.empty and coluna_voto in df_dados.columns:
        # Separação lógica: Pendentes atuais vs Histórico do Aprovador (Ponto 5)
        pendentes = df_dados[(df_dados[coluna_voto] == "Pendente") & (df_dados["Status_Final"] == "Em análise")]
        historico_aprovador = df_dados[df_dados[coluna_voto].isin(["Aprovado", "Reprovado"])]
        
        # Métricas rápidas no topo
        m1, m2, m3 = st.columns(3)
        with m1: st.metric("Suas Pendências", len(pendentes))
        with m2: st.metric("Aprovados pelo Fluxo", len(df_dados[df_dados["Status_Final"] == "Aprovado"]))
        with m3: st.metric("Reprovados pelo Fluxo", len(df_dados[df_dados["Status_Final"] == "Reprovado"]))
        
        st.markdown("---")
        
        # Seção 1: Pendências
        st.markdown("### 📥 Solicitações Pendentes de seu Parecer")
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
                        st.markdown(f"##### 📝 Descrição do Pedido:")
                        st.write(row['Descricao'])
                        st.markdown(f"##### 💡 Justificativa Corporativa:")
                        st.write(row['Justificativa'])
                        st.markdown("---")
                    
                    if f"recusando_{id_chamado}" not in st.session_state:
                        st.session_state[f"recusando_{id_chamado}"] = False
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if not st.session_state[f"recusando_{id_chamado}"]:
                        col_ap, col_rep, _ = st.columns([2, 2, 6])
                        
                        if col_ap.button("👍 Aprovar Compra", key=f"ap_{id_chamado}", use_container_width=True):
                            df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Aprovado"
                            linha_alt = df_dados[df_dados["ID"] == id_chamado].iloc[0]
                            if linha_alt["Voto_Aprovador1"] == "Aprovado" and linha_alt["Voto_Aprovador2"] == "Aprovado" and linha_alt["Voto_Aprovador3"] == "Aprovado":
                                df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Aprovado"
                                
                                html_sucesso = f"""
                                <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                                    <h3 style='color: #008D4C;'>HOSPITAL MOINHOS DE VENTO</h3>
                                    <p style='color: #6c757d;'>✅ Chamado #{id_chamado} foi APROVADO!</p>
                                    <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                                    <p>Todos os 3 aprovadores corporativos deram parecer positivo para: <b>{row['Titulo']}</b>.</p>
                                </div>
                                """
                                enviar_email(destinatario=row["Remetente_Email"], assunto=f"HOSPITAL MOINHOS: Solicitação Aprovada! - #{id_chamado}", corpo_html=html_sucesso)
                            
                            conn.update(data=df_dados)
                            st.rerun()
                            
                        if col_rep.button("👎 Reprovar", key=f"rep_gatilho_{id_chamado}", use_container_width=True):
                            st.session_state[f"recusando_{id_chamado}"] = True
                            st.rerun()
                    else:
                        st.markdown("⚠️ **Explique o motivo da recusa abaixo:**")
                        motivo = st.text_input("Motivo da Reprovação (Obrigatório):", key=f"input_motivo_{id_chamado}", placeholder="Descreva as razões técnicas/orçamentárias...")
                        col_conf, col_canc = st.columns([2, 8])
                        
                        if col_conf.button("Confirmar Rejeição", key=f"conf_rep_{id_chamado}", use_container_width=True):
                            if motivo.strip():
                                df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Reprovado"
                                df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Reprovado"
                                df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = f"{user_name}: {motivo}"
                                
                                html_rejeicao = f"""
                                <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                                    <h3 style='color: #D93025;'>HOSPITAL MOINHOS DE VENTO</h3>
                                    <p style='color: #6c757d;'>❌ Sua solicitação #{id_chamado} foi recusada</p>
                                    <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                                    <p>A solicitação <b>{row['Titulo']}</b> foi reprovada no fluxo corporativo.</p>
                                    <p><b>Motivo:</b> {motivo}</p>
                                </div>
                                """
                                enviar_email(destinatario=row["Remetente_Email"], assunto=f"HOSPITAL MOINHOS: Solicitação Recusada - #{id_chamado}", corpo_html=html_rejeicao)
                                conn.update(data=df_dados)
                                st.session_state[f"recusando_{id_chamado}"] = False
                                st.rerun()
                            else:
                                st.error("O motivo da recusa é obrigatório.")
                                
                        if col_canc.button("Cancelar", key=f"canc_rep_{id_chamado}", use_container_width=True):
                            st.session_state[f"recusando_{id_chamado}"] = False
                            st.rerun()

        # Seção 2: Histórico Próprio do Aprovador (Ponto 5)
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 📊 Histórico de Decisões da Governança")
        if historico_aprovador.empty:
            st.info("Você ainda não registrou votos em chamados anteriores neste portal.")
        else:
            for _, row in historico_aprovador.iterrows():
                id_c = int(row['ID'])
                voto_proprio = row[coluna_voto]
                status_f = row['Status_Final']
                
                cor_voto = "#008D4C" if voto_proprio == "Aprovado" else "#D93025"
                
                with st.expander(f"📋 Chamado #{id_c} - {row['Titulo']} (Seu Voto: {voto_proprio} | Status Final: {status_f})"):
                    st.markdown(f"Seu Parecer: <span style='color:{cor_voto}; font-weight:bold;'>{voto_proprio}</span>", unsafe_allow_html=True)
                    st.write(f"**Solicitante:** {row['Remetente_Nome']} ({row['Remetente_Email']})")
                    st.write(f"**Descrição:** {row['Descricao']}")
                    if row['Motivo_Recusa']:
                        st.info(f"**Histórico de Justificativas/Recusas:** {row['Motivo_Recusa']}")
    else:
        st.info("Nenhuma estrutura de dados mapeada.")

else:
    # Interface Tradicional para o Colaborador solicitante
    st.markdown("---")
    tab_novo, tab_status = st.tabs(["📝 Nova Solicitação de Compra", "📊 Status e Histórico dos meus Pedidos"])
    
    with tab_novo:
        st.markdown("### Formulário de Requisição Padrão")
        st.markdown("Preencha as informações abaixo para iniciar o processo de governança.")
        
        with st.form("form_requisicao", clear_on_submit=True):
            st.markdown("<h4 style='color: #005691;'>Identificação da Demanda</h4>", unsafe_allow_html=True)
            titulo = st.text_input("Título do Projeto/Solicitação de Compra:", placeholder="Ex: Aquisição de novos desfibriladores - UTI Leste")
            
            st.markdown("<br><h4 style='color: #005691;'>Detalhamento</h4>", unsafe_allow_html=True)
            descricao = st.text_area("Descrição detalhada da demanda (Itens, Quantidades, Especificações):", height=150, placeholder="Digite aqui o memorial descritivo completo...")
            justificativa = st.text_area("Justificativa / Impacto para o Hospital (ROI, Segurança, Necessidade):", height=100, placeholder="Porque esta compra é essencial?")
            
            st.markdown("---")
            enviar = st.form_submit_button("🚀 Enviar Solicitação para Governanças", use_container_width=True)
            
            if enviar:
                if titulo and descricao:
                    proximo_id = int(df_dados["ID"].max() + 1) if not df_dados.empty and "ID" in df_dados.columns else 1
                    nova_linha = pd.DataFrame([{
                        "ID": proximo_id,
                        "Remetente_Nome": user_name,
                        "Remetente_Email": user_email,
                        "Titulo": titulo,
                        "Descricao": descricao,
                        "Justificativa": justificativa,
                        "Voto_Aprovador1": "Pendente",
                        "Voto_Aprovador2": "Pendente",
                        "Voto_Aprovador3": "Pendente",
                        "Status_Final": "Em análise",
                        "Motivo_Recusa": ""
                    }])
                    df_atualizado = pd.concat([df_dados, nova_linha], ignore_index=True)
                    conn.update(data=df_atualizado)
                    
                    html_aprovadores = f"""
                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                        <h3 style='color: #005691;'>HOSPITAL MOINHOS DE VENTO</h3>
                        <p style='color: #6c757d;'>Nova Solicitação aguardando Aprovação</p>
                        <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                        <p><b>ID do Chamado:</b> #{proximo_id}</p>
                        <p><b>Remetente:</b> {user_name}</p>
                        <p><b>Título:</b> {titulo}</p>
                    </div>
                    """
                    with st.spinner("Enviando notificações para a governança..."):
                        erros = 0
                        for ap in APROVADORES:
                            sucesso = enviar_email(destinatario=ap, assunto=f"HOSPITAL MOINHOS: Nova Aprovação Pendente - #{titulo}", corpo_html=html_aprovadores)
                            if not sucesso: erros += 1
                        if erros == 0: st.success("Solicitação enviada com sucesso!")
                        else: st.warning("Gravado, mas houve atraso na notificação por e-mail.")
                    st.rerun()
                else:
                    st.error("Por favor, preencha o Título e a Descrição.")

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
                    elif status_atual == "Reprovado": cor_status = "#D93025"
                    elif status_atual == "Em análise": cor_status = "#005691"
                    
                    with st.expander(f"📋 Chamado #{id_c} - {row['Titulo']} [{status_atual}]"):
                        st.markdown(f"Status Final: <span style='color: {cor_status}; font-weight: bold;'>{status_atual}</span>", unsafe_allow_html=True)
                        st.write(f"**Descrição:** {row['Descricao']}")
                        
                        if status_atual == "Reprovado" and str(row.get("Motivo_Recusa", "")).strip() != "":
                            st.markdown(f"<div style='background-color: #F8D7DA; padding: 10px; border-radius: 8px; border: 1px solid #F5C6CB; color: #721C24;'>🚨 **Motivo da Reprovação:** {row['Motivo_Recusa']}</div>", unsafe_allow_html=True)
                        
                        st.markdown("---")
                        st.markdown("<b>Linha do tempo dos avaliadores:</b>", unsafe_allow_html=True)
                        
                        v1, v2, v3 = st.columns(3)
                        for idx, ap_col in enumerate([v1, v2, v3]):
                            ap_email = APROVADORES[idx]
                            voto = row[f"Voto_Aprovador{idx+1}"]
                            with ap_col:
                                if voto == "Pendente": st.caption(f"⏳ **Em análise**\n`{ap_email}`")
                                elif voto == "Aprovado": st.success(f"✅ **Aprovado**\n`{ap_email}`")
                                else: st.error(f"❌ **Reprovado**\n`{ap_email}`")
        else:
            st.info("Nenhuma solicitação encontrada.")
