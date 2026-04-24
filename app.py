import streamlit as st
from historico_pedidos import renderizar_historico
from datetime import date
from database import Database
from pedidos import renderizar_novo_pedido
import pandas as pd
import os
import time

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

@st.cache_data(ttl=600)
def carregar_dados_pedidos():
  for tentativa in range(3):

    try:
      db = Database()

      aba = db.conectar_aba("Controle", "Pedidos")
      df = pd.DataFrame(aba.get_all_records())

      if not df.empty:
        df['Data Pedido'] = pd.to_datetime(df['Data Pedido'], dayfirst=True).dt.date
        df['Data Entrega'] = pd.to_datetime(df['Data Entrega'], dayfirst=True).dt.date
      return df
    except Exception as e:
      if "503" in str(e) and tentativa < 2:
        time.sleep(1)
        continue
      st.error(f"Erro ao carregar dados: {e}")
      return pd.DataFrame()

def carregar_logo():
  caminho_logo = "assets/logo_black2.png"
  if os.path.exists(caminho_logo):
    st.sidebar.image(caminho_logo, width=250)
  else:
    st.sidebar.title("Maison Lycoris")

carregar_logo()

#tratamento para converter strings de moeda
def clean_currency(x):
  if isinstance(x, str):
    return float(x.replace('R$', '').replace('.', '').replace(',', '.').strip())
  return(x) 

def tela_inicio():
  st.title("🥐 Maison Lycoris - Gestão Artesanal")
  st.write(f"Bem vindo! Hoje é dia {date.today().strftime('%d/%m/%Y')}")

  #1. Carregar dados
  df = carregar_dados_pedidos()
  hoje = date.today()

  if df.empty:
    st.warning("Nenhum dado encontrado na planilha Pedidos.")
    return

  #2. Metricas
  df_vendas_hoje = df[df['Data Pedido'] == hoje]

  if not df_vendas_hoje.empty:
    vendas_valor = df_vendas_hoje['Total Item Líquido'].apply(clean_currency).sum()
  else:
    vendas_valor = 0.0
 

  vendas_valor = df_vendas_hoje['Total Item Líquido'].sum() if not df_vendas_hoje.empty else 0.0

  # Pedidos para hoje ou no futuro
  entregas_hoje = df[df['Data Entrega'] >= hoje.strftime('%d/%m/%Y')]
  total_entregas_hoje = len(entregas_hoje)


  #3. Dashboard
  col1, col2, col3 = st.columns(3)
  col1.metric("Vendas Hoje", f"R$ {vendas_valor:,.2f}")
  col2.metric("Entregas para Hoje", total_entregas_hoje)
  col3.metric("Estoque Crítico", "implementar", delta="implementar", delta_color="inverse")

  st.divider()

  #4. Próximas fornadas
  st.subheader("Cronograma de Produção")
  pedidos_futuros = df[df['Data Entrega'] >= hoje].sort_values('Data Entrega')

  if not pedidos_futuros.empty:
    view_producao = pedidos_futuros[['Data Entrega', 'Cliente', 'Produto', 'Quantidade']].sort_values('Data Entrega')
    st.dataframe(view_producao, use_container_width=True, hide_index=True)
  else:
    st.info("Nenhum pedido agendado para os próximos dias.")

# Gerenciador de navegação na sidebar
st.sidebar.markdown("### 🧭 Navegação")

if 'aba_atual' not in st.session_state:
  st.session_state.aba_atual = "Início"

def ir_para(nome_aba):
  st.session_state.aba_atual = nome_aba

# Botões sidebar
st.sidebar.button("🏠 Início", on_click=ir_para, args=("Início",), use_container_width=True)
st.sidebar.button("📝 Novo Pedido", on_click=ir_para, args=("Novo Pedido",), use_container_width=True)
st.sidebar.button("📜 Histórico", on_click=ir_para, args=("Histórico",), use_container_width=True)
st.sidebar.button("📦 Estoque", on_click=ir_para, args=("Estoque",), use_container_width=True)
st.sidebar.button("💰 Faturamento", on_click=ir_para, args=("Faturamento",), use_container_width=True)

# Lógica de renderização baseada no estado
if st.session_state.aba_atual == "Início":
    tela_inicio()
elif st.session_state.aba_atual == "Novo Pedido":
    renderizar_novo_pedido
elif st.session_state.aba_atual == "Histórico":
    renderizar_historico()
elif st.session_state.aba_atual == "Estoque":
    st.title("📦 Gestão de Estoque")
elif st.session_state.aba_atual == "Faturamento":
    st.title("💰 Faturamento")
