import streamlit as st
from historico_pedidos import renderizar_historico
from datetime import date
import os

def carregar_logo():
  caminho_logo = "assets/logo_black2.png"

  if os.path.exists(caminho_logo):
    st.sidebar.image(caminho_logo, width=150)
  else:
    st.sidebar.title("Maison Lycoris")

carregar_logo()

def tela_inicio():
  st.title("🥐 Maison Lycoris - Gestão Artesanal")
  st.write(f"Bem vindo! Hoje é dia {date.today().strftime('%d/%m/%Y')}")

  #Dashboard
  col1, col2, col3 = st.columns(3)
  col1.metric("Vendas Hoje", "implementar valor vendas", "implementar variação")
  col2.metric("Pedidos a Entregar", "implementar qtd pedidos")
  col3.metric("Implementar metrica de estoque", "Produto", delta="-und kg", delta_color="inverse")

  st.divider()
  st.subheader("Próximas fornadas")
  st.info("implementar controle de produção")

# Gerenciador de navegação na sidebar
st.sidebar.image("assets/logo_black2.png", width=100)
aba = st.sidebar.selectbox("Ir para: ", ["Início", "Novo Pedido", "Histórico", "Estoque", "Faturamento"])

if aba == "Início":
  tela_inicio()
elif aba == "Novo Pedido":
  #implementar tela pedidos e corrigir validação
  pass
elif aba == "Histórico":
  renderizar_historico()
elif aba == "Faturamento":
  #implementar tela faturamento
  pass
