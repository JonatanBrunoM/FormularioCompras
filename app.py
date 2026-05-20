import streamlit as st
import requests
import pandas as pd
import smtplib
import os # Necessário para ler o caminho da imagem
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google_auth_oauthlib.flow import Flow
from streamlit_gsheets import GSheetsConnection

# ==============================================================================
# 1. Configuração Básica da Página e Design
# ==============================================================================
# Definindo as cores oficiais e favicon (logomini.png)
st.set_page_config(
    page_title="Workflow de Aprovações - Hospital Moinhos",
    page_icon="logomini.png", # Favicon (Precisa estar na mesma pasta no GitHub)
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS customizada para cores e cantos arredondados
st.markdown("""
<style>
    /* Cores Globais - Tons de azul/verde corporativo */
    :root {
        --cor-principal: #005691; /* Exemplo de azul hospitalar */
        --cor-secundaria: #008D4C; /* Verde aprovação */
    }
    
    /* Títulos principais */
    h1, h2, h3 { color: var(--cor-principal) !important; }
    
    /* Botões */
    div.stButton > button {
        border-radius: 8px !important;
        border: 1px solid #ced4da !important;
    }
    div.stButton > button:first-child:hover {
        background-color: #f8f9fa !important;
        border-color: var(--cor-principal) !important;
    }
    
    /* Cards (border-containers) */
    [data-testid="stForm"], div[data-testid="stContainer"][aria-label="border"] {
        border-radius: 12px !important;
        border: 1px solid #EAEAEA !important;
        padding: 20px !important;
        background-color: #ffffff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    
    /* Tabs customizadas */
    button[data-baseweb="tab"] {
        font-size: 1.1em;
        font-weight: 500;
        color: #495057;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--cor-principal);
    }
    div[data-baseweb="tab-highlight"] {
        background-color: var(--cor-principal);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. Configurações de E-mail e Banco de Dados (Inalterados)
# ==============================================================================
APROVADORES = ["jonatan231196@gmail.com", "jonatan231196@gmail.com", "jonatan231196@gmail.com"]

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

# --- LOGIN (Inalterado) ---
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
        st.query_params.clear()
        st.rerun()
    except Exception:
        st.query_params.clear()

# ==============================================================================
# 3. Sidebar e Logo Principal
# ==============================================================================
# Adiciona a logo no topo da barra lateral (logomoinhos.png)
if os.path.exists("logomoinhos.png"):
    st.sidebar.image("logomoinhos.png", use_container_width=True)
else:
    st.sidebar.title("Hospital Moinhos")
st.sidebar.markdown("---")

if not st.session_state.connected:
    st.markdown("<h1 style='text-align: center;'>🔗 Workflow de Aprovações</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6c757d; font-size: 1.1em;'>Hospital Moinhos de Vento</p>", unsafe_allow_html=True)
    st.warning("🔒 Por favor, faça login com sua conta Google para acessar o sistema.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"response_type=code&client_id={st.secrets.get('GOOGLE_CLIENT_ID','')}&"
        f"redirect_uri={st.secrets.get('GOOGLE_REDIRECT_URI','')}&"
        f"scope=https://www.googleapis.com/auth/userinfo.profile%20https://www.googleapis.com/auth/userinfo.email%20openid&prompt=select_account"
    )
    col2.link_button("🔑 Efetuar Login Institucional", auth_url, type="primary", use_container_width=True)
    st.stop()

# Dados do usuário logado na sidebar
user_email = st.session_state.email
user_name = st.session_state.name
st.sidebar.markdown(f"🧑‍💻 **Usuário:**\n{user_name}\n`{user_email}`")
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==============================================================================
# 4. Interface Principal e Organização Visual
# ==============================================================================
df_dados = carregar_dados()
is_aprovador = user_email in APROVADORES

# Título Principal limpo
st.title("Central de Aprovações de Compras")
st.markdown("<p style='color: #6c757d; font-size: 1.1em; margin-top: -10px;'>Fluxo de governança e consenso para o Hospital Moinhos</p>", unsafe_allow_html=True)
if is_aprovador:
    # Métricas simples no topo para o aprovador (Melhoria visual)
    st.markdown("---")
    num_aprovador_m = APROVADORES.index(user_email) + 1
    coluna_voto_m = f"Voto_Aprovador{num_aprovador_m}"
    if not df_dados.empty and coluna_voto_m in df_dados.columns:
        total_p = len(df_dados[(df_dados[coluna_voto_m] == "Pendente") & (df_dados["Status_Final"] == "Em análise")])
        final_a = len(df_dados[df_dados["Status_Final"] == "Aprovado"])
        final_r = len(df_dados[df_dados["Status_Final"] == "Reprovado"])
        
        m1, m2, m3 = st.columns(3)
        with m1: st.metric("Suas Pendências", total_p, "Urgente", delta_color="inverse")
        with m2: st.metric("Total Aprovados (Mês)", final_a)
        with m3: st.metric("Total Reprovados (Mês)", final_r)
    
    st.markdown("---")
    tab_painel, tab_novo = st.tabs(["📥 Painel de Aprovações Corporativas", "📝 Enviar Nova Solicitação de Compra"])
else:
    tab_novo, tab_status = st.tabs(["📝 Nova Solicitação de Compra", "📊 Status e Histórico dos meus Pedidos"])
    tab_painel = None

# --- ABA: CRIAR FORMULÁRIO (Corrigido para evitar quebras) ---
with tab_novo:
    st.markdown("### Formulário de Requisição Padrão")
    st.markdown("Preencha as informações abaixo para iniciar o processo de governança.")
    
    with st.form("form_requisicao", clear_on_submit=True):
        st.markdown("<h4 style='color: #6c757d;'>Identificação da Demanda</h4>", unsafe_allow_html=True)
        titulo = st.text_input("Título do Projeto/Solicitação de Compra:", placeholder="Ex: Aquisição de novos desfibriladores - UTI Leste")
        
        st.markdown("<br><h4 style='color: #6c757d;'>Detalhamento</h4>", unsafe_allow_html=True)
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
                
                # --- Envio de E-mail (Melhoria visual no HTML) ---
                html_aprovadores = f"""
                <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                    <h3 style='color: #005691;'>HOSPITAL MOINHOS DE VENTO</h3>
                    <p style='color: #6c757d;'>Nova Solicitação aguardando Aprovação</p>
                    <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                    <p><b>ID do Chamado:</b> #{proximo_id}</p>
                    <p><b>Remetente:</b> {user_name} ({user_email})</p>
                    <p><b>Título:</b> {titulo}</p>
                    <p><b>Descrição:</b> {descricao}</p>
                    <br>
                    <a href='https://formulariocompras.streamlit.app' style='background-color: #005691; color: white; padding: 10px 20px; text-decoration: none; border-radius: 8px; display: inline-block;'>Acessar Sistema de Aprovação</a>
                </div>
                """
                
                with st.spinner("Enviando notificações para a governança..."):
                    erros = 0
                    for ap in APROVADORES:
                        sucesso = enviar_email(destinatario=ap, assunto=f"HOSPITAL MOINHOS: Nova Aprovação Pendente - #{titulo}", corpo_html=html_aprovadores)
                        if not sucesso: erros += 1
                    
                    if erros == 0: st.success("Solicitação enviada e governança notificada com sucesso!")
                    else: st.warning("Solicitação gravada, mas houve falha no envio de e-mails de alerta.")
                st.rerun()
            else:
                st.error("Por favor, preencha o Título e a Descrição.")

# --- ABA: VISÃO DO REMETENTE (Cards visuais) ---
if not is_aprovador:
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
                    
                    # Estilo visual baseado no status
                    cor_status = "#495057"
                    if status_atual == "Aprovado": cor_status = "#008D4C"
                    elif status_atual == "Reprovado": cor_status = "#D93025"
                    elif status_atual == "Em análise": cor_status = "#005691"
                    
                    with st.expander(f"📋 Chamado #{id_c} - {row['Titulo']} [{status_atual}]"):
                        st.markdown(f"Status Final: <span style='color: {cor_status}; font-weight: bold;'>{status_atual}</span>", unsafe_allow_submission=True)
                        st.write(f"**Descrição:** {row['Descricao']}")
                        
                        if status_atual == "Reprovado" and str(row.get("Motivo_Recusa", "")).strip() != "":
                            st.markdown(f"<div style='background-color: #F8D7DA; padding: 10px; border-radius: 8px; border: 1px solid #F5C6CB; color: #721C24;'>🚨 **Motivo da Reprovação:** {row['Motivo_Recusa']}</div>", unsafe_allow_submission=True)
                        
                        st.markdown("---")
                        st.markdown("<b>Linha do tempo dos avaliadores:</b>", unsafe_allow_submission=True)
                        
                        # Colunas para os 3 votos (Visual incremental)
                        v1, v2, v3 = st.columns(3)
                        for idx, ap_col in enumerate([v1, v2, v3]):
                            ap_email = APROVADORES[idx]
                            voto = row[f"Voto_Aprovador{idx+1}"]
                            with ap_col:
                                if voto == "Pendente":
                                    st.caption(f"⏳ **Em análise**\n`{ap_email}`")
                                elif voto == "Aprovado":
                                    st.success(f"✅ **Aprovado**\n`{ap_email}`")
                                else:
                                    st.error(f"❌ **Reprovado**\n`{ap_email}`")
        else:
            st.info("Nenhuma solicitação encontrada.")

# --- ABA: VISÃO DO APROVADOR (Design limpo) ---
if is_aprovador and tab_painel:
    with tab_painel:
        st.markdown("### Solicitações Pendentes de seu Parecer")
        
        num_aprovador = APROVADORES.index(user_email) + 1
        coluna_voto = f"Voto_Aprovador{num_aprovador}"
        
        if not df_dados.empty and coluna_voto in df_dados.columns:
            pendentes = df_dados[(df_dados[coluna_voto] == "Pendente") & (df_dados["Status_Final"] == "Em análise")]
            
            if pendentes.empty:
                st.success("🎈 Excelente! Nenhuma solicitação corporativa pendente para você.")
            else:
                for _, row in pendentes.iterrows():
                    id_chamado = row["ID"]
                    
                    with st.container(border=True):
                        st.markdown(f"#### #{id_chamado} - {row['Titulo']} (Remetente: {row['Remetente_Nome']})")
                        st.write(f"**Descrição:** {row['Descricao']}")
                        st.write(f"**Justificativa:** {row['Justificativa']}")
                        
                        if f"recusando_{id_chamado}" not in st.session_state:
                            st.session_state[f"recusando_{id_chamado}"] = False
                        
                        st.markdown("---")
                        
                        if not st.session_state[f"recusando_{id_chamado}"]:
                            col_ap, col_rep, _ = st.columns([2, 2, 6])
                            
                            # Botões com ícones e cores
                            if col_ap.button("👍 Aprovar Compra", key=f"ap_{id_chamado}", use_container_width=True):
                                # ... (Lógica de aprovação inalterada) ...
                                df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Aprovado"
                                linha_alt = df_dados[df_dados["ID"] == id_chamado].iloc[0]
                                if linha_alt["Voto_Aprovador1"] == "Aprovado" and linha_alt["Voto_Aprovador2"] == "Aprovado" and linha_alt["Voto_Aprovador3"] == "Aprovado":
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Aprovado"
                                    
                                    # E-mail de Sucesso (Melhoria visual)
                                    html_sucesso = f"""
                                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                                        <h3 style='color: #008D4C;'>HOSPITAL MOINHOS DE VENTO</h3>
                                        <p style='color: #6c757d;'>✅ Chamado #{id_chamado} foi APROVADO!</p>
                                        <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                                        <p>Todos os 3 aprovadores corporativos deram parecer positivo para a sua solicitação: <b>{row['Titulo']}</b>.</p>
                                        <br>
                                        <a href='https://formulariocompras.streamlit.app' style='background-color: #008D4C; color: white; padding: 10px 20px; text-decoration: none; border-radius: 8px; display: inline-block;'>Acompanhar Pedido</a>
                                    </div>
                                    """
                                    enviar_email(destinatario=row["Remetente_Email"], assunto=f"HOSPITAL MOINHOS: Solicitação Aprovada por Unanimidade! - #{id_chamado}", corpo_html=html_sucesso)
                                
                                conn.update(data=df_dados)
                                st.rerun()
                                
                            if col_rep.button("👎 Reprovar", key=f"rep_gatilho_{id_chamado}", use_container_width=True):
                                st.session_state[f"recusando_{id_chamado}"] = True
                                st.rerun()
                        
                        else:
                            st.markdown("⚠️ **Explique o motivo da recusa abaixo:**")
                            motivo = st.text_input("Motivo da Reprovação (Obrigatório):", key=f"input_motivo_{id_chamado}", placeholder="Descreva os pontos de atenção...")
                            col_conf, col_canc = st.columns([2, 8])
                            
                            if col_conf.button("Confirmar", key=f"conf_rep_{id_chamado}", use_container_width=True):
                                if motivo.strip():
                                    df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Reprovado"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Reprovado"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = f"{user_name}: {motivo}"
                                    
                                    # E-mail de Rejeição (Melhoria visual)
                                    html_rejeicao = f"""
                                    <div style='font-family: sans-serif; max-width: 600px; border: 1px solid #EAEAEA; border-radius: 12px; padding: 20px;'>
                                        <h3 style='color: #D93025;'>HOSPITAL MOINHOS DE VENTO</h3>
                                        <p style='color: #6c757d;'>❌ Sua solicitação #{id_chamado} foi recusada</p>
                                        <hr style='border: 0; border-top: 1px solid #EAEAEA;'>
                                        <p>A solicitação <b>{row['Titulo']}</b> foi reprovada no fluxo corporativo.</p>
                                        <p><b>Motivo apontado por {user_name}:</b> {motivo}</p>
                                        <br>
                                        <a href='https://formulariocompras.streamlit.app' style='background-color: #D93025; color: white; padding: 10px 20px; text-decoration: none; border-radius: 8px; display: inline-block;'>Acessar Sistema</a>
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
        else:
            st.info("Nenhuma conexão de dados encontrada.")
