import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from streamlit_lottie import st_lottie

# --- 0. ANIMAÇÃO LOTTIE INCORPORADA ---
# JSON de um check verde minimalista para garantir carregamento instantâneo e offline
lottie_check_json = json.loads("""
{
  "v": "5.5.7", "fr": 60, "ip": 0, "op": 60, "w": 100, "h": 100, "nm": "Check", "ddd": 0,
  "assets": [], "comps": [],
  "layers": [{
    "ddd": 0, "ind": 1, "ty": 4, "nm": "Shape", "sr": 1,
    "ks": {
      "o": {"a": 0, "k": 100}, "r": {"a": 0, "k": 0}, "p": {"a": 0, "k": [50, 50, 0]},
      "a": {"a": 0, "k": [0, 0, 0]}, "s": {"a": 0, "k": [100, 100, 100]}
    },
    "shapes": [{
      "ty": "gr", "it": [
        {
          "ind": 0, "ty": "sh", "ix": 1,
          "ks": {
            "a": 1,
            "k": [
              {"i": {"x": [0.667], "y": [1]}, "o": {"x": [0.333], "y": [0]}, "t": 0, "s": [{"i": [[0, 0], [0, 0], [0, 0]], "o": [[0, 0], [0, 0], [0, 0]], "v": [[-26, 4], [-26, 4], [-26, 4]], "c": false}]},
              {"i": {"x": [0.667], "y": [1]}, "o": {"x": [0.333], "y": [0]}, "t": 20, "s": [{"i": [[0, 0], [0, 0], [0, 0]], "o": [[0, 0], [0, 0], [0, 0]], "v": [[-26, 4], [-9, 21], [-9, 21]], "c": false}]},
              {"t": 35, "s": [{"i": [[0, 0], [0, 0], [0, 0]], "o": [[0, 0], [0, 0], [0, 0]], "v": [[-26, 4], [-9, 21], [27, -17]], "c": false}]}
            ]
          }
        },
        {
          "ty": "st", "c": {"a": 0, "k": [0.15, 0.65, 0.27, 1]},
          "o": {"a": 0, "k": 100}, "w": {"a": 0, "k": 8}, "lc": 2, "lj": 2
        }
      ]
    }]
  }]
}
""")

# --- 0. SEGURANÇA (LOGIN) ---
def check_password():
    """Retorna True se o usuário digitou a senha correta."""
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
    else:
        return True

if not check_password():
    st.stop()

# --- 1. CONFIGURAÇÃO DO GOOGLE SHEETS ---
@st.cache_resource
def conectar_google():
    try:
        info = dict(st.secrets["gcp_service_account"])
        raw_key = info["private_key"].strip()
        lines = [line.strip() for line in raw_key.split('\n')]
        clean_key = '\n'.join(lines)
        info["private_key"] = clean_key.replace("\\n", "\n")
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        
        return client.open("Controle").worksheet("Pedidos")
        
    except Exception as e:
        st.error(f"Erro de conexão detalhado: {e}")
        return None

try:
    aba_pedidos = conectar_google()
except Exception as e:
    st.error(f"Erro de conexão com a planilha: {e}")
    st.stop()

# --- 2. ESTADO DO SISTEMA (MEMÓRIA) ---
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
if 'pedido_enviado' not in st.session_state:
    st.session_state.pedido_enviado = False

# --- 3. DADOS FIXOS ---
cardapio = {
    "Pão de Leite": 15.00,
    "Pão Integral": 17.00,
    "Pão Semi Integral": 17.00,
    "Shokupan": 17.00,
    "Pastel de Nata": 7.00,
    "Pastel de Maçã": 7.00,
    "Pastel de Ricota com Ervas Finas": 7.00,
    "Pastel de Frango com Parmesão": 7.00,
}
codigo_pasteis = ["Pastel de Nata", "Pastel de Maçã", "Pastel de Ricota com Ervas Finas", "Pastel de Frango com Parmesão"]

# --- 4. INTERFACE VISUAL ---
st.set_page_config(page_title="Maison Lycoris - Pedidos", page_icon="🥐")

