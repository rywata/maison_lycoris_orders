import streamlit as st
import pandas as pd
from logic_pedidos import BuscaPedidos
from database import Database

def renderizar_historico():
  st.title("📂 Histórico de Pedidos")

  # 1. Carga de dados
  db = Database()
  dados_brutos = db.conectar_aba("Controle", "Pedidos").get.all.records()
  df_original = pd.DataFrame(dados_brutos)

  # 2. Menu lateral de filtros
  st.sidebar.header("🔍 Filtros de Busca")

  with st.sidebar:
    nome_cliente = st.text_input("Nome do Cliente")

    produtos_unicos = ["Todos"] + list(df_original['Produto'].unique())
    produto_selecionado = st.selectbox("Produto", options=produtos_unicos)

    # Filtro de data
    intervalo_data = st.date_input(
      "Intervalo de Datas",
      value=(df_original['Data'].min(), df_original['Data'].max())
    )

  # 3. Execução da busca
  buscador = BuscaPedidos(df_original)

  if nome_cliente:
    buscador.por_cliente(nome_cliente)

  if produto_selecionado != "Todos":
    buscador.por_produto(produto_selecionado)

  if len(intervalo_data) == 2:
    buscador.por_intervalo_data(intervalo_data[0], intervalo_data[1])

  df_filtrado = buscador.obter_resultado()

  col1, col2 = st.columns(2)
  col1.metric("Pedidos Localizados", len(df_filtrado))
  col2.metric("Soma Total", f"R$ {df_filtrado['Valor Total'].sum():.2f}")

  # Tabela principal
  st.dataframe(df_filtrado, use_container_width=True)
