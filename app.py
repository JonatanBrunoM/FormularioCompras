import streamlit as st
import requests
import pandas as pd
from google_auth_oauthlib.flow import Flow
from streamlit_gsheets import GSheetsConnection

# 1. Configuração Básica da Página
st.set_page_config(page_title="Sistema de Fluxo de Aprovação", layout="wide")

# --- LISTA DE EMAIL DOS 3 APROVADORES OFICIAIS ---
# ATENÇÃO: Substitua pelos e-mails reais de quem vai aprovar
APROVADORES = ["jonatan231196@gmail.com", "aprovador2@email.com", "aprovador3@email.com"]

# --- CONEXÃO NATIVA COM O GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Função para ler os dados da planilha atualizados
def carregar_dados():
    try:
        # Lê a planilha, tratando a primeira linha como cabeçalho
        df = conn.read(ttl=0) # ttl=0 garante que não haverá cache, trazendo dados em tempo real
        return df.dropna(how="all") # Remove linhas totalmente vazias se houverem
    except Exception as e:
        st.error(f"Erro ao conectar com a planilha: {e}")
        return pd.DataFrame()

# --- INICIALIZAÇÃO DE LOGIN ---
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

# Carrega a base de dados vinda da planilha do Google
df_dados = carregar_dados()

user_email = st.session_state.email
user_name = st.session_state.name

st.sidebar.markdown(f"**Usuário:** {user_name}\n`{user_email}`")
if st.sidebar.button("🚪 Sair"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- DIVISÃO DE PAPÉIS (REMETENTE VS APROVADOR) ---
is_aprovador = user_email in APROVADORES

if is_aprovador:
    st.info("⚡ Você está logado como um dos **Aprovadores Oficiais**.")
    tab_painel, tab_novo = st.tabs(["📥 Painel de Aprovações", "📝 Enviar Nova Solicitação"])
else:
    tab_novo, tab_status = st.tabs(["📝 Nova Solicitação", "📊 Status dos meus Pedidos"])
    tab_painel = None

# --- ABA: CRIAR FORMULÁRIO (Salva direto na Planilha) ---
with tab_novo:
    st.subheader("Formulário de Requisição Padrão")
    with st.form("form_requisicao", clear_on_submit=True):
        titulo = st.text_input("Título do Projeto/Solicitação:")
        descricao = st.text_area("Descrição detalhada da demanda:")
        justificativa = st.text_area("Justificativa / Impacto:")
        
        enviar = st.form_submit_button("🚀 Enviar para Aprovação", use_container_width=True)
        
        if enviar:
            if titulo and descricao:
                # Calcula o próximo ID sequencial baseado nas linhas existentes
                proximo_id = int(df_dados["ID"].max() + 1) if not df_dados.empty and "ID" in df_dados.columns else 1
                
                # Monta a nova linha para anexar no DataFrame
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
                    "Status_Final": "Em análise"
                }])
                
                # Junta o dado novo com a tabela existente e atualiza a planilha inteira
                df_atualizado = pd.concat([df_dados, nova_linha], ignore_index=True)
                conn.update(data=df_atualizado)
                st.success("Solicitação enviada e gravada no Google Sheets com sucesso!")
                st.rerun()
            else:
                st.error("Por favor, preencha o Título e a Descrição.")

# --- ABA: VISÃO DO REMETENTE (Lê o status da Planilha) ---
if not is_aprovador:
    with tab_status:
        st.subheader("Suas solicitações e andamento")
        if not df_dados.empty and "Remetente_Email" in df_dados.columns:
            meus_pedidos = df_dados[df_dados["Remetente_Email"] == user_email]
            
            if meus_pedidos.empty:
                st.write("Você ainda não enviou nenhuma solicitação.")
            else:
                for _, row in meus_pedidos.iterrows():
                    with st.expander(f"📋 Chamado #{int(row['ID'])} - {row['Titulo']} [{row['Status_Final']}]"):
                        st.write(f"**Descrição:** {row['Descricao']}")
                        st.write(f"**Justificativa:** {row['Justificativa']}")
                        st.markdown("---")
                        st.write("**Status da Avaliação pelos Gestores:**")
                        
                        # Mostra o status de cada um dos 3 aprovadores baseado nas colunas da planilha
                        for idx, ap_email in enumerate(APROVADORES):
                            voto = row[f"Voto_Aprovador{idx+1}"]
                            if voto == "Pendente":
                                st.caption(f"⏳ {ap_email}: **Em análise**")
                            elif voto == "Aprovado":
                                st.success(f"✅ {ap_email}: **Aprovado**")
                            else:
                                st.error(f"❌ {ap_email}: **Reprovado**")
        else:
            st.write("Nenhuma solicitação encontrada no banco de dados.")

# --- ABA: VISÃO DO APROVADOR (Atualiza a Planilha com o Voto) ---
if is_aprovador and tab_painel:
    with tab_painel:
        st.subheader("Solicitações aguardando seu parecer")
        
        # Descobre qual coluna pertence ao aprovador logado (1, 2 ou 3)
        num_aprovador = APROVADORES.index(user_email) + 1
        coluna_voto = f"Voto_Aprovador{num_aprovador}"
        
        if not df_dados.empty and coluna_voto in df_dados.columns:
            # Filtra apenas linhas onde o voto deste aprovador específico está "Pendente"
            pendentes = df_dados[df_dados[coluna_voto] == "Pendente"]
            
            if pendentes.empty:
                st.success("🎈 Tudo em dia! Nenhuma solicitação pendente para você.")
            else:
                for _, row in pendentes.iterrows():
                    id_chamado = row["ID"]
                    with st.container(border=True):
                        st.markdown(f"### {row['Titulo']} (Por: {row['Remetente_Nome']})")
                        st.write(f"**Descrição:** {row['Descricao']}")
                        st.write(f"**Justificativa:** {row['Justificativa']}")
                        
                        col_ap, col_rep, _ = st.columns([1, 1, 4])
                        
                        # Se clicar em aprovar ou reprovar, localiza a linha exata no dataframe pelo ID e altera a célula
                        if col_ap.button("👍 Aprovar", key=f"ap_{id_chamado}"):
                            df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Aprovado"
                            conn.update(data=df_dados)
                            st.toast("Você APROVOU esta solicitação.")
                            st.rerun()
                            
                        if col_rep.button("👎 Reprovar", key=f"rep_{id_chamado}"):
                            df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Reprovado"
                            conn.update(data=df_dados)
                            st.toast("Você REPROVOU esta solicitação.")
                            st.rerun()
        else:
            st.write("Sem conexões pendentes configuradas.")
