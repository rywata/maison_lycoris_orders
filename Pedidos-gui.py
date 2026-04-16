import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

# --- 1. CONFIGURAÇÃO GOOGLE SHEETS ---
@st.cache_resource
def conectar_google():
    try:
        info = dict(st.secrets["gcp_service_account"])
        raw_key = info["private_key"].strip()
        lines = [line.strip() for line in raw_key.split('\n')]
        info["private_key"] = '\n'.join(lines).replace("\\n", "\n")
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        return client.open("Controle").worksheet("Pedidos")
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

try:
    aba_pedidos = conectar_google()
except:
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

# TELA DE SUCESSO (Check Estático)
if st.session_state.pedido_enviado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    # Check Verde Gigante Centralizado
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
        # Seletor de data conforme solicitado
        data_sel = st.date_input("Data de Entrega", value=datetime.now(), format="DD/MM/YYYY")
        data_entrega = data_sel.strftime("%d/%m/%Y")

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
            st.session_state.carrinho.append({
                "produto": produto, "qtd": qtd, "preco_unitario": cardapio[produto], "subtotal": qtd * cardapio[produto]
            })
            st.toast(f"{produto} adicionado!", icon="🛒")
        else:
            st.warning("Preencha o nome do cliente!")

# --- 4. CARRINHO ---
if st.session_state.carrinho:
    st.divider()
    df = pd.DataFrame(st.session_state.carrinho)
    total_pasteis = sum(item['qtd'] for item in st.session_state.carrinho if item['produto'] in codigo_pasteis)
    tem_desc = total_pasteis >= 4
    
    for item in st.session_state.carrinho:
        st.write(f"**{item['qtd']}x {item['produto']}** - R$ {item['subtotal']:.2f}")

    total_bruto = df['subtotal'].sum()
    # Aplicando o desconto de 15% para o combo de 4 ou mais pastéis
    total_desc = sum(item['subtotal'] * 0.15 for item in st.session_state.carrinho if tem_desc and item['produto'] in codigo_pasteis)
    
    st.divider()
    if total_desc > 0:
        st.write(f"Subtotal Bruto: R$ {total_bruto:.2f}")
        st.write(f"🎁 Desconto Combo: -R$ {total_desc:.2f}")
    st.metric("Total a Pagar", f"R$ {total_bruto - total_desc:.2f}")

    if st.button("🚀 FINALIZAR E ENVIAR PEDIDO", use_container_width=True):
        id_p = datetime.now().strftime("%Y%m%d%H%M")
        dt_in = datetime.now().strftime("%d/%m/%Y %H:%M")
        dados = []
        for item in st.session_state.carrinho:
            d_i = (item['subtotal'] * 0.15) if (tem_desc and item['produto'] in codigo_pasteis) else 0.0
            dados.append([id_p, nome_cliente, data_sel.isoformat(), item['produto'], item['qtd'], item['subtotal'], d_i, item['subtotal']-d_i, datetime.now().isoformat()])
        
        try:
            aba_pedidos.append_rows(dados, value_input_option='USER_ENTERED')
            st.session_state.pedido_enviado = True
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
