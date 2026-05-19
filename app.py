import streamlit as st
import requests
from google_auth_oauthlib.flow import Flow

# 1. Configuração Básica da Página
st.set_page_config(page_title="Sistema de Fluxo de Aprovação", layout="wide")

# --- LISTA DE EMAIL DOS 3 APROVADORES OFICIAIS ---
# Mude para os e-mails reais depois
APROVADORES = ["aprovador1@email.com", "aprovador2@email.com", "aprovador3@email.com"]

# --- INICIALIZAÇÃO DO BANCO DE DADOS TEMPORÁRIO ---
if "solicitacoes" not in st.session_state:
    st.session_state.solicitacoes = [] # Guardará os formulários enviados

if "connected" not in st.session_state:
    st.session_state.connected = False

# --- CONTROLE DE LOGIN (Reaproveitado do seu projeto) ---
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
    except Exception as e:
        st.error(f"Erro ao processar login: {e}")
        st.query_params.clear()

# --- INTERFACE PRINCIPAL ---
st.title("🔗 Workflow de Aprovação Automatizado")

if not st.session_state.connected:
    st.warning("🔒 Por favor, faça login com sua conta Google para acessar o sistema.")
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"response_type=code&client_id={st.secrets.get('GOOGLE_CLIENT_ID','')}&"
        f"redirect_uri={st.secrets.get('GOOGLE_REDIRECT_URI','')}&"
        f"scope=https://www.googleapis.com/auth/userinfo.profile%20https://www.googleapis.com/auth/userinfo.email%20openid&prompt=select_account"
    )
    st.link_button("🔑 Efetuar Login com Google", auth_url, type="primary")
    st.stop()

# Dados do usuário logado
user_email = st.session_state.email
user_name = st.session_state.name

st.sidebar.markdown(f"**Usuário:** {user_name}\n`{user_email}`")
if st.sidebar.button("🚪 Sair"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- DIVISÃO DE PAPÉIS (VISÃO REMETENTE VS VISÃO APROVADOR) ---
is_aprovador = user_email in APROVADORES

if is_aprovador:
    st.info("⚡ Você está logado como um dos **Aprovadores Oficiais**.")
    tab_painel, tab_novo = st.tabs(["📥 Painel de Aprovações", "📝 Enviar Nova Solicitação"])
else:
    tab_novo, tab_status = st.tabs(["📝 Nova Solicitação", "📊 Status dos meus Pedidos"])
    tab_painel = None

# --- ABA: CRIAR FORMULÁRIO (Disponível para todos) ---
with tab_novo:
    st.subheader("Formulário de Requisição Padrão")
    with st.form("form_requisicao", clear_on_submit=True):
        titulo = st.text_input("Título do Projeto/Solicitação:")
        descricao = st.text_area("Descrição detalhada da demanda:")
        justificativa = st.text_area("Justificativa / Impacto:")
        
        enviar = st.form_submit_button("🚀 Enviar para Aprovação")
        
        if enviar:
            if titulo and descricao:
                # Cria a estrutura do pedido
                nova_solicitacao = {
                    "id": len(st.session_state.solicitacoes) + 1,
                    "remetente_nome": user_name,
                    "remetente_email": user_email,
                    "titulo": titulo,
                    "descricao": descricao,
                    "justificativa": justificativa,
                    # Dicionário controlando o voto de cada um dos 3 aprovadores
                    "votos": {aprovador: "Pendente" for aprovador in APROVADORES}
                }
                st.session_state.solicitacoes.append(nova_solicitacao)
                st.success("Solicitação enviada com sucesso para os 3 aprovadores!")
            else:
                st.error("Por favor, preencha o Título e a Descrição.")

# --- ABA: VISÃO DO REMETENTE (Acompanhar Status) ---
if not is_aprovador:
    with tab_status:
        st.subheader("Suas solicitações e andamento")
        meus_pedidos = [p for p in st.session_state.solicitacoes if p["remetente_email"] == user_email]
        
        if not meus_pedidos:
            st.write("Você ainda não enviou nenhuma solicitação.")
        for p in meus_pedidos:
            with st.expander(f"📋 Chamado #{p['id']} - {p['titulo']}"):
                st.write(f"**Descrição:** {p['descricao']}")
                st.write(f"**Justificativa:** {p['justificativa']}")
                st.markdown("---")
                st.write("**Status da Avaliação pelos 3 Gestores:**")
                
                # Exibe o voto de cada um dos e-mails
                for ap, status_voto in p["votos"].items():
                    if status_voto == "Pendente":
                        st.caption(f"⏳ {ap}: **Em análise**")
                    elif status_voto == "Aprovado":
                        st.success(f"✅ {ap}: **Aprovado**")
                    else:
                        st.error(f"❌ {ap}: **Reprovado**")

# --- ABA: VISÃO DO APROVADOR (Painel de Decisão) ---
if is_aprovador and tab_painel:
    with tab_painel:
        st.subheader("Solicitações aguardando seu parecer")
        
        # Filtra chamados onde este aprovador específico ainda está com status "Pendente"
        pendentes = [p for p in st.session_state.solicitacoes if p["votos"][user_email] == "Pendente"]
        
        if not pendentes:
            st.success("🎈 Tudo em dia! Nenhuma solicitação pendente para você.")
            
        for p in pendentes:
            with st.container(border=True):
                st.markdown(f"### {p['titulo']} (Por: {p['remetente_nome']})")
                st.write(f"**Descrição:** {p['descricao']}")
                st.write(f"**Justificativa:** {p['justificativa']}")
                
                col_ap, col_rep, _ = st.columns([1, 1, 4])
                
                # Ações de aprovação usando chaves dinâmicas baseadas no id do chamado
                if col_ap.button("👍 Aprovar", key=f"ap_{p['id']}"):
                    p["votos"][user_email] = "Aprovado"
                    st.toast("Você APROVOU esta solicitação.")
                    st.rerun()
                    
                if col_rep.button("👎 Reprovar", key=f"rep_{p['id']}"):
                    p["votos"][user_email] = "Reprovado"
                    st.toast("Você REPROVOU esta solicitação.")
                    st.rerun()
