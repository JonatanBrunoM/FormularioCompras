import streamlit as st
import requests
import pandas as pd
from google_auth_oauthlib.flow import Flow
from streamlit_gsheets import GSheetsConnection

# 1. Configuração Básica da Página
st.set_page_config(page_title="Sistema de Fluxo de Aprovação", layout="wide")

# --- LISTA DE EMAIL DOS 3 APROVADORES OFICIAIS ---
APROVADORES = ["jonatan231196@gmail.com", "aprovador2@email.com", "aprovador3@email.com"]

# --- CONEXÃO NATIVA COM O GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Lê a planilha atualizada
        df = conn.read(ttl=0)
        df = df.dropna(how="all") # Remove linhas totalmente vazias
        
        if not df.empty:
            # CORREÇÃO AQUI: Força a coluna a ser tratada como Texto (String)
            if "Motivo_Recusa" in df.columns:
                df["Motivo_Recusa"] = df["Motivo_Recusa"].astype(str).replace("nan", "")
            
            # Garante que o ID seja sempre número inteiro para não dar erro na busca
            if "ID" in df.columns:
                df["ID"] = df["ID"].astype(int)
                
        return df
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

df_dados = carregar_dados()
user_email = st.session_state.email
user_name = st.session_state.name

st.sidebar.markdown(f"**Usuário:** {user_name}\n`{user_email}`")
if st.sidebar.button("🚪 Sair"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

is_aprovador = user_email in APROVADORES

if is_aprovador:
    st.info("⚡ Você está logado como um dos **Aprovadores Oficiais**.")
    tab_painel, tab_novo = st.tabs(["📥 Painel de Aprovações", "📝 Enviar Nova Solicitação"])
else:
    tab_novo, tab_status = st.tabs(["📝 Nova Solicitação", "📊 Status dos meus Pedidos"])
    tab_painel = None

# --- ABA: CRIAR FORMULÁRIO ---
with tab_novo:
    st.subheader("Formulário de Requisição Padrão")
    with st.form("form_requisicao", clear_on_submit=True):
        titulo = st.text_input("Título do Projeto/Solicitação:")
        descricao = st.text_area("Descrição detalhada da demanda:")
        justificativa = st.text_area("Justificativa / Impacto:")
        
        enviar = st.form_submit_button("🚀 Enviar para Aprovação", use_container_width=True)
        
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
                    "Motivo_Recusa": ""  # Começa vazio
                }])
                
                df_atualizado = pd.concat([df_dados, nova_linha], ignore_index=True)
                conn.update(data=df_atualizado)
                st.success("Solicitação enviada e gravada no Google Sheets com sucesso!")
                st.rerun()
            else:
                st.error("Por favor, preencha o Título e a Descrição.")

# --- ABA: VISÃO DO REMETENTE (Acompanhar Status e Comentários) ---
if not is_aprovador:
    with tab_status:
        st.subheader("Suas solicitações e andamento")
        if not df_dados.empty and "Remetente_Email" in df_dados.columns:
            meus_pedidos = df_dados[df_dados["Remetente_Email"] == user_email]
            
            if meus_pedidos.empty:
                st.write("Você ainda não enviou nenhuma solicitud.");
            else:
                for _, row in meus_pedidos.iterrows():
                    status_atual = row['Status_Final']
                    id_c = int(row['ID'])
                    
                    with st.expander(f"📋 Chamado #{id_c} - {row['Titulo']} [{status_atual}]"):
                        st.write(f"**Descrição:** {row['Descricao']}")
                        st.write(f"**Justificativa:** {row['Justificativa']}")
                        
                        # Se houver motivo de recusa, exibe em destaque
                        if status_atual == "Reprovado" and str(row.get("Motivo_Recusa", "")).strip() != "" and str(row.get("Motivo_Recusa", "")) != "nan":
                            st.error(f"🚨 **Motivo da Reprovação:** {row['Motivo_Recusa']}")
                            
                        st.markdown("---")
                        st.write("**Status detalhado dos avaliadores:**")
                        
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

