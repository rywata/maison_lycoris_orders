import streamlit as st
from historico_pedidos import renderizar_historico
from pedidos import renderizar_novo_pedido
from estoque import renderizar_estoque
from producao import renderizar_producao
from database import Database
from datetime import date
import pandas as pd
import os
import time

# --- SEGURANÇA (LOGIN) ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["usernames"].get(st.session_state["username"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Acesso Restrito - Maison Lycoris")
        st.text_input("Usuário", key="username", autocomplete="username")
        st.text_input("Senha", type="password", key="password", autocomplete="current-password")
        st.button("Entrar", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 Acesso Restrito - Maison Lycoris")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar", on_click=password_entered)
        st.error("😕 Usuário ou senha incorretos.")
        return False
    return True

if not check_password():
    st.stop()

# --- LOGO ---
def carregar_logo():
    caminho_logo = "assets/logo_black2.png"
    if os.path.exists(caminho_logo):
        st.sidebar.image(caminho_logo, width=250)
    else:
        st.sidebar.title("Maison Lycoris")

carregar_logo()

# --- TELA INÍCIO ---
@st.cache_data(ttl=60)
def carregar_dados_inicio():
    db = Database()
    return db.pedidos()

def tela_inicio():
    st.title("🥐 Maison Lycoris - Gestão Artesanal")
    st.write(f"Bem vindo! Hoje é dia {date.today().strftime('%d/%m/%Y')}")

    df = carregar_dados_inicio()
    hoje = date.today()

    if df.empty:
        st.warning("Nenhum dado encontrado.")
        return

    df.columns = [c.lower() for c in df.columns]
    df['data_pedido'] = pd.to_datetime(df['data_pedido'], errors='coerce').dt.date
    df['data_entrega'] = pd.to_datetime(df['data_entrega'], errors='coerce').dt.date
    df['total_liquido'] = pd.to_numeric(df['total_liquido'], errors='coerce').fillna(0)

    # Métricas
    df_hoje = df[df['data_pedido'] == hoje]
    vendas_hoje = df_hoje['total_liquido'].sum()
    entregas_futuras = len(df[df['data_entrega'] >= hoje]['id_pedido'].unique())

    # Estoque crítico
    db = Database()
    df_critico = db.estoque_critico()

    col1, col2, col3 = st.columns(3)
    col1.metric("Vendas Hoje", f"R$ {vendas_hoje:,.2f}")
    col2.metric("Entregas Pendentes", entregas_futuras)
    col3.metric("Estoque Crítico", len(df_critico),
                delta="itens abaixo do mínimo" if not df_critico.empty else "OK",
                delta_color="inverse" if not df_critico.empty else "normal")

    st.divider()

    # Cronograma de produção
    st.subheader("Cronograma de Produção")
    pedidos_futuros = df[df['data_entrega'] >= hoje].sort_values('data_entrega')

    if not pedidos_futuros.empty:
        view = pedidos_futuros[['data_entrega', 'nome_cliente', 'produto', 'quantidade']].copy()
        view.columns = ['Data Entrega', 'Cliente', 'Produto', 'Quantidade']
        st.dataframe(view, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum pedido agendado para os próximos dias.")

    # Alertas de validade
    df_validade = db.alertas_validade()
    if not df_validade.empty:
        st.divider()
        st.subheader("⚠️ Alertas de Validade")
        st.warning(f"{len(df_validade)} item(ns) vencendo nos próximos 7 dias")
        st.dataframe(df_validade, use_container_width=True, hide_index=True)

# --- NAVEGAÇÃO ---
if 'aba_atual' not in st.session_state:
    st.session_state.aba_atual = "Início"

def ir_para(nome_aba):
    st.session_state.aba_atual = nome_aba

st.sidebar.button("🏠 Início", on_click=ir_para, args=("Início",), use_container_width=True)
st.sidebar.button("📝 Novo Pedido", on_click=ir_para, args=("Novo Pedido",), use_container_width=True)
st.sidebar.button("📜 Histórico", on_click=ir_para, args=("Histórico",), use_container_width=True)
st.sidebar.button("📦 Estoque", on_click=ir_para, args=("Estoque",), use_container_width=True)
st.sidebar.button("🏗️ Produção", on_click=ir_para, args=("Produção",), use_container_width=True)
st.sidebar.button("💰 Faturamento", on_click=ir_para, args=("Faturamento",), use_container_width=True)

# --- ROTEAMENTO ---
if st.session_state.aba_atual == "Início":
    tela_inicio()
elif st.session_state.aba_atual == "Novo Pedido":
    renderizar_novo_pedido()
elif st.session_state.aba_atual == "Histórico":
    renderizar_historico()
elif st.session_state.aba_atual == "Estoque":
    renderizar_estoque()
elif st.session_state.aba_atual == "Produção":
    renderizar_producao()
elif st.session_state.aba_atual == "Faturamento":
    st.title("💰 Faturamento")
    st.info("Em desenvolvimento.")