# TELA DE SUCESSO PÓS-ENVIO
if st.session_state.pedido_enviado:
    st.markdown("<br>", unsafe_allow_html=True)
    # Exibe a animação do Check
    if lottie_json:
        st_lottie(lottie_json, height=200, key="success_check", speed=1, loop=False)
    else:
        st.title("✔️") # Fallback caso o link do Lottie falhe
    
    st.markdown("<h2 style='text-align: center;'>Pedido Confirmado!</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Os dados já estão na planilha da Maison Lycoris.</p>", unsafe_allow_html=True)
    
    if st.button("Criar Novo Pedido", use_container_width=True):
        st.session_state.carrinho = []
        st.session_state.pedido_enviado = False
        st.rerun()
    st.stop()

st.title("🥐 Maison Lycoris - Sistema de Pedidos")

# Coleta de dados do cliente
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        nome_cliente = st.text_input("Nome do Cliente", placeholder="Ex: Zé Bedeu")
    with col2:
        data_selecionada = st.date_input(
            "Data de Entrega", 
            value=datetime.now(),
            format="DD/MM/YYYY" 
        )
        data_entrega = data_selecionada.strftime("%d/%m/%Y")

st.divider()

# Seleção de produtos
st.subheader("Adicionar Produtos")
c_prod, c_qtd, c_add = st.columns([3, 1, 1])

with c_prod:
    produto = st.selectbox("Selecione o Produto", list(cardapio.keys()))
with c_qtd:
    qtd = st.number_input("Quantidade", min_value=1, step=1)
with c_add:
    st.write(" ") 
    if st.button("➕ Adicionar"):
        if nome_cliente and data_entrega:
            preco_u = cardapio[produto]
            st.session_state.carrinho.append({
                "produto": produto,
                "qtd": qtd,
                "preco_unitario": preco_u,
                "subtotal": qtd * preco_u
            })
            st.toast(f"{produto} adicionado!", icon="🛒")
        else:
            st.warning("Preencha o nome do cliente e a data primeiro!")

# --- 5. EXIBIÇÃO DO CARRINHO E CÁLCULOS ---
if st.session_state.carrinho:
    st.divider()
    st.subheader("📝 Resumo da Encomenda")
    
    df = pd.DataFrame(st.session_state.carrinho)
    total_unidades_pasteis = sum(item['qtd'] for item in st.session_state.carrinho if item['produto'] in codigo_pasteis)
    tem_desconto = total_unidades_pasteis >= 4
    
    for i, item in df.iterrows():
        st.write(f"**{item['qtd']}x {item['produto']}** - R$ {item['subtotal']:.2f}")

    total_bruto = df['subtotal'].sum()
    total_desconto = sum(item['subtotal'] * 0.15 for item in st.session_state.carrinho if tem_desconto and item['produto'] in codigo_pasteis)
    total_final = total_bruto - total_desconto

    st.divider()
    if total_desconto > 0:
        st.write(f"Subtotal Bruto: R$ {total_bruto:.2f}")
        st.write(f"🎁 Desconto Combo Pastéis: -R$ {total_desconto:.2f}")
    
    st.metric("Total a Pagar", f"R$ {total_final:.2f}")

    # --- 6. ENVIO PARA O GOOGLE SHEETS ---
    if st.button("🚀 FINALIZAR E ENVIAR PEDIDO", use_container_width=True):
        id_pedido = datetime.now().strftime("%Y%m%d%H%M")
        data_entrada = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        dados_finais = []
        for item in st.session_state.carrinho:
            desc_i = (item['subtotal'] * 0.15) if (tem_desconto and item['produto'] in codigo_pasteis) else 0.0
            liq_i = item['subtotal'] - desc_i
            
            dados_finais.append([
                id_pedido, nome_cliente, data_entrega, item['produto'], 
                item['qtd'], item['subtotal'], desc_i, liq_i, data_entrada
            ])
        
        try:
            aba_pedidos.append_rows(dados_finais)
            st.session_state.pedido_enviado = True
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar na planilha: {e}")
