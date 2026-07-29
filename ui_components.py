"""Componentes visuais do CAPROQ.

Responsividade, tema, CSS e outros.
"""

from __future__ import annotations

from html import escape
from typing import Literal

import streamlit as st


def load_global_css() -> None:
    """Carrega todos os estilos globais do CAPROQ."""
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

    # ------------------------------------------------------------------------------
    # Componentes globais de feedback: estados vazios, alertas e mensagens
    # ------------------------------------------------------------------------------
    st.markdown("""
    <style>
    .caproq-feedback {display:flex;gap:14px;align-items:flex-start;padding:15px 17px;margin:10px 0 14px;border-radius:14px;border:1px solid;box-shadow:0 8px 24px rgba(15,23,42,.05)}
    .caproq-feedback__icon {width:38px;height:38px;min-width:38px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:1.15rem}
    .caproq-feedback__title {font-weight:800;line-height:1.25;margin:1px 0 4px}
    .caproq-feedback__text {font-size:.92rem;line-height:1.5;opacity:.82}
    .caproq-feedback--success {background:rgba(22,163,74,.08);border-color:rgba(22,163,74,.24)}
    .caproq-feedback--success .caproq-feedback__icon {background:rgba(22,163,74,.14)}
    .caproq-feedback--warning {background:rgba(245,158,11,.09);border-color:rgba(245,158,11,.27)}
    .caproq-feedback--warning .caproq-feedback__icon {background:rgba(245,158,11,.16)}
    .caproq-feedback--error {background:rgba(220,38,38,.08);border-color:rgba(220,38,38,.24)}
    .caproq-feedback--error .caproq-feedback__icon {background:rgba(220,38,38,.14)}
    .caproq-feedback--info {background:rgba(0,86,145,.08);border-color:rgba(0,86,145,.23)}
    .caproq-feedback--info .caproq-feedback__icon {background:rgba(0,86,145,.14)}
    .caproq-empty-global {text-align:center;padding:34px 22px;margin:14px 0;border-radius:16px;border:1px dashed rgba(127,127,127,.34);background:rgba(127,127,127,.045)}
    .caproq-empty-global__icon {font-size:2.25rem;margin-bottom:8px}
    .caproq-empty-global__title {font-size:1.05rem;font-weight:800;margin-bottom:5px}
    .caproq-empty-global__text {font-size:.92rem;opacity:.7;line-height:1.5;max-width:620px;margin:0 auto}
    @media(max-width:640px){.caproq-feedback{padding:13px 14px}.caproq-feedback__icon{width:34px;height:34px;min-width:34px}.caproq-empty-global{padding:27px 16px}}
    </style>
    """, unsafe_allow_html=True)


    # ------------------------------------------------------------------------------
    # Design System CAPROQ — padronização final e global do CSS
    # ------------------------------------------------------------------------------
    st.markdown("""
    <style>
    :root {
        --caproq-primary: #005691;
        --caproq-primary-hover: #003d66;
        --caproq-primary-soft: rgba(0, 86, 145, 0.09);
        --caproq-primary-border: rgba(0, 86, 145, 0.22);
        --caproq-success: #16803c;
        --caproq-warning: #b86b00;
        --caproq-danger: #bd2525;
        --caproq-info: #005691;
        --caproq-radius-sm: 8px;
        --caproq-radius-md: 12px;
        --caproq-radius-lg: 16px;
        --caproq-shadow-sm: 0 2px 8px rgba(15, 23, 42, 0.05);
        --caproq-shadow-md: 0 10px 28px rgba(15, 23, 42, 0.07);
        --caproq-transition: 160ms ease;
    }

    /* Estrutura e ritmo vertical */
    [data-testid="stAppViewContainer"] .main .block-container {
        max-width: 1480px;
        padding-top: 1.15rem;
        padding-bottom: 3rem;
    }
    [data-testid="stVerticalBlock"] {
        gap: 0.82rem;
    }
    [data-testid="stHorizontalBlock"] {
        gap: 0.9rem;
    }

    /* Tipografia global */
    html, body, [class*="css"] {
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
    }
    h1, h2, h3, h4, h5, h6 {
        letter-spacing: -0.018em;
        line-height: 1.2;
    }
    h1 { font-size: clamp(1.7rem, 2.2vw, 2.35rem) !important; }
    h2 { font-size: clamp(1.35rem, 1.8vw, 1.8rem) !important; }
    h3 { font-size: clamp(1.08rem, 1.35vw, 1.34rem) !important; }
    p, li, label { line-height: 1.5; }
    small, .stCaption { opacity: 0.74; }

    /* Links */
    a {
        color: var(--caproq-primary);
        text-underline-offset: 3px;
        transition: color var(--caproq-transition);
    }
    a:hover { color: var(--caproq-primary-hover); }

    /* Campos de formulário */
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input {
        border-radius: var(--caproq-radius-sm) !important;
        border-color: rgba(127, 127, 127, 0.28) !important;
        transition: border-color var(--caproq-transition), box-shadow var(--caproq-transition) !important;
    }
    [data-baseweb="input"] > div:focus-within,
    [data-baseweb="textarea"] > div:focus-within,
    [data-baseweb="select"] > div:focus-within {
        border-color: var(--caproq-primary) !important;
        box-shadow: 0 0 0 3px rgba(0, 86, 145, 0.12) !important;
    }
    [data-testid="stTextInput"] label,
    [data-testid="stTextArea"] label,
    [data-testid="stSelectbox"] label,
    [data-testid="stMultiSelect"] label,
    [data-testid="stRadio"] label,
    [data-testid="stCheckbox"] label,
    [data-testid="stFileUploader"] label,
    [data-testid="stDateInput"] label,
    [data-testid="stNumberInput"] label {
        font-weight: 650 !important;
    }

    /* Botões primários, secundários e download */
    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {
        min-height: 2.7rem;
        border-radius: 9px !important;
        font-weight: 700 !important;
        letter-spacing: 0.005em;
        transition: transform var(--caproq-transition), box-shadow var(--caproq-transition), background var(--caproq-transition), border-color var(--caproq-transition) !important;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.10);
    }
    .stButton > button[kind="primary"],
    [data-testid="stFormSubmitButton"] > button[kind="primary"] {
        background: var(--caproq-primary) !important;
        border-color: var(--caproq-primary) !important;
        color: #fff !important;
    }
    .stButton > button[kind="primary"]:hover,
    [data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
        background: var(--caproq-primary-hover) !important;
        border-color: var(--caproq-primary-hover) !important;
    }
    .stButton > button:focus-visible,
    .stDownloadButton > button:focus-visible {
        outline: 3px solid rgba(0, 86, 145, 0.25) !important;
        outline-offset: 2px;
    }

    /* Abas */
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 0.25rem;
        border-bottom: 1px solid rgba(127, 127, 127, 0.20);
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        min-height: 2.85rem;
        padding: 0.55rem 0.9rem;
        border-radius: 9px 9px 0 0;
        font-weight: 680;
        transition: background var(--caproq-transition), color var(--caproq-transition);
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
        background: var(--caproq-primary-soft);
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--caproq-primary) !important;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: var(--caproq-primary) !important;
        height: 3px;
        border-radius: 999px 999px 0 0;
    }

    /* Expanders */
    [data-testid="stExpander"] {
        border: 1px solid rgba(127, 127, 127, 0.20) !important;
        border-radius: var(--caproq-radius-md) !important;
        overflow: hidden;
        box-shadow: var(--caproq-shadow-sm);
        transition: border-color var(--caproq-transition), box-shadow var(--caproq-transition);
    }
    [data-testid="stExpander"]:hover {
        border-color: var(--caproq-primary-border) !important;
        box-shadow: var(--caproq-shadow-md);
    }
    [data-testid="stExpander"] details > summary {
        min-height: 3.25rem;
        padding: 0.68rem 0.9rem !important;
        font-weight: 720;
    }
    [data-testid="stExpander"] details[open] > summary {
        background: var(--caproq-primary-soft);
        border-bottom: 1px solid var(--caproq-primary-border);
    }

    /* Métricas */
    div[data-testid="stMetric"] {
        min-height: 106px;
        padding: 1rem 1.05rem;
        border: 1px solid rgba(127, 127, 127, 0.20);
        border-radius: var(--caproq-radius-md);
        background: var(--secondary-background-color);
        box-shadow: var(--caproq-shadow-sm);
    }
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
        font-weight: 680;
        opacity: 0.76;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-weight: 820;
        letter-spacing: -0.025em;
    }

    /* Uploads */
    [data-testid="stFileUploaderDropzone"] {
        border: 1.5px dashed rgba(0, 86, 145, 0.34) !important;
        border-radius: var(--caproq-radius-md) !important;
        background: var(--caproq-primary-soft) !important;
        transition: border-color var(--caproq-transition), background var(--caproq-transition);
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: var(--caproq-primary) !important;
        background: rgba(0, 86, 145, 0.13) !important;
    }

    /* Tabelas e dataframes */
    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        border: 1px solid rgba(127, 127, 127, 0.20);
        border-radius: var(--caproq-radius-md);
        overflow: hidden;
        box-shadow: var(--caproq-shadow-sm);
    }
    [data-testid="stDataFrame"] [role="columnheader"] {
        font-weight: 720 !important;
    }

    /* Alertas nativos remanescentes */
    [data-testid="stAlert"] {
        border-radius: var(--caproq-radius-md) !important;
        border-width: 1px !important;
        box-shadow: var(--caproq-shadow-sm);
    }

    /* Elementos de navegação e separadores */
    hr {
        border: 0 !important;
        border-top: 1px solid rgba(127, 127, 127, 0.20) !important;
        margin: 1.2rem 0 !important;
    }
    [data-testid="stSidebar"] hr { margin: 0.8rem 0 !important; }

    /* Sidebar: acabamento sem alterar a estrutura existente */
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(127, 127, 127, 0.16);
    }
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
    }

    /* Scrollbars discretas */
    * { scrollbar-width: thin; scrollbar-color: rgba(127,127,127,.38) transparent; }
    *::-webkit-scrollbar { width: 7px; height: 7px; }
    *::-webkit-scrollbar-track { background: transparent; }
    *::-webkit-scrollbar-thumb { background: rgba(127,127,127,.34); border-radius: 999px; }
    *::-webkit-scrollbar-thumb:hover { background: rgba(127,127,127,.50); }

    /* Foco acessível */
    *:focus-visible {
        outline-color: var(--caproq-primary);
        outline-offset: 2px;
    }

    /* Tema escuro */
    @media (prefers-color-scheme: dark) {
        :root {
            --caproq-primary: #4ba3db;
            --caproq-primary-hover: #73b9e5;
            --caproq-primary-soft: rgba(75, 163, 219, 0.12);
            --caproq-primary-border: rgba(75, 163, 219, 0.28);
            --caproq-shadow-sm: 0 2px 9px rgba(0, 0, 0, 0.18);
            --caproq-shadow-md: 0 12px 30px rgba(0, 0, 0, 0.24);
        }
    }

    /* Responsividade */
    @media (max-width: 900px) {
        [data-testid="stAppViewContainer"] .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        div[data-testid="stMetric"] { min-height: 96px; }
    }
    @media (max-width: 640px) {
        [data-testid="stAppViewContainer"] .main .block-container {
            padding-top: 0.75rem;
            padding-left: 0.72rem;
            padding-right: 0.72rem;
        }
        [data-testid="stHorizontalBlock"] { gap: 0.55rem; }
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            overflow-x: auto;
            flex-wrap: nowrap;
            scrollbar-width: none;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            white-space: nowrap;
            padding-inline: 0.72rem;
        }
        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button {
            min-height: 2.8rem;
        }
    }

    /* Respeito à preferência de movimento reduzido */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            scroll-behavior: auto !important;
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    load_screen_css()


def load_login_css() -> None:
    """Aplica ajustes visuais exclusivos da tela de autenticação."""
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


def load_screen_css() -> None:
    """Carrega estilos específicos das telas consolidadas do CAPROQ."""
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

.caproq-history-hero {
    padding: 1.3rem 1.45rem;
    border: 1px solid rgba(0, 86, 145, .18);
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(0, 86, 145, .13), rgba(0, 86, 145, .025));
    margin: .15rem 0 1rem;
}
.caproq-history-kicker {
    margin: 0 0 .3rem;
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .13em;
    text-transform: uppercase;
    opacity: .7;
}
.caproq-history-title {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 850;
    line-height: 1.2;
}
.caproq-history-subtitle {
    margin: .4rem 0 0;
    opacity: .76;
    line-height: 1.5;
}
.caproq-history-filter-shell {
    padding: .95rem 1rem .3rem;
    border: 1px solid rgba(128, 128, 128, .18);
    border-radius: 16px;
    background: rgba(128, 128, 128, .035);
    margin-bottom: .9rem;
}
.caproq-history-summary {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .7rem;
    margin: .25rem 0 1rem;
}
.caproq-history-summary-card {
    border: 1px solid rgba(128, 128, 128, .17);
    border-radius: 15px;
    padding: .82rem .9rem;
    background: rgba(128, 128, 128, .025);
}
.caproq-history-summary-label {
    margin: 0;
    font-size: .72rem;
    font-weight: 750;
    text-transform: uppercase;
    letter-spacing: .07em;
    opacity: .64;
}
.caproq-history-summary-value {
    margin: .16rem 0 0;
    font-size: 1.28rem;
    line-height: 1.15;
    font-weight: 850;
}
.caproq-history-request {
    border: 1px solid rgba(128, 128, 128, .17);
    border-radius: 15px;
    padding: .9rem 1rem;
    background: rgba(128, 128, 128, .025);
    margin: .2rem 0 .85rem;
}
.caproq-history-request-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .75rem;
}
.caproq-history-field-label {
    font-size: .7rem;
    font-weight: 780;
    text-transform: uppercase;
    letter-spacing: .06em;
    opacity: .6;
    margin-bottom: .18rem;
}
.caproq-history-field-value {
    font-size: .88rem;
    font-weight: 650;
    overflow-wrap: anywhere;
}
.caproq-history-scoreboard {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
    gap: .55rem;
    margin: .45rem 0 .85rem;
}
.caproq-history-area-card {
    border: 1px solid rgba(128, 128, 128, .16);
    border-radius: 13px;
    padding: .72rem .78rem;
    background: rgba(128, 128, 128, .025);
}
.caproq-history-area-name {
    font-size: .74rem;
    font-weight: 800;
    margin-bottom: .28rem;
    line-height: 1.25;
}
.caproq-history-badge {
    display: inline-flex;
    align-items: center;
    gap: .28rem;
    padding: .22rem .48rem;
    border-radius: 999px;
    font-size: .7rem;
    font-weight: 800;
}
.caproq-history-badge.approved { background: rgba(34, 197, 94, .14); color: #16823a; }
.caproq-history-badge.warning { background: rgba(245, 158, 11, .16); color: #9a6100; }
.caproq-history-badge.rejected { background: rgba(239, 68, 68, .14); color: #b42318; }
.caproq-history-badge.pending { background: rgba(107, 114, 128, .13); color: #60646c; }
.caproq-history-section-label {
    margin: .95rem 0 .45rem;
    font-size: .82rem;
    font-weight: 820;
    letter-spacing: .01em;
}
@media (max-width: 850px) {
    .caproq-history-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .caproq-history-request-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
    .caproq-history-hero { padding: 1.05rem 1rem; }
    .caproq-history-title { font-size: 1.28rem; }
    .caproq-history-summary { grid-template-columns: 1fr; }
    .caproq-history-request-grid { grid-template-columns: 1fr; }
}

.caproq-audit-hero {
    padding: 1.35rem 1.5rem;
    border: 1px solid rgba(49, 130, 206, .20);
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(0, 86, 145, .14), rgba(0, 86, 145, .025));
    margin: .15rem 0 1rem;
}
.caproq-audit-kicker {
    margin: 0 0 .32rem;
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .13em;
    text-transform: uppercase;
    opacity: .72;
}
.caproq-audit-title {
    margin: 0;
    font-size: 1.55rem;
    font-weight: 850;
    line-height: 1.2;
}
.caproq-audit-subtitle {
    margin: .42rem 0 0;
    opacity: .76;
    line-height: 1.5;
}
.caproq-audit-filter-shell {
    padding: .95rem 1rem .35rem;
    border: 1px solid rgba(128, 128, 128, .18);
    border-radius: 16px;
    background: rgba(128, 128, 128, .035);
    margin-bottom: .95rem;
}
.caproq-audit-summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .75rem;
    margin: .25rem 0 1rem;
}
.caproq-audit-summary-card {
    padding: .9rem 1rem;
    border: 1px solid rgba(128, 128, 128, .17);
    border-radius: 15px;
    background: rgba(128, 128, 128, .025);
}
.caproq-audit-summary-label {
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .08em;
    text-transform: uppercase;
    opacity: .62;
}
.caproq-audit-summary-value {
    margin-top: .2rem;
    font-size: 1.42rem;
    font-weight: 850;
}
.caproq-audit-meta-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .7rem;
    margin: .2rem 0 1rem;
}
.caproq-audit-meta-card {
    padding: .78rem .86rem;
    border-radius: 13px;
    border: 1px solid rgba(128, 128, 128, .16);
    background: rgba(128, 128, 128, .025);
}
.caproq-audit-meta-label {
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .07em;
    text-transform: uppercase;
    opacity: .6;
}
.caproq-audit-meta-value {
    margin-top: .22rem;
    font-size: .9rem;
    font-weight: 720;
    overflow-wrap: anywhere;
}
.caproq-audit-section-label {
    margin: 1rem 0 .55rem;
    font-size: .78rem;
    font-weight: 850;
    letter-spacing: .08em;
    text-transform: uppercase;
    opacity: .68;
}
.caproq-audit-event {
    position: relative;
    margin-left: .55rem;
    padding: .15rem 0 1rem 1.35rem;
    border-left: 2px solid rgba(128, 128, 128, .22);
}
.caproq-audit-event:last-child {
    padding-bottom: .25rem;
}
.caproq-audit-dot {
    position: absolute;
    left: -.48rem;
    top: .16rem;
    width: .84rem;
    height: .84rem;
    border-radius: 999px;
    border: 3px solid var(--background-color, #fff);
    background: #94a3b8;
}
.caproq-audit-dot.approved { background: #16a34a; }
.caproq-audit-dot.warning { background: #d97706; }
.caproq-audit-dot.rejected { background: #dc2626; }
.caproq-audit-dot.info { background: #0284c7; }
.caproq-audit-event-title {
    font-size: .92rem;
    font-weight: 820;
    margin: 0;
}
.caproq-audit-event-text {
    margin: .22rem 0 0;
    opacity: .78;
    line-height: 1.45;
    font-size: .86rem;
}
.caproq-audit-empty {
    padding: 1.25rem;
    border: 1px dashed rgba(128, 128, 128, .35);
    border-radius: 15px;
    text-align: center;
    opacity: .72;
}
@media (max-width: 900px) {
    .caproq-audit-summary-grid,
    .caproq-audit-meta-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
@media (max-width: 620px) {
    .caproq-audit-summary-grid,
    .caproq-audit-meta-grid {
        grid-template-columns: 1fr;
    }
    .caproq-audit-hero {
        padding: 1.05rem 1rem;
    }
}

.caproq-dashboard-hero {
    padding: 1.35rem 1.5rem;
    border: 1px solid rgba(49, 130, 206, .20);
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(0, 86, 145, .14), rgba(0, 86, 145, .025));
    margin: .15rem 0 1rem;
}
.caproq-dashboard-kicker {
    margin: 0 0 .32rem;
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .13em;
    text-transform: uppercase;
    opacity: .72;
}
.caproq-dashboard-title {
    margin: 0;
    font-size: 1.55rem;
    font-weight: 850;
    line-height: 1.2;
}
.caproq-dashboard-subtitle {
    margin: .42rem 0 0;
    opacity: .76;
    line-height: 1.5;
}
.caproq-filter-shell {
    padding: .95rem 1rem .35rem;
    border: 1px solid rgba(128, 128, 128, .18);
    border-radius: 16px;
    background: rgba(128, 128, 128, .035);
    margin-bottom: .95rem;
}
.caproq-dashboard-section {
    margin: 1.15rem 0 .58rem;
    font-size: .98rem;
    font-weight: 800;
    letter-spacing: -.01em;
}
.caproq-dashboard-card {
    border: 1px solid rgba(128, 128, 128, .17);
    border-radius: 16px;
    padding: .95rem 1rem;
    background: rgba(128, 128, 128, .025);
    min-height: 100%;
}
.caproq-dashboard-card-title {
    font-size: .88rem;
    font-weight: 800;
    margin: 0 0 .15rem;
}
.caproq-dashboard-card-caption {
    font-size: .76rem;
    opacity: .65;
    margin-bottom: .4rem;
}
.caproq-dashboard-note {
    padding: .8rem .95rem;
    border-radius: 14px;
    border: 1px solid rgba(0, 86, 145, .18);
    background: rgba(0, 86, 145, .055);
    line-height: 1.45;
    font-size: .86rem;
}
@media (max-width: 700px) {
    .caproq-dashboard-hero { padding: 1.05rem 1rem; }
    .caproq-dashboard-title { font-size: 1.3rem; }
}

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
    

        .caproq-my-hero {
            border: 1px solid rgba(0, 86, 145, .18);
            border-radius: 18px;
            padding: 22px 24px;
            margin: 8px 0 18px 0;
            background: linear-gradient(135deg, rgba(0,86,145,.12), rgba(0,86,145,.025));
        }
        .caproq-my-kicker {
            color: #005691;
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .10em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .caproq-my-title {
            font-size: 1.65rem;
            line-height: 1.15;
            font-weight: 800;
            margin: 0 0 7px 0;
        }
        .caproq-my-subtitle {
            opacity: .76;
            line-height: 1.55;
            max-width: 780px;
        }
        .caproq-my-metric {
            border: 1px solid rgba(128,128,128,.22);
            border-radius: 15px;
            padding: 15px 16px;
            min-height: 104px;
            background: rgba(255,255,255,.035);
        }
        .caproq-my-metric-label {
            opacity: .68;
            font-size: .77rem;
            font-weight: 700;
            letter-spacing: .04em;
            text-transform: uppercase;
        }
        .caproq-my-metric-value {
            font-size: 1.65rem;
            font-weight: 800;
            line-height: 1.2;
            margin-top: 7px;
        }
        .caproq-my-metric-help {
            opacity: .64;
            font-size: .80rem;
            margin-top: 4px;
        }
        .caproq-my-summary {
            display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));
            gap:10px;
            margin: 6px 0 16px 0;
        }
        .caproq-my-summary-item {
            border:1px solid rgba(128,128,128,.20);
            border-radius:12px;
            padding:12px 13px;
            background:rgba(255,255,255,.025);
        }
        .caproq-my-summary-label {
            opacity:.62;
            font-size:.72rem;
            font-weight:800;
            letter-spacing:.04em;
            text-transform:uppercase;
            margin-bottom:4px;
        }
        .caproq-my-summary-value {
            font-weight:700;
            line-height:1.35;
            overflow-wrap:anywhere;
        }
        .caproq-my-badge {
            display:inline-flex;
            align-items:center;
            gap:6px;
            border-radius:999px;
            padding:5px 10px;
            font-size:.76rem;
            font-weight:800;
            border:1px solid transparent;
        }
        .caproq-my-badge-blue {color:#005691;background:rgba(0,86,145,.12);border-color:rgba(0,86,145,.24)}
        .caproq-my-badge-green {color:#087443;background:rgba(8,116,67,.12);border-color:rgba(8,116,67,.24)}
        .caproq-my-badge-yellow {color:#9a6700;background:rgba(230,162,60,.14);border-color:rgba(230,162,60,.28)}
        .caproq-my-badge-red {color:#b3261e;background:rgba(217,48,37,.11);border-color:rgba(217,48,37,.23)}
        .caproq-my-badge-gray {color:inherit;background:rgba(128,128,128,.11);border-color:rgba(128,128,128,.20)}
        .caproq-my-stage {
            border:1px solid rgba(128,128,128,.20);
            border-radius:14px;
            padding:14px 15px;
            margin:10px 0 14px 0;
            background:rgba(255,255,255,.025);
        }
        .caproq-my-stage-title {font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.05em;opacity:.65;margin-bottom:5px}
        .caproq-my-stage-value {font-size:1.02rem;font-weight:800}
        .caproq-my-scoreboard {
            display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));
            gap:9px;
            margin:8px 0 14px 0;
        }
        .caproq-my-score {
            border-radius:12px;
            padding:11px 12px;
            border:1px solid rgba(128,128,128,.18);
            min-height:72px;
        }
        .caproq-my-score-label {font-size:.72rem;font-weight:800;line-height:1.25;margin-bottom:5px}
        .caproq-my-score-status {font-size:.75rem;font-weight:700;opacity:.83}
        .caproq-score-pending {background:rgba(128,128,128,.08)}
        .caproq-score-approved {background:rgba(8,116,67,.10);border-color:rgba(8,116,67,.24)}
        .caproq-score-warning {background:rgba(230,162,60,.12);border-color:rgba(230,162,60,.27)}
        .caproq-score-rejected {background:rgba(217,48,37,.09);border-color:rgba(217,48,37,.23)}
        .caproq-my-opinion {
            border-left:4px solid rgba(128,128,128,.35);
            border-radius:0 12px 12px 0;
            padding:12px 14px;
            margin:8px 0;
            background:rgba(128,128,128,.06);
        }
        .caproq-my-opinion-green {border-left-color:#087443;background:rgba(8,116,67,.075)}
        .caproq-my-opinion-yellow {border-left-color:#e6a23c;background:rgba(230,162,60,.085)}
        .caproq-my-opinion-red {border-left-color:#d93025;background:rgba(217,48,37,.065)}
        .caproq-my-opinion-area {font-weight:800;margin-bottom:5px}
        .caproq-my-opinion-text {opacity:.86;line-height:1.5;white-space:pre-wrap;overflow-wrap:anywhere}
        .caproq-empty-state {
            border:1px dashed rgba(128,128,128,.32);
            border-radius:16px;
            padding:34px 24px;
            text-align:center;
            margin-top:14px;
            background:rgba(128,128,128,.035);
        }
        .caproq-empty-icon {font-size:2.1rem;margin-bottom:8px}
        .caproq-empty-title {font-size:1.05rem;font-weight:800;margin-bottom:5px}
        .caproq-empty-text {opacity:.68;line-height:1.5}
        @media (max-width: 900px) {
            .caproq-my-summary,.caproq-my-scoreboard {grid-template-columns:repeat(2,minmax(0,1fr));}
        }
        @media (max-width: 560px) {
            .caproq-my-hero {padding:18px 16px}
            .caproq-my-title {font-size:1.35rem}
            .caproq-my-summary,.caproq-my-scoreboard {grid-template-columns:1fr;}
        }
        
        </style>
        """,
        unsafe_allow_html=True,
    )