# --- ABA: VISÃO DO APROVADOR ---
if is_aprovador and tab_painel:
    with tab_painel:
        st.subheader("Solicitações aguardando seu parecer")
        
        num_aprovador = APROVADORES.index(user_email) + 1
        coluna_voto = f"Voto_Aprovador{num_aprovador}"
        
        # Só mostra pedidos cuja avaliação geral ainda esteja "Em análise" e o voto dele esteja "Pendente"
        if not df_dados.empty and coluna_voto in df_dados.columns:
            pendentes = df_dados[(df_dados[coluna_voto] == "Pendente") & (df_dados["Status_Final"] == "Em análise")]
            
            if pendentes.empty:
                st.success("🎈 Tudo em dia! Nenhuma solicitação pendente para você.")
            else:
                for _, row in pendentes.iterrows():
                    id_chamado = row["ID"]
                    with st.container(border=True):
                        st.markdown(f"### {row['Titulo']} (Por: {row['Remetente_Nome']})")
                        st.write(f"**Descrição:** {row['Descricao']}")
                        st.write(f"**Justificativa:** {row['Justificativa']}")
                        
                        # Cria um estado na sessão para controlar se o botão de reprovar foi clicado
                        if f"recusando_{id_chamado}" not in st.session_state:
                            st.session_state[f"recusando_{id_chamado}"] = False
                        
                        if not st.session_state[f"recusando_{id_chamado}"]:
                            col_ap, col_rep, _ = st.columns([1, 1, 4])
                            
                            # AÇÃO: APROVAR
                            if col_ap.button("👍 Aprovar", key=f"ap_{id_chamado}"):
                                # Registra o voto positivo provisoriamente no DataFrame local
                                df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Aprovado"
                                
                                # LÓGICA DE UNANIMIDADE: Pega a linha atualizada para checar os outros votos
                                linha_alt = df_dados[df_dados["ID"] == id_chamado].iloc[0]
                                v1 = linha_alt["Voto_Aprovador1"]
                                v2 = linha_alt["Voto_Aprovador2"]
                                v3 = linha_alt["Voto_Aprovador3"]
                                
                                # Se todos os 3 derem "Aprovado", finaliza o chamado como Aprovado
                                if v1 == "Aprovado" and v2 == "Aprovado" and v3 == "Aprovado":
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Aprovado"
                                
                                conn.update(data=df_dados)
                                st.toast("Você APROVOU esta solicitação.")
                                st.rerun()
                                
                            # Gatilho para abrir o formulário de recusa
                            if col_rep.button("👎 Reprovar", key=f"rep_gatilho_{id_chamado}"):
                                st.session_state[f"recusando_{id_chamado}"] = True
                                st.rerun()
                        
                        # Se o aprovador clicou em Reprovar, exibe a caixa de texto obrigatória
                        else:
                            st.markdown("⚠️ **Explique o motivo da recusa abaixo:**")
                            motivo = st.text_input("Motivo (Obrigatório):", key=f"input_motivo_{id_chamado}")
                            
                            col_conf, col_canc = st.columns([2, 8])
                            
                            if col_conf.button("Confirmar Reprovação", key=f"conf_rep_{id_chamado}"):
                                if motivo.strip():
                                    # LÓGICA DE UNANIMIDADE: Se 1 reprova, o status final vira "Reprovado" imediatamente
                                    df_dados.loc[df_dados["ID"] == id_chamado, coluna_voto] = "Reprovado"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Status_Final"] = "Reprovado"
                                    df_dados.loc[df_dados["ID"] == id_chamado, "Motivo_Recusa"] = f"{user_name}: {motivo}"
                                    
                                    conn.update(data=df_dados)
                                    st.session_state[f"recusando_{id_chamado}"] = False
                                    st.toast("Solicitação reprovada com sucesso.")
                                    st.rerun()
                                else:
                                    st.error("Você precisa digitar um motivo para rejeitar.")
                                    
                            if col_canc.button("Cancelar", key=f"canc_rep_{id_chamado}"):
                                st.session_state[f"recusando_{id_chamado}"] = False
                                st.rerun()
        else:
            st.write("Sem conexões pendentes configuradas.")
