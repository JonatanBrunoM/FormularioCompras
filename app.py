import streamlit as st
import requests
import pandas as pd
import smtplib
import os
import datetime
import time
import base64
import json
import extra_streamlit_components as stx
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from streamlit_gsheets import GSheetsConnection
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from cryptography.fernet import Fernet, InvalidToken
import io

if "form_count" not in st.session_state:
    st.session_state["form_count"] = 0
    
# ==============================================================================
# 1. Configuração upload de arquivos
# ==============================================================================
def obter_credenciais_google():
    credentials = st.session_state.get(
        "google_credentials"
    )

    if credentials is None:
        return None

    try:
        if credentials.expired:
            if credentials.refresh_token:
                credentials.refresh(Request())

                st.session_state[
                    "google_credentials"
                ] = credentials

            else:
                return None

        if not credentials.valid:
            return None

        return credentials

    except Exception as erro:
        print(
            "Erro ao renovar credenciais Google:",
            erro,
        )

        return None

def upload_para_google_drive(arquivo_streamlit, pasta_id=None):
    """
    Faz o upload de um arquivo do Streamlit para uma pasta específica do Google Drive.
    Usa os tokens de autenticação salvos na sessão do usuário.
    """
    try:
        credentials = obter_credenciais_google()

        if credentials is None:
            st.error(
                "Sua autorização do Google expirou. "
                "Saia do sistema e entre novamente."
            )

            return None

        service = build(
            "drive",
            "v3",
            credentials=credentials,
        )
        
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

    .login-shell {
        width: 100%;
        max-width: 920px;
        margin: 0 auto;
    }

    .login-premium-grid {
    display: grid;
    grid-template-columns: 1.05fr 0.95fr;
    width: 100%;
    }
    
    .login-logo-image {
        display: block;
        width: 135px;
        max-width: 100%;
        height: auto;
        margin: 0 auto;
    }
    
    .login-google-button {
        min-height: 44px;
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        background: #005691;
        color: #ffffff !important;
        border: 1px solid #005691;
        border-radius: 9px;
        font-size: 0.91rem;
        font-weight: 650;
        text-decoration: none !important;
        transition:
            transform 0.18s ease,
            background 0.18s ease;
    }
    
    .login-google-button:hover {
        background: #003d66;
        border-color: #003d66;
        color: #ffffff !important;
        text-decoration: none !important;
        transform: translateY(-1px);
    }
    
    @media (max-width: 800px) {
        .login-premium-grid {
            grid-template-columns: 1fr;
        }
    
        .login-brand-panel {
            display: none;
        }
    }
    
    .login-brand-panel {
        min-height: 430px;
        padding: 42px 40px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        background: linear-gradient(
            145deg,
            #005691 0%,
            #003d66 100%
        );
        border-radius: 20px 0 0 20px;
        box-shadow: 0 18px 50px rgba(0, 61, 102, 0.16);
    }
    
    .login-brand-kicker {
        margin: 0 0 12px;
        color: rgba(255, 255, 255, 0.78);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    
    .login-brand-title {
        margin: 0;
        color: #ffffff !important;
        font-size: 2.35rem;
        font-weight: 700 !important;
        line-height: 1.05;
    }
    
    .login-brand-text {
        max-width: 390px;
        margin: 18px 0 0;
        color: rgba(255, 255, 255, 0.86);
        font-size: 0.98rem;
        line-height: 1.65;
    }
    
    .login-brand-footer {
        color: rgba(255, 255, 255, 0.68);
        font-size: 0.76rem;
    }
    
    .login-access-panel {
        min-height: 430px;
        padding: 34px 38px 30px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        background: #ffffff;
        border: 1px solid #e4e9ed;
        border-left: 0;
        border-radius: 0 20px 20px 0;
        box-shadow: 0 18px 50px rgba(0, 61, 102, 0.10);
    }
    
    .login-logo-wrap {
        height: 72px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 12px;
        overflow: hidden;
    }
    
    .login-access-title {
        margin: 0;
        color: #263238 !important;
        font-size: 1.42rem;
        font-weight: 700 !important;
        text-align: center;
    }
    
    .login-access-subtitle {
        max-width: 330px;
        margin: 8px auto 20px;
        color: #68757d;
        font-size: 0.88rem;
        line-height: 1.5;
        text-align: center;
    }
    
    .login-security-note {
        margin-top: 16px;
        padding: 11px 13px;
        background: #f4f8fb;
        border: 1px solid #ddeaf2;
        border-radius: 9px;
        color: #52616a;
        font-size: 0.77rem;
        line-height: 1.45;
    }
    
    .login-access-panel [data-testid="stLinkButton"] a {
        min-height: 44px;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: #005691 !important;
        color: #ffffff !important;
        border: 1px solid #005691 !important;
        border-radius: 9px !important;
        box-shadow: none !important;
        font-size: 0.91rem !important;
        font-weight: 650 !important;
        text-decoration: none !important;
        transition:
            transform 0.18s ease,
            background 0.18s ease !important;
    }
    
    .login-access-panel [data-testid="stLinkButton"] a:hover {
        background: #003d66 !important;
        border-color: #003d66 !important;
        color: #ffffff !important;
        text-decoration: none !important;
        transform: translateY(-1px);
    }
    
    @media (max-width: 800px) {
        .login-brand-panel {
            display: none;
        }
    
        .login-access-panel {
            min-height: auto;
            padding: 28px 24px;
            border: 1px solid #e4e9ed;
            border-radius: 16px;
        }
    }

    /* ==========================================
        2.1 SIDEBAR E COMPONENTES INTERNOS
       ========================================== */
    section[data-testid="stSidebar"] {
        background: var(--secondary-background-color) !important;
        border-right: 1px solid rgba(128, 128, 128, 0.20);
        color: var(--text-color) !important;
    }
    
    section[data-testid="stSidebar"] > div:first-child {
        height: 100vh;
        overflow-y: auto;
        overflow-x: hidden;
    }
    
    section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {
        padding-top: 0.75rem;
        padding-bottom: 0.75rem;
    }
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar {
        width: 5px;
    }
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar-track {
        background: transparent;
    }
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
        background: rgba(128, 128, 128, 0.28);
        border-radius: 999px;
    }
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {
        background: rgba(128, 128, 128, 0.45);
    }
    
    /* ------------------------------------------
       Cabeçalho institucional
       ------------------------------------------ */
    
    .sidebar-brand-card {
        padding: 14px 14px 12px;
        margin-bottom: 10px;
        border-radius: 13px;
        background:
            linear-gradient(
                135deg,
                #005691 0%,
                #003d66 100%
            );
        box-shadow: 0 6px 18px rgba(0, 61, 102, 0.22);
    }
    
    .sidebar-brand-kicker {
        margin: 0 0 3px;
        color: rgba(255, 255, 255, 0.72);
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.09em;
        text-transform: uppercase;
    }
    
    .sidebar-brand-title {
        margin: 0;
        color: #ffffff !important;
        font-size: 1.22rem;
        font-weight: 750;
        line-height: 1.1;
    }
    
    .sidebar-brand-subtitle {
        margin: 4px 0 0;
        color: rgba(255, 255, 255, 0.82);
        font-size: 0.70rem;
        line-height: 1.3;
    }
    
    /* ------------------------------------------
       Card do usuário
       ------------------------------------------ */
    
    .sidebar-user-card {
        display: flex;
        align-items: center;
        gap: 9px;
        padding: 10px;
        margin-bottom: 5px;
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 11px;
        background: var(--background-color);
        color: var(--text-color);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }
    
    .sidebar-user-avatar {
        width: 39px;
        height: 39px;
        flex: 0 0 39px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid var(--primary-color);
        box-shadow: 0 2px 6px rgba(0, 86, 145, 0.20);
    }
    
    .sidebar-user-info {
        min-width: 0;
        display: flex;
        flex-direction: column;
    }
    
    .sidebar-user-name {
        color: var(--text-color);
        font-size: 0.82rem;
        font-weight: 700;
        line-height: 1.25;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .sidebar-user-email {
        margin-top: 1px;
        color: var(--text-color);
        opacity: 0.65;
        font-size: 0.66rem;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    /* ------------------------------------------
       Identificação do perfil
       ------------------------------------------ */
    
    .sidebar-role-badge {
        display: inline-flex;
        align-items: center;
        width: fit-content;
        margin: 0 0 10px 2px;
        padding: 4px 8px;
        border: 1px solid rgba(0, 86, 145, 0.25);
        border-radius: 999px;
        background: rgba(0, 86, 145, 0.10);
        color: var(--primary-color);
        font-size: 0.61rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    
    /* ------------------------------------------
       Títulos das seções
       ------------------------------------------ */
    
    .sidebar-section-label {
        display: flex;
        align-items: center;
        gap: 6px;
        margin: 11px 2px 5px;
        color: var(--text-color);
        opacity: 0.62;
        font-size: 0.61rem;
        font-weight: 750;
        letter-spacing: 0.075em;
        text-transform: uppercase;
    }
    
    .sidebar-section-label::after {
        content: "";
        height: 1px;
        flex: 1;
        background: var(--text-color);
        opacity: 0.13;
    }
    
    /* ------------------------------------------
       Botões de navegação
       ------------------------------------------ */
    
    section[data-testid="stSidebar"]
    div[data-testid="stButton"] {
        margin-bottom: 2px;
    }
    
    section[data-testid="stSidebar"]
    div[data-testid="stButton"] > button {
        min-height: 37px;
        justify-content: flex-start;
        padding: 0.35rem 0.75rem;
        border: 1px solid transparent;
        border-radius: 9px;
        background: transparent;
        color: var(--text-color);
        font-size: 0.78rem;
        font-weight: 600;
        box-shadow: none;
        transition:
            background-color 0.18s ease,
            border-color 0.18s ease,
            color 0.18s ease,
            transform 0.18s ease;
    }
    
    section[data-testid="stSidebar"]
    div[data-testid="stButton"] > button:hover {
        border-color: rgba(0, 86, 145, 0.30);
        background: rgba(0, 86, 145, 0.10);
        color: var(--primary-color);
        transform: translateX(2px);
    }
    
    /* ------------------------------------------
       Links externos
       ------------------------------------------ */
    
    section[data-testid="stSidebar"]
    div[data-testid="stLinkButton"] {
        margin-bottom: 3px;
    }
    
    section[data-testid="stSidebar"]
    div[data-testid="stLinkButton"] a {
        min-height: 37px;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        padding: 0.35rem 0.75rem !important;
        border: 1px solid rgba(128, 128, 128, 0.22) !important;
        border-radius: 9px !important;
        background: var(--background-color) !important;
        color: var(--text-color) !important;
        font-size: 0.76rem !important;
        font-weight: 600 !important;
        text-decoration: none !important;
        box-shadow: none !important;
        transition:
            background-color 0.18s ease,
            border-color 0.18s ease,
            color 0.18s ease,
            transform 0.18s ease !important;
    }
    
    section[data-testid="stSidebar"]
    div[data-testid="stLinkButton"] a:hover {
        border-color: var(--primary-color) !important;
        background: rgba(0, 86, 145, 0.10) !important;
        color: var(--primary-color) !important;
        transform: translateX(2px);
    }
    
    /* ------------------------------------------
       Rodapé e saída
       ------------------------------------------ */
    
    .sidebar-divider {
        height: 1px;
        margin: 11px 0 8px;
        background: var(--text-color);
        opacity: 0.13;
    }
    
    .sidebar-footer {
        margin-top: 6px;
        padding: 5px 4px 0;
        color: var(--text-color);
        opacity: 0.52;
        font-size: 0.57rem;
        line-height: 1.35;
        text-align: center;
    }
    
    section[data-testid="stSidebar"]
    div.st-key-botao_sair_sidebar {
        margin-top: 2px;
    }
    
    section[data-testid="stSidebar"]
    div.st-key-botao_sair_sidebar button {
        min-height: 36px;
        justify-content: center;
        border: 1px solid rgba(200, 69, 80, 0.40);
        background: rgba(200, 69, 80, 0.08);
        color: #d65a63;
    }
    
    section[data-testid="stSidebar"]
    div.st-key-botao_sair_sidebar button:hover {
        border-color: #c84550;
        background: #c84550;
        color: #ffffff;
        transform: none;
    }
    
    /* ==========================================
       AJUSTES PARA TELAS MAIS BAIXAS
       ========================================== */
    
    @media (max-height: 850px) {
    
        .sidebar-brand-card {
            padding: 11px 12px 10px;
            margin-bottom: 7px;
        }
    
        .sidebar-brand-title {
            font-size: 1.10rem;
        }
    
        .sidebar-brand-subtitle {
            font-size: 0.64rem;
        }
    
        .sidebar-user-card {
            padding: 8px;
        }
    
        .sidebar-user-avatar {
            width: 35px;
            height: 35px;
            flex-basis: 35px;
        }
    
        .sidebar-role-badge {
            margin-bottom: 7px;
            padding: 3px 7px;
        }
    
        .sidebar-section-label {
            margin-top: 8px;
            margin-bottom: 4px;
        }
    
        section[data-testid="stSidebar"]
        div[data-testid="stButton"] > button,
        section[data-testid="stSidebar"]
        div[data-testid="stLinkButton"] a {
            min-height: 34px;
            font-size: 0.73rem !important;
        }
    
        .sidebar-divider {
            margin: 8px 0 6px;
        }
    
        .sidebar-footer {
            font-size: 0.53rem;
        }
    }
    
    /* Telas muito baixas */
    @media (max-height: 700px) {
    
        .sidebar-brand-subtitle {
            display: none;
        }
    
        .sidebar-user-email {
            display: none;
        }
    
        .sidebar-brand-card {
            padding: 9px 11px;
        }
    
        .sidebar-user-card {
            padding: 7px 8px;
        }
    
        .sidebar-role-badge {
            margin-bottom: 5px;
        }
    
        .sidebar-section-label {
            margin-top: 6px;
            margin-bottom: 3px;
        }
    
        section[data-testid="stSidebar"]
        div[data-testid="stButton"] > button,
        section[data-testid="stSidebar"]
        div[data-testid="stLinkButton"] a {
            min-height: 31px;
            padding-top: 0.20rem !important;
            padding-bottom: 0.20rem !important;
        }
    
        .sidebar-footer {
            display: none;
        }
    }
    


    /* ==========================================
       CHAMADOS DOS APROVADORES
       ========================================== */

    div[data-testid="stExpander"] {
        border: 1px solid rgba(128, 128, 128, 0.24) !important;
        border-radius: 12px !important;
        background: var(--secondary-background-color) !important;
        overflow: hidden;
        margin-bottom: 0.75rem;
    }

    div[data-testid="stExpander"] details > summary {
        padding: 0.8rem 1rem !important;
        background: var(--secondary-background-color) !important;
        color: var(--text-color) !important;
        font-weight: 650 !important;
    }

    div[data-testid="stExpander"] details[open] > summary {
        border-bottom: 1px solid rgba(128, 128, 128, 0.18);
    }

    .caproq-section-title {
        margin: 1rem 0 0.65rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid rgba(128, 128, 128, 0.20);
        color: var(--text-color);
        font-size: 0.82rem;
        font-weight: 750;
        letter-spacing: 0.035em;
        text-transform: uppercase;
    }

    .caproq-score-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
        gap: 0.55rem;
        margin-bottom: 0.8rem;
    }

    .caproq-score-item {
        min-width: 0;
        display: flex;
        align-items: center;
        gap: 0.55rem;
        padding: 0.65rem 0.7rem;
        border: 1px solid rgba(128, 128, 128, 0.20);
        border-radius: 10px;
        background: var(--background-color);
    }

    .caproq-score-icon {
        width: 28px;
        height: 28px;
        flex: 0 0 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        font-size: 0.82rem;
        font-weight: 800;
    }

    .caproq-score-content {
        min-width: 0;
    }

    .caproq-score-area {
        overflow: hidden;
        color: var(--text-color);
        font-size: 0.72rem;
        font-weight: 700;
        line-height: 1.25;
        text-overflow: ellipsis;
    }

    .caproq-score-status {
        margin-top: 0.08rem;
        font-size: 0.64rem;
        font-weight: 650;
    }

    .caproq-score-item.aprovado {
        border-color: rgba(0, 141, 76, 0.34);
        background: rgba(0, 141, 76, 0.08);
    }

    .caproq-score-item.aprovado .caproq-score-icon {
        background: rgba(0, 141, 76, 0.16);
        color: #008d4c;
    }

    .caproq-score-item.aprovado .caproq-score-status {
        color: #008d4c;
    }

    .caproq-score-item.ressalva {
        border-color: rgba(230, 162, 60, 0.38);
        background: rgba(230, 162, 60, 0.09);
    }

    .caproq-score-item.ressalva .caproq-score-icon {
        background: rgba(230, 162, 60, 0.18);
        color: #c98618;
    }

    .caproq-score-item.ressalva .caproq-score-status {
        color: #c98618;
    }

    .caproq-score-item.reprovado {
        border-color: rgba(217, 48, 37, 0.34);
        background: rgba(217, 48, 37, 0.08);
    }

    .caproq-score-item.reprovado .caproq-score-icon {
        background: rgba(217, 48, 37, 0.16);
        color: #d93025;
    }

    .caproq-score-item.reprovado .caproq-score-status {
        color: #d93025;
    }

    .caproq-score-item.pendente {
        border-color: rgba(128, 128, 128, 0.24);
        background: rgba(128, 128, 128, 0.07);
    }

    .caproq-score-item.pendente .caproq-score-icon {
        background: rgba(128, 128, 128, 0.14);
        color: var(--text-color);
        opacity: 0.72;
    }

    .caproq-score-item.pendente .caproq-score-status {
        color: var(--text-color);
        opacity: 0.62;
    }

    @media (max-width: 760px) {
        .caproq-score-grid {
            grid-template-columns: 1fr;
        }
    }


    /* ==========================================
       DESIGN SYSTEM — PAINEL DE APROVAÇÕES
       ========================================== */

    .caproq-page-hero {
        position: relative;
        overflow: hidden;
        margin: 0.25rem 0 1rem;
        padding: 1.15rem 1.3rem;
        border: 1px solid rgba(0, 86, 145, 0.22);
        border-radius: 16px;
        background:
            linear-gradient(135deg, rgba(0, 86, 145, 0.14), rgba(0, 61, 102, 0.05)),
            var(--secondary-background-color);
        box-shadow: 0 8px 26px rgba(0, 61, 102, 0.08);
    }

    .caproq-page-hero::after {
        content: "";
        position: absolute;
        top: -55px;
        right: -45px;
        width: 165px;
        height: 165px;
        border-radius: 50%;
        background: rgba(0, 86, 145, 0.08);
        pointer-events: none;
    }

    .caproq-page-kicker {
        margin: 0 0 0.3rem;
        color: var(--primary-color);
        font-size: 0.69rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .caproq-page-title {
        margin: 0;
        color: var(--text-color) !important;
        font-size: clamp(1.35rem, 2.6vw, 2rem);
        font-weight: 780;
        line-height: 1.15;
    }

    .caproq-page-subtitle {
        max-width: 760px;
        margin: 0.4rem 0 0;
        color: var(--text-color);
        opacity: 0.70;
        font-size: 0.88rem;
        line-height: 1.5;
    }

    .caproq-section-intro {
        margin: 0.25rem 0 0.9rem;
        padding: 0.85rem 0.95rem;
        border-left: 4px solid var(--primary-color);
        border-radius: 0 10px 10px 0;
        background: rgba(0, 86, 145, 0.07);
    }

    .caproq-section-intro-title {
        margin: 0;
        color: var(--text-color);
        font-size: 1rem;
        font-weight: 750;
    }

    .caproq-section-intro-text {
        margin: 0.24rem 0 0;
        color: var(--text-color);
        opacity: 0.68;
        font-size: 0.78rem;
        line-height: 1.45;
    }

    /* Cartões de métricas */
    div[data-testid="stMetric"] {
        min-height: 108px;
        padding: 0.9rem 1rem;
        border: 1px solid rgba(128, 128, 128, 0.20);
        border-radius: 14px;
        background: var(--secondary-background-color);
        box-shadow: 0 5px 18px rgba(0, 0, 0, 0.05);
    }

    div[data-testid="stMetric"] label {
        color: var(--text-color) !important;
        opacity: 0.66;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricValue"] {
        color: var(--text-color) !important;
        font-size: 1.65rem !important;
        font-weight: 780 !important;
    }

    /* Abas principais */
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 0.35rem;
        padding: 0.35rem;
        border: 1px solid rgba(128, 128, 128, 0.18);
        border-radius: 12px;
        background: var(--secondary-background-color);
    }

    div[data-testid="stTabs"] [data-baseweb="tab"] {
        min-height: 39px;
        padding: 0.45rem 0.8rem;
        border-radius: 9px;
        color: var(--text-color);
        font-size: 0.76rem;
        font-weight: 650;
    }

    div[data-testid="stTabs"] [aria-selected="true"] {
        background: rgba(0, 86, 145, 0.12) !important;
        color: var(--primary-color) !important;
    }

    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        display: none;
    }

    /* Containers internos e tabelas */
    div[data-testid="stDataFrame"] {
        overflow: hidden;
        border: 1px solid rgba(128, 128, 128, 0.18);
        border-radius: 12px;
    }

    div[data-testid="stPlotlyChart"] {
        padding: 0.35rem;
        border: 1px solid rgba(128, 128, 128, 0.18);
        border-radius: 13px;
        background: var(--secondary-background-color);
    }

    .caproq-panel-divider {
        height: 1px;
        margin: 1rem 0;
        background: var(--text-color);
        opacity: 0.12;
    }

    @media (max-width: 760px) {
        .caproq-page-hero {
            padding: 1rem;
            border-radius: 13px;
        }

        div[data-testid="stMetric"] {
            min-height: 94px;
        }

        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            overflow-x: auto;
            flex-wrap: nowrap;
        }
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
            and (agora - horario_cache) < 60
        )

        if cache_valido:
            return st.session_state["df_usuarios_cache"].copy()

        df = conn.read(
            worksheet="Usuarios",
            ttl=60
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
if "usuario_cadastrado" not in st.session_state:
    st.session_state["usuario_cadastrado"] = False
if "usuario_validado" not in st.session_state:
    st.session_state["usuario_validado"] = False
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "solicitacoes"

def validar_usuario_logado(email_usuario):
    email_usuario = str(email_usuario or "").strip().lower()

    if not email_usuario:
        return False, "Não foi possível identificar o e-mail da conta Google."

    # Todo usuário autenticado entra, por padrão, como solicitante.
    st.session_state["user_nome"] = (
        st.session_state.get("name")
        or email_usuario.split("@")[0]
        or "Solicitante"
    )
    st.session_state["user_perfil"] = "Solicitante"
    st.session_state["user_alcadas"] = []
    st.session_state["is_admin"] = False
    st.session_state["user_ativo"] = True
    st.session_state["usuario_cadastrado"] = False
    st.session_state["usuario_validado"] = True

    # A aba Usuarios controla apenas permissões especiais e bloqueios.
    if df_usuarios.empty or "Email" not in df_usuarios.columns:
        return True, ""

    usuario_encontrado = df_usuarios[
        df_usuarios["Email"].astype(str).str.strip().str.lower()
        == email_usuario
    ]

    if usuario_encontrado.empty:
        return True, ""

    usuario_info = usuario_encontrado.iloc[0]
    usuario_ativo = (
        str(usuario_info.get("Ativo", "Sim")).strip().lower() == "sim"
    )

    if not usuario_ativo:
        st.session_state["user_ativo"] = False
        return False, "Seu usuário está inativo no sistema."

    nome_planilha = str(usuario_info.get("Nome", "")).strip()
    perfil_planilha = str(
        usuario_info.get("Perfil", "Solicitante")
    ).strip()
    admin_planilha = (
        str(usuario_info.get("Admin", "Não")).strip().lower() == "sim"
    )
    alcadas_raw = str(usuario_info.get("Alcada", "Nenhum")).strip()

    if alcadas_raw and alcadas_raw.lower() not in {"nenhum", "nenhuma"}:
        lista_alcadas = [
            alcada.strip()
            for alcada in alcadas_raw.split(",")
            if alcada.strip()
        ]
    else:
        lista_alcadas = []

    st.session_state["user_nome"] = (
        nome_planilha or st.session_state.get("name") or "Usuário"
    )
    st.session_state["user_perfil"] = perfil_planilha or "Solicitante"
    st.session_state["user_alcadas"] = lista_alcadas
    st.session_state["is_admin"] = admin_planilha
    st.session_state["user_ativo"] = True
    st.session_state["usuario_cadastrado"] = True
    st.session_state["usuario_validado"] = True

    return True, ""


def usuario_eh_admin():
    return bool(st.session_state.get("is_admin", False))


def usuario_eh_aprovador():
    return bool(st.session_state.get("user_alcadas", []))


def usuario_tem_alcada(alcada):
    alcada_normalizada = str(alcada or "").strip().lower()
    alcadas_usuario = {
        str(item).strip().lower()
        for item in st.session_state.get("user_alcadas", [])
    }
    return usuario_eh_admin() or alcada_normalizada in alcadas_usuario


def exigir_login():
    if not st.session_state.get("connected", False):
        st.error("Sua sessão não está autenticada.")
        st.stop()


def exigir_admin():
    exigir_login()
    if not usuario_eh_admin():
        st.error("Você não possui permissão para acessar esta área.")
        st.stop()


def exigir_aprovador():
    exigir_login()
    if not (usuario_eh_aprovador() or usuario_eh_admin()):
        st.error("Esta área está disponível somente para aprovadores.")
        st.stop()

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
if "connected" not in st.session_state:
    st.session_state.connected = False


client_config = {
    "web": {
        "client_id": st.secrets.get(
            "GOOGLE_CLIENT_ID",
            "",
        ),
        "client_secret": st.secrets.get(
            "GOOGLE_CLIENT_SECRET",
            "",
        ),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [
            st.secrets.get(
                "GOOGLE_REDIRECT_URI",
                "",
            )
        ],
    }
}


query_params = st.query_params

if (
    "code" in query_params
    and not st.session_state.get("connected", False)
):
    try:
        codigo_google = query_params["code"]

        if isinstance(codigo_google, list):
            codigo_google = codigo_google[0]

        flow = Flow.from_client_config(
            client_config,
            scopes=[
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
                "openid",
                "https://www.googleapis.com/auth/drive.file",
            ],
            redirect_uri=st.secrets["GOOGLE_REDIRECT_URI"],
        )

        flow.fetch_token(
            code=codigo_google
        )

        credentials = flow.credentials

        st.session_state[
            "google_credentials"
        ] = credentials

        user_info_service = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={
                "Authorization": (
                    f"Bearer {credentials.token}"
                )
            },
            timeout=20,
        ).json()

        st.session_state.connected = True
        st.session_state.name = (
            user_info_service.get("name")
        )
        st.session_state.email = (
            user_info_service.get("email")
        )
        st.session_state.picture = (
            user_info_service.get("picture")
        )

        st.query_params.clear()
        st.rerun()

    except Exception as erro:
        st.session_state[
            "erro_login_google"
        ] = (
            f"{type(erro).__name__}: {erro}"
        )

        st.session_state.connected = False
        st.session_state.pop(
            "google_credentials",
            None,
        )

        st.query_params.clear()
        st.rerun()