FEEDBACK_CONFIG = {
    "success": ("✅", "Concluído"),
    "warning": ("⚠️", "Atenção"),
    "error": ("⛔", "Não foi possível concluir"),
    "info": ("ℹ️", "Informação"),
}

FeedbackKind = Literal["success", "warning", "error", "info"]


def render_feedback(message: object, kind: FeedbackKind = "info", title: str | None = None, icon: str | None = None) -> None:
    """Exibe uma mensagem padronizada de sucesso, aviso, erro ou informação."""
    normalized_kind = kind if kind in FEEDBACK_CONFIG else "info"
    default_icon, default_title = FEEDBACK_CONFIG[normalized_kind]
    html = (
        '<div class="caproq-feedback caproq-feedback--{kind}">'
        '<div class="caproq-feedback__icon">{icon}</div>'
        '<div><div class="caproq-feedback__title">{title}</div>'
        '<div class="caproq-feedback__text">{message}</div></div></div>'
    ).format(
        kind=normalized_kind,
        icon=escape(icon or default_icon),
        title=escape(title or default_title),
        message=escape(str(message)),
    )
    st.markdown(html, unsafe_allow_html=True)


def render_empty_state(title: str, message: str, icon: str = "📭") -> None:
    """Exibe um estado vazio padronizado."""
    html = (
        '<div class="caproq-empty-global">'
        '<div class="caproq-empty-global__icon">{icon}</div>'
        '<div class="caproq-empty-global__title">{title}</div>'
        '<div class="caproq-empty-global__text">{message}</div></div>'
    ).format(icon=escape(icon), title=escape(title), message=escape(message))
    st.markdown(html, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str, icon: str = "📋") -> None:
    """Renderiza um cabeçalho reutilizável no padrão CAPROQ."""
    st.markdown(
        f"""
        <div class="caproq-page-header">
            <div class="caproq-page-icon">{escape(icon)}</div>
            <div class="caproq-page-header-content">
                <h1>{escape(title)}</h1>
                <p>{escape(subtitle)}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, subtitle: str | None = None, icon: str = "") -> None:
    """Renderiza um título de seção simples e consistente."""
    subtitle_html = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="caproq-section-header">
            <h2>{escape(icon)} {escape(title)}</h2>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
