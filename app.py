import streamlit as st
from historico_pedidos import renderizar_historico
from datetime import date
from database import Database
import pandas as pd
import os

@st.cache_data(ttl=600)
def carregar_dados_pedidos():
  try:
    db = Database()

    aba = db.conectar_aba("Controle", "Pedidos")
    df = pd.DataFrame(aba.get_all_records())

    if not df.empty:
      df['Data'] = pd.to_datetime(df['Data'], dayfirst=True).dt.date
      df['Data Entrega'] = pd.to_datetime(df['Data Entrega'], dayfirst=True).dt.date
    return df
  except Exception as e:
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
  df_vendas_hoje = df[df['Data'] == hoje]

  if not df_vendas_hoje.empty:
    vendas_valor = df_vendas_hoje['Total Item Líquido'].apply(clean_currency).sum()
  else:
    vendas_valor = 0.0
 

  vendas_valor = df_vendas_hoje['Total Item Líquido'].sum() if not df_vendas_hoje.empty else 0.0

  # Pedidos para hoje ou no futuro
  pedidos_pendentes = df[df['Data Entrega'] >= hoje.strftime('%d/%m/%Y')]
  total_pendentes = len(pedidos_pendentes)


  #3. Dashboard
  col1, col2, col3 = st.columns(3)
  col1.metric("Vendas Hoje", f"R$ {vendas_valor:,.2f}")
  col2.metric("Pedidos a Entregar", total_pendentes)
  col3.metric("Estoque Crítico", "implementar", delta="implementar", delta_color="inverse")

  st.divider()

  #4. Próximas fornadas
  st.subheader("Próximas fornadas")
  if not pedidos_pendentes.empty:
    view_producao = pedidos_pendentes[['Data Entrega', 'Cliente', 'Produto', 'Quantidade']].sort_values('Data Entrega')
    st.dataframe(view_producao, use_container_width=True, hide_index=True)
  else:
    st.info("Nenhum pedido agendado para os próximos dias.")

# Gerenciador de navegação na sidebar
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