# ==============================================================================
# 5. Confirgurações tela de Login                     
# ==============================================================================
if not st.session_state.connected:
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"] {
                display: none !important;
            }

            header[data-testid="stHeader"] {
                height: 0 !important;
                min-height: 0 !important;
                background: transparent !important;
            }

            div[data-testid="stToolbar"] {
                display: none !important;
            }

            .block-container {
                max-width: 100% !important;
                padding-top: 1.2rem !important;
                padding-bottom: 1rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    auth_url = (
        "https://accounts.google.com/o/oauth2/auth?"
        "response_type=code"
        f"&client_id={st.secrets.get('GOOGLE_CLIENT_ID', '')}"
        f"&redirect_uri={st.secrets.get('GOOGLE_REDIRECT_URI', '')}"
        "&scope="
        "https://www.googleapis.com/auth/userinfo.profile"
        "%20https://www.googleapis.com/auth/userinfo.email"
        "%20openid"
        "%20https://www.googleapis.com/auth/drive.file"
        "&prompt=select_account"
    )

    erro_login = st.session_state.pop(
        "erro_login_google",
        None,
    )

    if erro_login:
        st.error(
            "Não foi possível concluir o login com o Google."
        )

        with st.expander("Detalhes técnicos"):
            st.code(erro_login)

    logo_html = ""

    if os.path.exists("logomoinhos.png"):
        with open("logomoinhos.png", "rb") as arquivo_logo:
            logo_base64 = base64.b64encode(
                arquivo_logo.read()
            ).decode("utf-8")

        logo_html = f"""
        <div class="login-logo-wrap">
            <img
                src="data:image/png;base64,{logo_base64}"
                alt="Hospital Moinhos de Vento"
                class="login-logo-image"
            >
        </div>
        """

    auth_url_html = auth_url

    login_html = f"""
<div class="login-shell">
    <div class="login-premium-grid">

        <div class="login-brand-panel">
            <div>
                <p class="login-brand-kicker">
                    Hospital Moinhos de Vento
                </p>

                <h1 class="login-brand-title">
                    CAPROQ
                </h1>

                <p class="login-brand-text">
                    Plataforma para solicitação, análise técnica,
                    acompanhamento e padronização de produtos químicos.
                </p>
            </div>

            <div class="login-brand-footer">
                Processo integrado de avaliação por alçadas técnicas
            </div>
        </div>

        <div class="login-access-panel">
            {logo_html}

            <h2 class="login-access-title">
                Acesse sua conta
            </h2>

            <p class="login-access-subtitle">
                Entre com sua conta Google para registrar solicitações
                e acompanhar o fluxo de avaliação.
            </p>

            <a
                class="login-google-button"
                href="{auth_url_html}"
                target="_blank" rel="noopener noreferrer"
            >
                Continuar com o Google
            </a>

            <div class="login-security-note">
                <strong>Acesso seguro</strong><br>
                Usuários não cadastrados entram automaticamente como
                solicitantes. Permissões adicionais são carregadas
                conforme a aba de usuários.
            </div>
        </div>

    </div>
</div>
"""

    st.html(login_html)

    st.stop()

usuario_valido, mensagem_validacao = validar_usuario_logado(
    st.session_state.get("email", "")
)

if not usuario_valido:
    st.error(f"❌ {mensagem_validacao}")
    st.info(
        "Entre em contato com a administração do CAPROQ caso seja "
        "necessário reativar seu acesso."
    )

    if st.button(
        "Voltar para o login",
        use_container_width=True,
        key="voltar_login_usuario_inativo",
    ):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

    st.stop()

exigir_login()

usuario_privilegiado = (
    usuario_eh_aprovador()
    or usuario_eh_admin()
)

if (
    usuario_privilegiado
    and st.session_state.get("pagina_atual") == "solicitacoes"
):
    st.session_state["pagina_atual"] = "painel_principal"

if "pagina_atual" not in st.session_state:

    if usuario_eh_admin() or usuario_eh_aprovador():
        st.session_state["pagina_atual"] = "painel_principal"

    else:
        st.session_state["pagina_atual"] = "solicitacoes"

pagina = st.session_state["pagina_atual"]

CAPROQ_SHEETS_URL = str(
    st.secrets.get("CAPROQ_SHEETS_URL", "")
).strip()

CAPROQ_DRIVE_URL = str(
    st.secrets.get("CAPROQ_DRIVE_URL", "")
).strip()

# ==============================================================================
# 6. Configurações da sidebar
# ==============================================================================
# ------------------------------------------------------------------------------
# Cabeçalho institucional
# ------------------------------------------------------------------------------

st.sidebar.markdown(
    """
<div class="sidebar-brand-card">
    <p class="sidebar-brand-kicker">Hospital Moinhos de Vento</p>
    <p class="sidebar-brand-title">CAPROQ</p>
    <p class="sidebar-brand-subtitle">
        Gestão e padronização de produtos químicos
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# Dados do usuário
# ------------------------------------------------------------------------------

user_name = (
    st.session_state.get("user_nome")
    or st.session_state.get("name")
    or "Usuário"
)

user_email = (
    st.session_state.get("email")
    or ""
)

user_picture = (
    st.session_state.get("picture")
    or "https://cdn-icons-png.flaticon.com/512/149/149071.png"
)

if usuario_eh_admin():
    perfil_usuario = "Administrador"
    icone_perfil = "🛡️"

elif usuario_eh_aprovador():
    perfil_usuario = "Aprovador"
    icone_perfil = "✅"

else:
    perfil_usuario = "Solicitante"
    icone_perfil = "👤"

user_name_safe = escape(str(user_name))
user_email_safe = escape(str(user_email))
user_picture_safe = escape(str(user_picture), quote=True)
perfil_usuario_safe = escape(str(perfil_usuario))

avatar_html = f"""
<div class="sidebar-user-card">
    <img
        class="sidebar-user-avatar"
        src="{user_picture_safe}"
        alt="Foto do usuário"
        onerror="this.onerror=null;this.src='https://cdn-icons-png.flaticon.com/512/149/149071.png';"
    >
    <div class="sidebar-user-info">
        <span class="sidebar-user-name">{user_name_safe}</span>
        <span class="sidebar-user-email">{user_email_safe}</span>
    </div>
</div>
<div class="sidebar-role-badge">
    {icone_perfil}&nbsp; {perfil_usuario_safe}
</div>
"""

st.sidebar.markdown(
    avatar_html,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# Navegação principal
# ------------------------------------------------------------------------------

st.sidebar.markdown(
    '<div class="sidebar-section-label">Navegação</div>',
    unsafe_allow_html=True,
)

# Tela exclusiva dos solicitantes
if not usuario_privilegiado:

    if st.sidebar.button(
        "📝 Nova solicitação",
        use_container_width=True,
        key="menu_solicitacoes",
    ):
        st.session_state["pagina_atual"] = "solicitacoes"
        st.rerun()

# Painel exclusivo dos aprovadores e administradores
if usuario_privilegiado:

    if st.sidebar.button(
        "📥 Painel de aprovações",
        use_container_width=True,
        key="menu_aprovacoes",
    ):
        st.session_state["pagina_atual"] = "painel_principal"
        st.rerun()

# ------------------------------------------------------------------------------
# Área administrativa
# ------------------------------------------------------------------------------

if usuario_eh_admin():

    st.sidebar.markdown(
        '<div class="sidebar-section-label">Administração</div>',
        unsafe_allow_html=True,
    )

    if st.sidebar.button(
        "🛡️ Homologação final",
        use_container_width=True,
        key="menu_homologacao",
    ):
        st.session_state["pagina_atual"] = "homologacao_final"
        st.rerun()

    if st.sidebar.button(
        "⚙️ Gerenciar aprovadores",
        use_container_width=True,
        key="menu_usuarios",
    ):
        st.session_state["pagina_atual"] = "gerenciar_aprovadores"
        st.rerun()

# ------------------------------------------------------------------------------
# Acessos externos
# ------------------------------------------------------------------------------

if usuario_privilegiado:

    st.sidebar.markdown(
        '<div class="sidebar-section-label">Acessos rápidos</div>',
        unsafe_allow_html=True,
    )

    if CAPROQ_SHEETS_URL:

        st.sidebar.link_button(
            "📊 Planilha do CAPROQ",
            CAPROQ_SHEETS_URL,
            use_container_width=True,
        )

    else:

        st.sidebar.button(
            "📊 Planilha não configurada",
            use_container_width=True,
            disabled=True,
            key="link_sheets_nao_configurado",
            help=(
                "Adicione CAPROQ_SHEETS_URL "
                "nos Secrets do aplicativo."
            ),
        )

    if CAPROQ_DRIVE_URL:

        st.sidebar.link_button(
            "📁 Pasta de documentos",
            CAPROQ_DRIVE_URL,
            use_container_width=True,
        )

# ------------------------------------------------------------------------------
# Rodapé e saída
# ------------------------------------------------------------------------------

st.sidebar.markdown(
    '<div class="sidebar-divider"></div>',
    unsafe_allow_html=True,
)

if st.sidebar.button(
    "🚪 Encerrar sessão",
    use_container_width=True,
    key="botao_sair_sidebar",
):
    st.session_state.pop(
        "google_credentials",
        None,
    )

    st.session_state.pop(
        "oauth_state",
        None,
    )

    st.session_state.pop(
        "google_auth_url",
        None,
    )

    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown(
    """
<div class="sidebar-footer">
    CAPROQ · Hospital Moinhos de Vento<br>
    Processo integrado de avaliação técnica
</div>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 7. Tela principal
# ==============================================================================
df_dados = carregar_dados()

user_email = st.session_state.get('email', '')
user_name = (
    st.session_state.get('user_nome')
    or st.session_state.get('name')
    or 'Usuário'
)
is_aprovador = usuario_eh_aprovador() or usuario_eh_admin()

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
if is_aprovador and st.session_state.get("pagina_atual") != "solicitacoes":
    exigir_aprovador()
    
    if st.session_state.get("is_admin", False) and st.session_state.get("pagina_atual") == "gerenciar_aprovadores":
        exigir_admin()

        st.markdown(
            """
<style>
.caproq-admin-hero {
    padding: 1.55rem 1.65rem;
    border: 1px solid rgba(0, 86, 145, .16);
    border-radius: 20px;
    background: linear-gradient(135deg, rgba(0, 86, 145, .12), rgba(0, 86, 145, .03));
    margin-bottom: 1rem;
}
.caproq-admin-kicker {
    margin: 0 0 .35rem 0;
    color: #005691;
    font-size: .78rem;
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
}
.caproq-admin-title {
    margin: 0;
    font-size: clamp(1.65rem, 3vw, 2.35rem);
    line-height: 1.12;
}
.caproq-admin-subtitle {
    margin: .6rem 0 0 0;
    max-width: 880px;
    opacity: .76;
    line-height: 1.55;
}
.caproq-admin-section {
    margin: 1.2rem 0 .65rem 0;
}
.caproq-admin-section h3 {
    margin: 0;
    font-size: 1.05rem;
}
.caproq-admin-section p {
    margin: .25rem 0 0 0;
    opacity: .7;
    font-size: .9rem;
}
.caproq-admin-note {
    padding: .9rem 1rem;
    border-radius: 14px;
    border: 1px solid rgba(0, 86, 145, .14);
    background: rgba(0, 86, 145, .045);
    margin-bottom: .8rem;
}
.caproq-admin-danger {
    padding: .95rem 1rem;
    border-radius: 14px;
    border: 1px solid rgba(198, 40, 40, .24);
    background: rgba(198, 40, 40, .06);
    margin-bottom: .8rem;
}
@media (prefers-color-scheme: dark) {
    .caproq-admin-hero,
    .caproq-admin-note {
        border-color: rgba(120, 190, 235, .20);
        background: rgba(0, 86, 145, .12);
    }
}
</style>
<div class="caproq-admin-hero">
    <p class="caproq-admin-kicker">Administração · CAPROQ</p>
    <h1 class="caproq-admin-title">Gestão de usuários e alçadas</h1>
    <p class="caproq-admin-subtitle">
        Controle acessos, perfis administrativos e responsabilidades técnicas
        vinculadas à aba <strong>Usuarios</strong> do Google Sheets.
    </p>
</div>
""",
            unsafe_allow_html=True,
        )

        df_usuarios = carregar_dados_usuarios()

        if not df_usuarios.empty:
            df_usuarios["Email"] = df_usuarios["Email"].astype(str).str.strip().str.lower()
            df_usuarios["Ativo"] = df_usuarios["Ativo"].astype(str).str.strip().str.upper()
            df_usuarios["Admin"] = df_usuarios["Admin"].astype(str).str.strip().str.upper()

        total_usuarios = len(df_usuarios) if not df_usuarios.empty else 0
        total_ativos = int((df_usuarios["Ativo"] == "SIM").sum()) if not df_usuarios.empty else 0
        total_admins = int((df_usuarios["Admin"] == "SIM").sum()) if not df_usuarios.empty else 0
        total_aprovadores = int((df_usuarios["Perfil"].astype(str).str.lower() == "aprovador").sum()) if not df_usuarios.empty and "Perfil" in df_usuarios.columns else 0

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Usuários cadastrados", total_usuarios)
        col_m2.metric("Usuários ativos", total_ativos)
        col_m3.metric("Aprovadores", total_aprovadores)
        col_m4.metric("Administradores", total_admins)

        st.markdown(
            """
<div class="caproq-admin-section">
    <h3>👥 Diretório de usuários</h3>
    <p>Visualize os cadastros existentes e confira rapidamente perfis, alçadas e situação de acesso.</p>
</div>
""",
            unsafe_allow_html=True,
        )

        if not df_usuarios.empty:
            col_busca, col_status, col_perfil = st.columns([2.2, 1, 1])
            with col_busca:
                busca_usuario = st.text_input(
                    "Buscar usuário",
                    placeholder="Nome ou e-mail",
                    key="busca_usuario_admin",
                )
            with col_status:
                filtro_status = st.selectbox(
                    "Status",
                    ["Todos", "Ativos", "Inativos"],
                    key="filtro_status_usuario_admin",
                )
            with col_perfil:
                perfis_disponiveis = sorted(
                    [p for p in df_usuarios.get("Perfil", pd.Series(dtype=str)).dropna().astype(str).unique() if p.strip()]
                )
                filtro_perfil = st.selectbox(
                    "Perfil",
                    ["Todos"] + perfis_disponiveis,
                    key="filtro_perfil_usuario_admin",
                )

            df_exibicao = df_usuarios.copy()
            if busca_usuario.strip():
                termo = busca_usuario.strip().lower()
                mascara_busca = (
                    df_exibicao["Email"].astype(str).str.lower().str.contains(termo, na=False)
                    | df_exibicao["Nome"].astype(str).str.lower().str.contains(termo, na=False)
                )
                df_exibicao = df_exibicao[mascara_busca]

            if filtro_status == "Ativos":
                df_exibicao = df_exibicao[df_exibicao["Ativo"] == "SIM"]
            elif filtro_status == "Inativos":
                df_exibicao = df_exibicao[df_exibicao["Ativo"] != "SIM"]

            if filtro_perfil != "Todos":
                df_exibicao = df_exibicao[df_exibicao["Perfil"].astype(str) == filtro_perfil]

            st.caption(f"Exibindo {len(df_exibicao)} de {total_usuarios} usuários.")
            st.dataframe(
                df_exibicao,
                column_config={
                    "Email": st.column_config.TextColumn("E-mail"),
                    "Nome": st.column_config.TextColumn("Nome completo"),
                    "Perfil": st.column_config.TextColumn("Perfil"),
                    "Alcada": st.column_config.TextColumn("Alçadas associadas"),
                    "Admin": st.column_config.TextColumn("Administrador"),
                    "Ativo": st.column_config.TextColumn("Ativo"),
                    "Data_Cadastro": st.column_config.TextColumn("Cadastro"),
                },
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("⚠️ Nenhum usuário encontrado na aba 'Usuarios' do Google Sheets.")

        st.markdown(
            """
<div class="caproq-admin-section">
    <h3>⚙️ Ações administrativas</h3>
    <p>Cadastre, atualize ou remova usuários mantendo o controle centralizado no Google Sheets.</p>
</div>
""",
            unsafe_allow_html=True,
        )

        tab_salvar_usuario, tab_excluir_usuario = st.tabs([
            "➕ Cadastrar ou atualizar",
            "🗑️ Remover usuário",
        ])

        lista_alcadas_disponiveis = [
            ALCADAS_INFO[chave].get("label", chave) for chave in ALCADAS_INFO.keys()
        ]

        with tab_salvar_usuario:
            st.markdown(
                """
<div class="caproq-admin-note">
    <strong>Cadastro inteligente:</strong> quando o e-mail já existir, o registro será atualizado sem criar duplicidade.
</div>
""",
                unsafe_allow_html=True,
            )

            with st.form("form_usuario_sheets"):
                st.markdown("#### Identificação do usuário")
                col_ident1, col_ident2 = st.columns(2)
                with col_ident1:
                    email_input = st.text_input(
                        "E-mail do usuário *",
                        placeholder="nome@empresa.com.br",
                    ).strip().lower()
                with col_ident2:
                    nome_input = st.text_input(
                        "Nome completo *",
                        placeholder="Nome e sobrenome",
                    )

                st.markdown("#### Perfil e permissões")
                col_permissao1, col_permissao2, col_permissao3 = st.columns(3)
                with col_permissao1:
                    perfil_input = st.selectbox(
                        "Perfil de acesso",
                        ["Aprovador", "Solicitante", "Visualizador"],
                    )
                with col_permissao2:
                    is_admin_input = st.selectbox("Administrador", ["NÃO", "SIM"])
                with col_permissao3:
                    is_ativo_input = st.selectbox("Usuário ativo", ["SIM", "NÃO"])

                st.markdown("#### Alçadas técnicas")
                st.caption("Selecione somente as áreas pelas quais o usuário será responsável.")
                alcadas_selecionadas = []
                col_checkboxes = st.columns(2)
                for idx, nome_alcada in enumerate(lista_alcadas_disponiveis):
                    with col_checkboxes[idx % 2]:
                        if st.checkbox(nome_alcada, key=f"check_alcada_{nome_alcada}"):
                            alcadas_selecionadas.append(nome_alcada)

                botao_salvar_usr = st.form_submit_button(
                    "💾 Salvar usuário",
                    use_container_width=True,
                    type="primary",
                )

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
                            "Data_Cadastro": data_atual_str,
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

        with tab_excluir_usuario:
            st.markdown(
                """
<div class="caproq-admin-danger">
    <strong>Atenção:</strong> a remoção apaga o registro da base do sistema. Para apenas bloquear o acesso, prefira atualizar o usuário como <strong>inativo</strong>.
</div>
""",
                unsafe_allow_html=True,
            )

            if not df_usuarios.empty:
                opcoes_exclusao = {
                    f"{valor_seguro(row.get('Nome'))} · {row.get('Email', '')}": row.get("Email", "")
                    for _, row in df_usuarios.iterrows()
                }
                with st.form("form_excluir_usuario"):
                    usuario_excluir_label = st.selectbox(
                        "Selecione o usuário para remover",
                        options=list(opcoes_exclusao.keys()),
                    )
                    email_excluir = opcoes_exclusao[usuario_excluir_label]
                    confirmar_exclusao = st.checkbox(
                        "Confirmo que desejo apagar permanentemente este registro."
                    )
                    botao_excluir_usr = st.form_submit_button(
                        "🗑️ Remover usuário",
                        use_container_width=True,
                    )

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
        st.markdown(
            """
<div class="caproq-page-hero">
    <p class="caproq-page-kicker">Central técnica · CAPROQ</p>
    <h1 class="caproq-page-title">Painel de Aprovações</h1>
    <p class="caproq-page-subtitle">
        Consulte solicitações, acompanhe o andamento das alçadas e registre
        decisões técnicas em um ambiente único e organizado.
    </p>
</div>
""",
            unsafe_allow_html=True,
        )
        
        colunas_permitidas_usuario = []
        is_user_admin = user_email in ADMINS
        
        for letra_col, info_alcada in ALCADAS_INFO.items():
            nome_coluna_sheets = info_alcada["coluna_sheets"]
            emails_alcada = info_alcada.get("emails", [])
            if not isinstance(emails_alcada, list):
                emails_alcada = [emails_alcada]
            if is_user_admin or user_email in emails_alcada:
                colunas_permitidas_usuario.append(nome_coluna_sheets)

        if not df_dados.empty:
            colunas_validas = [c for c in colunas_permitidas_usuario if c in df_dados.columns]
            
            if colunas_validas:
                condicao_pendente = (df_dados["Status_Final"] == "Em análise") & (
                    df_dados[colunas_validas].eq("Pendente").any(axis=1)
                )
                pendentes = df_dados[condicao_pendente]
                
                condicao_historico = df_dados[colunas_validas].apply(
                    lambda col: col.astype(str).str.startswith(("Aprovar", "Reprovar"), na=False)
                ).any(axis=1)
                
                historico_aprovador = df_dados[condicao_historico]
            else:
                pendentes = pd.DataFrame()
                historico_aprovador = pd.DataFrame()
            
            total_aprovados = len(
                df_dados[df_dados["Status_Final"] == "Aprovado"]
            )
            total_reprovados = len(
                df_dados[df_dados["Status_Final"] == "Reprovado"]
            )

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Pendências da sua área", len(pendentes))
            with m2:
                st.metric("Chamados aprovados", total_aprovados)
            with m3:
                st.metric("Chamados reprovados", total_reprovados)

            st.markdown(
                '<div class="caproq-panel-divider"></div>',
                unsafe_allow_html=True,
            )

            tab_pendentes, tab_hist_aprovador, tab_logs, tab_indicadores = st.tabs([
                "📥 Minhas pendências",
                "📋 Histórico de decisões",
                "🕒 Log de atividades",
                "📊 Indicadores",
            ])
            
            # ----------------------------------------------------------------------
            # 8.1. Aba "Minhas pendências"
            # ----------------------------------------------------------------------
            with tab_pendentes:

                st.markdown(
                    """
<div class="caproq-section-intro">
    <p class="caproq-section-intro-title">Solicitações aguardando seu parecer</p>
    <p class="caproq-section-intro-text">
        Abra um chamado para consultar os dados completos, acompanhar o placar
        das alçadas e registrar sua decisão técnica.
    </p>
</div>
""",
                    unsafe_allow_html=True,
                )

                if pendentes.empty:
                    st.success(
                        "Nenhuma solicitação pendente para a sua alçada técnica "
                        "no momento."
                    )
                else:
                    for _, row in pendentes.iterrows():
                        id_chamado = int(row["ID"])

                        # Identificação uniforme do produto
                        if "Descrição completa do produto" in row.index:
                            col_prod = "Descrição completa do produto"
                        elif "Descrição do produto" in row.index:
                            col_prod = "Descrição do produto"
                        else:
                            col_prod = "Descricao_Produto"

                        descricao_produto = valor_seguro(
                            row.get(col_prod, "Sem descrição"),
                            "Sem descrição",
                        )

                        # Data e hora de abertura para o título resumido
                        carimbo_abertura = row.get(
                            "Carimbo de data/hora",
                            row.get("Timestamp", row.get("Data_Abertura", "")),
                        )
                        abertura_formatada = "Data não informada"

                        if str(carimbo_abertura).strip().lower() not in {
                            "", "nan", "none", "nat"
                        }:
                            try:
                                data_abertura = pd.to_datetime(
                                    carimbo_abertura,
                                    dayfirst=True,
                                    errors="raise",
                                )
                                abertura_formatada = data_abertura.strftime(
                                    "%d/%m/%Y às %H:%M"
                                )
                            except Exception:
                                abertura_formatada = valor_seguro(
                                    carimbo_abertura,
                                    "Data não informada",
                                )

                        titulo_expander = (
                            f"Chamado #{id_chamado} — {descricao_produto} "
                            f"— {abertura_formatada}"
                        )

                        with st.expander(
                            titulo_expander,
                            expanded=False,
                        ):
                            # ------------------------------------------------------
                            # Placar das alçadas
                            # ------------------------------------------------------
                            st.markdown(
                                '<div class="caproq-section-title">'
                                'Situação das alçadas técnicas'
                                '</div>',
                                unsafe_allow_html=True,
                            )

                            itens_placar = []

                            for _, info_placar in ALCADAS_INFO.items():
                                coluna_placar = info_placar["coluna_sheets"]
                                label_placar = info_placar["label"]
                                voto_placar = str(
                                    row.get(coluna_placar, "Pendente")
                                ).strip()
                                voto_minusculo = voto_placar.lower()

                                if voto_placar.startswith("Reprovar"):
                                    classe_status = "reprovado"
                                    texto_status = "Reprovado"
                                    icone_status = "✕"
                                elif "ressalva" in voto_minusculo:
                                    classe_status = "ressalva"
                                    texto_status = "Com ressalva"
                                    icone_status = "!"
                                elif voto_placar.startswith("Aprovar"):
                                    classe_status = "aprovado"
                                    texto_status = "Aprovado"
                                    icone_status = "✓"
                                else:
                                    classe_status = "pendente"
                                    texto_status = "Pendente"
                                    icone_status = "•"

                                itens_placar.append(
                                    f"""
<div class="caproq-score-item {classe_status}">
    <div class="caproq-score-icon">{icone_status}</div>
    <div class="caproq-score-content">
        <div class="caproq-score-area">{escape(label_placar)}</div>
        <div class="caproq-score-status">{texto_status}</div>
    </div>
</div>
"""
                                )

                            st.markdown(
                                '<div class="caproq-score-grid">'
                                + "".join(itens_placar)
                                + "</div>",
                                unsafe_allow_html=True,
                            )

                            # ------------------------------------------------------
                            # Resumo da solicitação
                            # ------------------------------------------------------
                            nome_solicitante_chamado = valor_seguro(
                                row.get(
                                    "Nome solicitante",
                                    row.get("Nome", "Não informado"),
                                ),
                                "Não informado",
                            )
                            email_solicitante_chamado = valor_seguro(
                                row.get("Endereço de e-mail", ""),
                                "Não informado",
                            )

                            st.markdown(
                                '<div class="caproq-section-title">'
                                'Resumo da solicitação'
                                '</div>',
                                unsafe_allow_html=True,
                            )

                            resumo_col1, resumo_col2, resumo_col3 = st.columns(3)

                            with resumo_col1:
                                st.markdown("**Solicitante**")
                                st.write(nome_solicitante_chamado)

                            with resumo_col2:
                                st.markdown("**E-mail**")
                                st.write(email_solicitante_chamado)

                            with resumo_col3:
                                st.markdown("**Abertura**")
                                st.write(abertura_formatada)

                            # ------------------------------------------------------
                            # Dados completos do formulário
                            # ------------------------------------------------------
                            st.markdown(
                                '<div class="caproq-section-title">'
                                'Informações do produto'
                                '</div>',
                                unsafe_allow_html=True,
                            )

                            col_detalhe1, col_detalhe2 = st.columns(2)

                            with col_detalhe1:
                                st.markdown("**Descrição do produto**")
                                st.write(descricao_produto)

                                st.markdown("**Apresentação / volume**")
                                st.write(valor_seguro(row.get("Apresentação/volume", "")))

                                st.markdown("**Fabricante / fornecedor**")
                                st.write(valor_seguro(row.get("Fabricante/fornecedor", "")))

                                st.markdown("**Área e indicação de uso**")
                                st.write(
                                    valor_seguro(
                                        row.get(
                                            "Área onde será utilizado e indicação detalhada de uso do produto",
                                            "",
                                        )
                                    )
                                )

                            with col_detalhe2:
                                st.markdown("**Contato do fornecedor**")
                                st.write(
                                    valor_seguro(
                                        row.get(
                                            "Informações de contato do fornecedor (nome, e-mail e telefone)",
                                            "",
                                        )
                                    )
                                )

                                st.markdown("**Procedimento atual sem o produto**")
                                st.write(
                                    valor_seguro(
                                        row.get(
                                            "Explique como o procedimento/atividade atual é realizado SEM este produto:",
                                            "",
                                        )
                                    )
                                )

                                st.markdown("**Gera resíduo perigoso?**")
                                st.write(
                                    valor_seguro(
                                        row.get(
                                            "O item solicitado gera resíduo perigoso?",
                                            "",
                                        )
                                    )
                                )

                                st.markdown("**Possui estudos científicos?**")
                                st.write(
                                    valor_seguro(
                                        row.get(
                                            "O produto apresenta estudos científicos e de custo-efetividade comparado com o utilizado atualmente no HMV? Caso sim, anexe o arquivo abaixo.",
                                            "",
                                        )
                                    )
                                )

                            # ------------------------------------------------------
                            # Documentos
                            # ------------------------------------------------------
                            st.markdown(
                                '<div class="caproq-section-title">Documentos</div>',
                                unsafe_allow_html=True,
                            )

                            link_anexo = row.get(
                                "Link_Anexo",
                                row.get("Arquivos anexados", ""),
                            )
                            link_fds = row.get("Anexar FDS", "")

                            doc_col1, doc_col2 = st.columns(2)

                            with doc_col1:
                                if str(link_fds).strip().lower() not in {
                                    "", "nan", "none", "não aplicável"
                                }:
                                    st.link_button(
                                        "📄 Abrir FDS",
                                        str(link_fds).strip(),
                                        use_container_width=True,
                                    )
                                else:
                                    st.caption("FDS não disponível.")

                            with doc_col2:
                                if str(link_anexo).strip().lower() not in {
                                    "",
                                    "nan",
                                    "none",
                                    "nenhum arquivo anexado",
                                    "nenhum arquivo adicional",
                                }:
                                    st.link_button(
                                        "📎 Abrir arquivos anexados",
                                        str(link_anexo).strip(),
                                        use_container_width=True,
                                    )
                                else:
                                    st.caption("Nenhum arquivo adicional anexado.")

                            st.markdown(
                                '<div class="caproq-section-title">'
                                'Seu parecer técnico'
                                '</div>',
                                unsafe_allow_html=True,
                            )
                            
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

                st.markdown(
                    """
<div class="caproq-section-intro">
    <p class="caproq-section-intro-title">Acompanhamento e histórico de deliberações</p>
    <p class="caproq-section-intro-text">
        Consulte decisões já registradas, situação das áreas e prazos de resposta
        de cada alçada técnica.
    </p>
</div>
""",
                    unsafe_allow_html=True,
                )
                
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

                st.markdown(
                    """
<div class="caproq-section-intro">
    <p class="caproq-section-intro-title">Linha do tempo e auditoria dos processos</p>
    <p class="caproq-section-intro-text">
        Acompanhe os registros desde a abertura do chamado até o encerramento,
        com foco em rastreabilidade e conformidade.
    </p>
</div>
""",
                    unsafe_allow_html=True,
                )
                
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

                st.markdown(
                    """
<div class="caproq-section-intro">
    <p class="caproq-section-intro-title">Painel analítico do CAPROQ</p>
    <p class="caproq-section-intro-text">
        Visualize volumetria, distribuição das decisões e desempenho do fluxo
        técnico do comitê.
    </p>
</div>
""",
                    unsafe_allow_html=True,
                )
                
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
                
                st.markdown('<div class="caproq-section-title">Volumetria temporal</div>', unsafe_allow_html=True)
                kpi_t1, kpi_t2, kpi_t3, kpi_t4 = st.columns(4)
                with kpi_t1: st.metric("Últimos 7 dias (Semanal)", qtd_semana)
                with kpi_t2: st.metric("Últimos 30 dias (Mensal)", qtd_mes)
                with kpi_t3: st.metric("Último Ano (Anual)", qtd_ano)
                with kpi_t4: st.metric("Total Histórico", len(df_dados))
                
                st.markdown("---")
                
                st.markdown('<div class="caproq-section-title">Distribuição mensal das deliberações</div>', unsafe_allow_html=True)
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
                st.markdown('<div class="caproq-section-title">Performance histórica por alçada</div>', unsafe_allow_html=True)
                
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
        exigir_admin()

        st.markdown(
            """
            <style>
            .caproq-homolog-header {
                padding: 1.45rem 1.55rem;
                border: 1px solid rgba(49, 130, 206, .20);
                border-radius: 18px;
                background: linear-gradient(135deg, rgba(0, 86, 145, .13), rgba(0, 86, 145, .03));
                margin: .25rem 0 1.1rem;
            }
            .caproq-homolog-kicker {
                font-size: .74rem; font-weight: 800; letter-spacing: .13em;
                text-transform: uppercase; opacity: .72; margin-bottom: .35rem;
            }
            .caproq-homolog-title {
                font-size: 1.7rem; font-weight: 800; line-height: 1.15; margin: 0;
            }
            .caproq-homolog-subtitle {
                margin-top: .45rem; opacity: .78; line-height: 1.5;
            }
            .caproq-summary-grid {
                display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: .7rem; margin: .8rem 0 1rem;
            }
            .caproq-summary-card {
                padding: .8rem .9rem; border-radius: 13px;
                border: 1px solid rgba(128,128,128,.20);
                background: rgba(128,128,128,.055); min-height: 74px;
            }
            .caproq-summary-label {
                font-size: .70rem; font-weight: 800; letter-spacing: .06em;
                text-transform: uppercase; opacity: .62; margin-bottom: .28rem;
            }
            .caproq-summary-value { font-weight: 700; line-height: 1.25; overflow-wrap: anywhere; }
            .caproq-score-grid {
                display:grid; grid-template-columns:repeat(auto-fit,minmax(135px,1fr));
                gap:.55rem; margin:.65rem 0 1rem;
            }
            .caproq-score-card {
                padding:.72rem .75rem; border-radius:12px; border:1px solid var(--score-border);
                background:var(--score-bg);
            }
            .caproq-score-label { font-size:.72rem; font-weight:800; opacity:.75; margin-bottom:.25rem; }
            .caproq-score-status { font-size:.84rem; font-weight:800; }
            .caproq-section-title {
                margin: 1.1rem 0 .6rem; padding-left:.7rem; border-left:4px solid #005691;
                font-size:1.02rem; font-weight:800;
            }
            .caproq-parecer-card {
                padding:.85rem .95rem; margin:.55rem 0; border-radius:12px;
                border:1px solid rgba(128,128,128,.18); background:rgba(128,128,128,.045);
            }
            .caproq-parecer-head { font-weight:800; margin-bottom:.35rem; }
            .caproq-parecer-text { opacity:.82; line-height:1.5; overflow-wrap:anywhere; }
            .caproq-decision-box {
                margin:1.2rem 0 .7rem; padding:1rem 1.1rem; border-radius:14px;
                border:1px solid rgba(0,86,145,.28); background:rgba(0,86,145,.07);
            }
            @media (max-width: 900px) {
                .caproq-summary-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
            }
            @media (max-width: 560px) {
                .caproq-summary-grid { grid-template-columns:1fr; }
                .caproq-homolog-title { font-size:1.35rem; }
            }
            </style>
            <div class="caproq-homolog-header">
                <div class="caproq-homolog-kicker">CAPROQ · Governança técnica</div>
                <div class="caproq-homolog-title">🛡️ Homologação e decisão final</div>
                <div class="caproq-homolog-subtitle">
                    Consolide os pareceres das alçadas, registre as validações finais e formalize a decisão institucional sobre o produto.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
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
                total_homologacao = len(chamados_para_decisao)
                total_reuniao = chamados_para_decisao[
                    chamados_para_decisao["Status_Aprovadores"]
                    .astype(str)
                    .str.lower()
                    .str.contains("reunião|reuniao", regex=True)
                ].shape[0]
                total_teste = chamados_para_decisao.get(
                    "Produto_Teste", pd.Series(index=chamados_para_decisao.index, dtype=str)
                ).astype(str).str.strip().str.upper().eq("SIM").sum()

                metrica_1, metrica_2, metrica_3 = st.columns(3)
                metrica_1.metric("Aguardando decisão", total_homologacao)
                metrica_2.metric("Produtos de teste", int(total_teste))
                metrica_3.metric("Com reunião indicada", total_reuniao)
                st.caption(
                    "Abra um chamado para visualizar o resumo executivo, os pareceres técnicos e o formulário de decisão final."
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

                    data_abertura = row.get(
                        "Carimbo de data/hora", row.get("Timestamp", "")
                    )
                    try:
                        data_abertura_formatada = pd.to_datetime(
                            data_abertura, dayfirst=True
                        ).strftime("%d/%m/%Y às %H:%M")
                    except Exception:
                        data_abertura_formatada = valor_seguro(data_abertura)

                    titulo_homologacao = (
                        f"Chamado #{id_chamado} · {descricao_produto} · "
                        f"{data_abertura_formatada}"
                    )

                    with st.expander(titulo_homologacao, expanded=False):
                        eh_produto_teste = (
                            str(row.get("Produto_Teste", "NÃO"))
                            .strip()
                            .upper()
                            == "SIM"
                        )

                        nome_solicitante_resumo = valor_seguro(
                            row.get("Nome solicitante", row.get("Nome", "Não informado"))
                        )
                        setor_solicitante_resumo = valor_seguro(
                            row.get("Setor_Solicitante", row.get("Setor", "Não informado"))
                        )
                        fornecedor_resumo = valor_seguro(
                            row.get("Fornecedor", row.get("Nome do fornecedor", "Não informado"))
                        )
                        tipo_resumo = "Produto de teste / piloto" if eh_produto_teste else "Solicitação padrão"
                        status_seguro = escape(valor_seguro(status_apr))
                        st.markdown(
                            f"""
                            <div class="caproq-summary-grid">
                                <div class="caproq-summary-card"><div class="caproq-summary-label">Solicitante</div><div class="caproq-summary-value">{escape(nome_solicitante_resumo)}</div></div>
                                <div class="caproq-summary-card"><div class="caproq-summary-label">Setor</div><div class="caproq-summary-value">{escape(setor_solicitante_resumo)}</div></div>
                                <div class="caproq-summary-card"><div class="caproq-summary-label">Fornecedor</div><div class="caproq-summary-value">{escape(fornecedor_resumo)}</div></div>
                                <div class="caproq-summary-card"><div class="caproq-summary-label">Modalidade</div><div class="caproq-summary-value">{escape(tipo_resumo)}</div></div>
                            </div>
                            <div class="caproq-decision-box"><b>Status do fluxo técnico:</b> {status_seguro}</div>
                            """,
                            unsafe_allow_html=True,
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

                        st.markdown(
                            '<div class="caproq-section-title">📋 Panorama das alçadas técnicas</div>',
                            unsafe_allow_html=True,
                        )
                        cards_votos = []
                        for _, info in ALCADAS_INFO.items():
                            voto_atual = str(row.get(info["coluna_sheets"], "Pendente"))
                            voto_lower = voto_atual.lower()
                            if "aprovar" in voto_lower and "ressalva" not in voto_lower:
                                rotulo_voto, icone_voto = "Aprovado", "●"
                                fundo_voto, borda_voto = "rgba(0,141,76,.11)", "rgba(0,141,76,.32)"
                            elif "ressalva" in voto_lower:
                                rotulo_voto, icone_voto = "Com ressalva", "●"
                                fundo_voto, borda_voto = "rgba(230,162,60,.13)", "rgba(230,162,60,.38)"
                            elif "reprovar" in voto_lower:
                                rotulo_voto, icone_voto = "Reprovado", "●"
                                fundo_voto, borda_voto = "rgba(217,48,37,.11)", "rgba(217,48,37,.34)"
                            else:
                                rotulo_voto, icone_voto = "Pendente", "○"
                                fundo_voto, borda_voto = "rgba(128,128,128,.08)", "rgba(128,128,128,.25)"
                            cards_votos.append(
                                f'<div class="caproq-score-card" style="--score-bg:{fundo_voto};--score-border:{borda_voto}">'
                                f'<div class="caproq-score-label">{escape(info["label"])}</div>'
                                f'<div class="caproq-score-status">{icone_voto} {rotulo_voto}</div></div>'
                            )
                        st.markdown(
                            '<div class="caproq-score-grid">' + ''.join(cards_votos) + '</div>',
                            unsafe_allow_html=True,
                        )

                        with st.expander(
                            "💬 Pareceres completos das alçadas", expanded=False
                        ):
                            for _, info in ALCADAS_INFO.items():
                                voto_detalhado = valor_seguro(
                                    row.get(info["coluna_sheets"], "Pendente")
                                )
                                st.markdown(
                                    f'<div class="caproq-parecer-card">'
                                    f'<div class="caproq-parecer-head">{escape(info["label"])}</div>'
                                    f'<div class="caproq-parecer-text">{escape(voto_detalhado)}</div>'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )

                        if eh_produto_teste:
                            st.markdown("---")
                            st.markdown(
                                '<div class="caproq-section-title">🧪 Avaliação técnica do produto de teste</div>',
                                unsafe_allow_html=True,
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

                        st.markdown(
                            '<div class="caproq-section-title">✅ Validações de encerramento</div>',
                            unsafe_allow_html=True,
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

                        st.markdown(
                            '<div class="caproq-section-title">🛡️ Deliberação administrativa final</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            '<div class="caproq-decision-box"><b>Decisão institucional</b><br><span style="opacity:.75">Considere os pareceres técnicos e registre abaixo o veredito que encerrará oficialmente o chamado.</span></div>',
                            unsafe_allow_html=True,
                        )
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
    st.markdown("""
    <style>
    .caproq-request-hero {
        padding: 26px 28px;
        border: 1px solid color-mix(in srgb, #005691 24%, transparent);
        border-radius: 18px;
        background: linear-gradient(135deg, color-mix(in srgb, #005691 12%, transparent), color-mix(in srgb, #ffffff 94%, transparent));
        margin: 4px 0 18px 0;
        box-shadow: 0 12px 30px rgba(0, 86, 145, .08);
    }
    .caproq-request-kicker {
        color: #005691;
        font-size: .78rem;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
        margin-bottom: 7px;
    }
    .caproq-request-title {
        font-size: clamp(1.55rem, 2.8vw, 2.35rem);
        font-weight: 800;
        line-height: 1.12;
        margin: 0;
    }
    .caproq-request-subtitle {
        margin: 9px 0 0 0;
        opacity: .76;
        max-width: 760px;
        line-height: 1.55;
    }
    .caproq-steps {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 8px;
        margin: 0 0 18px 0;
    }
    .caproq-step {
        min-height: 68px;
        border: 1px solid color-mix(in srgb, #005691 18%, transparent);
        border-radius: 13px;
        padding: 10px 9px;
        background: color-mix(in srgb, #005691 5%, transparent);
        display: flex;
        gap: 8px;
        align-items: center;
    }
    .caproq-step-number {
        min-width: 27px;
        height: 27px;
        border-radius: 50%;
        background: #005691;
        color: white;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: .78rem;
        font-weight: 800;
    }
    .caproq-step-label {
        font-size: .78rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .caproq-form-section {
        margin: 22px 0 13px 0;
        padding: 15px 17px;
        border-left: 5px solid #005691;
        border-radius: 0 13px 13px 0;
        background: color-mix(in srgb, #005691 7%, transparent);
    }
    .caproq-form-section-title {
        font-size: 1.03rem;
        font-weight: 800;
        margin: 0;
    }
    .caproq-form-section-help {
        font-size: .84rem;
        opacity: .72;
        margin-top: 4px;
    }
    .caproq-required-note {
        margin: 4px 0 13px 0;
        font-size: .82rem;
        opacity: .7;
    }
    .caproq-test-banner {
        padding: 16px 18px;
        border-radius: 14px;
        background: color-mix(in srgb, #e6a23c 13%, transparent);
        border: 1px solid color-mix(in srgb, #e6a23c 32%, transparent);
        margin-bottom: 15px;
    }
    .caproq-test-title {font-weight: 800; margin-bottom: 4px;}
    .caproq-test-copy {font-size: .88rem; opacity: .78;}
    div[data-testid="stForm"] {
        border: 1px solid color-mix(in srgb, #005691 17%, transparent);
        border-radius: 18px;
        padding: 1.05rem 1.15rem 1.2rem 1.15rem;
        background: color-mix(in srgb, var(--background-color, #ffffff) 97%, #005691 3%);
        box-shadow: 0 12px 28px rgba(0, 86, 145, .05);
    }
    div[data-testid="stFileUploader"] {
        border-radius: 14px;
        padding: 4px 8px;
        background: color-mix(in srgb, #005691 4%, transparent);
    }
    @media (max-width: 900px) {
        .caproq-steps {grid-template-columns: repeat(3, minmax(0, 1fr));}
    }
    @media (max-width: 560px) {
        .caproq-request-hero {padding: 21px 18px;}
        .caproq-steps {grid-template-columns: repeat(2, minmax(0, 1fr));}
        div[data-testid="stForm"] {padding: .75rem;}
    }
    </style>
    <div class="caproq-request-hero">
        <div class="caproq-request-kicker">Hospital Moinhos de Vento · CAPROQ</div>
        <h1 class="caproq-request-title">Solicitação de padronização de produtos químicos</h1>
        <p class="caproq-request-subtitle">Registre as informações do produto, sua utilização e os documentos técnicos para iniciar o fluxo de avaliação pelas alçadas responsáveis.</p>
    </div>
    <div class="caproq-steps">
        <div class="caproq-step"><span class="caproq-step-number">1</span><span class="caproq-step-label">Classificação</span></div>
        <div class="caproq-step"><span class="caproq-step-number">2</span><span class="caproq-step-label">Dados do produto</span></div>
        <div class="caproq-step"><span class="caproq-step-number">3</span><span class="caproq-step-label">Processos e uso</span></div>
        <div class="caproq-step"><span class="caproq-step-number">4</span><span class="caproq-step-label">Impacto e segurança</span></div>
        <div class="caproq-step"><span class="caproq-step-number">5</span><span class="caproq-step-label">Documentos</span></div>
        <div class="caproq-step"><span class="caproq-step-number">6</span><span class="caproq-step-label">Envio</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    tab_novo, tab_status = st.tabs(["📝 Nova solicitação", "📚 Meus chamados"])
    
    with tab_novo:
        st.markdown("<div class='caproq-required-note'>Os campos identificados com <b>*</b> são obrigatórios.</div>", unsafe_allow_html=True)
        
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
            
            st.markdown("""
            <div class="caproq-form-section">
                <div class="caproq-form-section-title">🧭 Classificação inicial</div>
                <div class="caproq-form-section-help">Informe se o item seguirá o fluxo padrão ou se será avaliado como produto de teste ou piloto.</div>
            </div>
            """, unsafe_allow_html=True)
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
                    secoes_visuais = {
                        "Dados do Produto": ("📦", "Dados do produto", "Descreva o item, a apresentação, o fabricante e a finalidade de uso."),
                        "Processos e Dependências": ("⚙️", "Processos e dependências", "Explique o processo atual e eventuais equipamentos ou insumos relacionados."),
                        "Avaliação de Impacto e Segurança": ("🛡️", "Impacto e segurança", "Avalie os ganhos esperados e os possíveis impactos assistenciais, ocupacionais e ambientais."),
                        "Studies e Viabilidade": ("📊", "Estudos e viabilidade", "Informe a existência de evidências científicas e análises de custo-efetividade."),
                    }
                    icone_secao, titulo_secao, ajuda_secao = secoes_visuais.get(
                        secao_atual,
                        ("📌", secao_atual, "Preencha as informações desta etapa."),
                    )
                    st.markdown(
                        f"""
                        <div class="caproq-form-section">
                            <div class="caproq-form-section-title">{icone_secao} {titulo_secao}</div>
                            <div class="caproq-form-section-help">{ajuda_secao}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                
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
            st.markdown("""
            <div class="caproq-form-section">
                <div class="caproq-form-section-title">📎 Documentos técnicos</div>
                <div class="caproq-form-section-help">Anexe a FDS obrigatória e, quando disponíveis, registro ANVISA, laudos, ficha técnica, catálogo e estudos.</div>
            </div>
            """, unsafe_allow_html=True)
            
            arquivos_gerais = st.file_uploader("Arquivos anexados (Registro ANVISA, Laudo Técnico, Ficha Técnico, Fabricante):", accept_multiple_files=True, key=f"up_arquivos_gerais_{v}")
            fds_obrigatorio = st.file_uploader("Anexar FDS (Obrigatório) *", key=f"up_fds_obrigatorio_{v}")
            arquivo_estudos = st.file_uploader("Anexo arquivo de estudos científicos e de custo-efetividade:", key=f"up_arquivo_estudos_{v}")
    
            st.markdown("""
            <div class="caproq-form-section">
                <div class="caproq-form-section-title">✅ Revisão e envio</div>
                <div class="caproq-form-section-help">Revise as respostas e os anexos. Após o envio, o chamado será encaminhado automaticamente às alçadas técnicas.</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botão de envio padrão - Aciona a validação em 1 clique
            enviar_formulario = st.form_submit_button("Enviar solicitação para avaliação", use_container_width=True, type="primary")
            
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
                st.markdown("""
                <div class="caproq-test-banner">
                    <div class="caproq-test-title">🧪 Informações complementares do produto de teste</div>
                    <div class="caproq-test-copy">O formulário principal foi validado. Complete os dados operacionais e de contato abaixo para concluir o envio.</div>
                </div>
                """, unsafe_allow_html=True)
                
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
                            "às áreas técnicas. Acesse o painel para mais informações."
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
        st.markdown("""
        <div class="caproq-form-section" style="margin-top:8px;">
            <div class="caproq-form-section-title">📚 Status e histórico dos meus chamados</div>
            <div class="caproq-form-section-help">Acompanhe o andamento das avaliações técnicas, os pareceres registrados e a decisão final de cada solicitação.</div>
        </div>
        """, unsafe_allow_html=True)
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
