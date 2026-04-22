import streamlit as st
import pandas as pd
from datetime import datetime
from logic_pedidos import Carrinho
from database import Database, salvar_pedido

# --- 0. SEGURANÇA (LOGIN) ---
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

# --- 1. CONFIGURAÇÃO GOOGLE SHEETS (Via Database) ---
@st.cache_resource
def iniciar_conexao():
    db = Database() 
    return db.conectar_aba("Controle", "Pedidos")

try:
    aba_pedidos = iniciar_conexao()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- 2. ESTADO E DADOS ---
if 'carrinho' not in st.session_state: st.session_state.carrinho = []
if 'pedido_enviado' not in st.session_state: st.session_state.pedido_enviado = False

cardapio = {
    "Pão de Leite": 15.0, "Pão Integral": 17.0, "Pão Semi Integral": 17.0, "Shokupan": 17.0,
    "Pastel de Nata": 7.0, "Pastel de Maçã": 7.0, "Pastel de Ricota com Ervas Finas": 7.0, "Pastel de Frango com Parmesão": 7.0
}
codigo_pasteis = [k for k in cardapio.keys() if "Pastel" in k]

# --- 3. INTERFACE ---
st.set_page_config(page_title="Maison Lycoris - Pedidos", page_icon="🥐", layout="centered")

if st.session_state.pedido_enviado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center;">
            <span style="color: #28a745; font-size: 120px; font-weight: bold;">✓</span>
            <h2 style="margin-top: 10px;">Pedido Confirmado!</h2>
            <p>Os dados já estão na planilha da Maison Lycoris.</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Criar Novo Pedido", use_container_width=True):
        st.session_state.carrinho = []
        st.session_state.pedido_enviado = False
        st.rerun()
    st.stop()

st.title("🥐 Maison Lycoris - Sistema de Pedidos")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        nome_cliente = st.text_input("Nome do Cliente", placeholder="Ex: Zé Bedeu")
    with col2:
        data_sel = st.date_input("Data de Entrega", value=datetime.now(), format="DD/MM/YYYY")

st.divider()
st.subheader("Adicionar Produtos")
c_prod, c_qtd, c_add = st.columns([3, 1, 1])

with c_prod:
    produto = st.selectbox("Selecione o Produto", list(cardapio.keys()))
with c_qtd:
    qtd = st.number_input("Qtd", min_value=1, step=1)
with c_add:
    st.write(" ")
    if st.button("➕ Adicionar"):
        if nome_cliente:
            meu_carrinho_temp = Carrinho(st.session_state.carrinho, codigo_pasteis)
            try:
                meu_carrinho_temp.adicionar_item(produto, qtd, cardapio[produto])
                #Validação das regras
                st.session_state.carrinho = meu_carrinho_temp.itens
                st.toast(f"{produto} adicionado!", icon="🛒")
            except ValueError as e:
                st.error(f"⚠️ Erro: {e}")
        else:
            st.warning("Preencha o nome do cliente!")

# --- 4. CARRINHO (Via Logic) ---
if st.session_state.carrinho:
    st.divider()
    
    meu_carrinho = Carrinho(st.session_state.carrinho, codigo_pasteis)
    
    for item in meu_carrinho.itens:
        st.write(f"**{item['qtd']}x {item['produto']}** - R$ {item['subtotal']:.2f}")

    st.divider()
    # ACESSO ÀS PROPERTIES
    if meu_carrinho.desconto_total > 0:
        st.write(f"Subtotal Bruto: R$ {meu_carrinho.total_bruto:.2f}")
        st.write(f"🎁 Desconto Combo: -R$ {meu_carrinho.desconto_total:.2f}")
    
    st.metric("Total a Pagar", f"R$ {meu_carrinho.total_final:.2f}")

    # --- 5. FINALIZAÇÃO ---
    if st.button("🚀 FINALIZAR E ENVIAR PEDIDO", use_container_width=True):
        id_p = datetime.now().strftime("%Y%m%d%H%M")
        dt_in = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        dados_para_planilha = []
        for item in meu_carrinho.itens:
            d_i = float((item['subtotal'] * 0.15) if (meu_carrinho.tem_desconto and item['produto'] in codigo_pasteis) else 0.0)
            bruto = float(item['subtotal'])
            
            dados_para_planilha.append([
                id_p, 
                nome_cliente, 
                data_sel.isoformat(), 
                item['produto'], 
                int(item['qtd']), 
                bruto, 
                d_i, 
                float(bruto - d_i), 
                dt_in
            ])
        
        if salvar_pedido(aba_pedidos, dados_para_planilha):
            st.session_state.pedido_enviado = True
            st.rerun()
        else:
            st.error("Erro ao salvar no banco de dados.")
