import streamlit as st
import pandas as pd
from logic_pedidos import BuscaPedidos
from database import Database

def renderizar_historico():
  st.title("📂 Histórico de Pedidos")

  # 1. Carga de dados
  try:
    db = Database()
    dados_brutos = db.conectar_aba("Controle", "Pedidos").get_all_records()
    df = pd.DataFrame(dados_brutos)
    
    if df.empty:
      st.warning("A planilha está vazia.")
      return

    df.columns = df.columns.str.strip()
    df['Data Pedido'] = pd.to_datetime(df['Data Pedido'], dayfirst=True).dt.date
    df['Valor Numérico'] = (
      df['Total Item Líquido']
      .astype(str)
      .str.replace('R$', '', regex=False)
      .str.replace('.', '', regex=False)
      .str.replace(',', '.', regex=False)
      .astype(float)
    )
  
  except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    return

  # 2. Menu lateral de filtros
  st.sidebar.header("🔍 Filtros de Busca")

  with st.sidebar:
    busca_nome = st.text_input("Filtrar por Nome do Cliente").strip()

    produtos_unicos = ["Todos"] + sorted(list(df['Produto'].unique()))
    produto_selecionado = st.selectbox("Produto", options=produtos_unicos)

    # Filtro de data
    data_min = df['Data Pedido'].min()
    data_max = df['Data Pedido'].max()

    intervalo_data = st.date_input(
      "Intervalo de Datas (Pedido)",
      value=(data_min, data_max),
      min_value=data_min,
      max_value=data_max
    )
  
  #3. Filtragem
  df_filtrado = df.copy()

  if busca_nome:
    df_filtrado = df_filtrado[df_filtrado['Nome Cliente'].str.contains(busca_nome, case=False, na=False)]

  if produto_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Produto'] == produto_selecionado]

  if isinstance(intervalo_data, tuple) and len(intervalo_data) == 2:
    df_filtrado = df_filtrado[
      (df_filtrado['Data Pedido'] >= intervalo_data[0]) &
      (df_filtrado['Data Pedido'] <= intervalo_data[1])
    ]

  #4. Métricas e Exibição
  col1, col2 = st.columns(2)
  col1.metric("Pedidos Localizados", len(df_filtrado))
  col2.metric("Soma Total", f"R$ {df_filtrado['Valor Numérico'].sum():,.2f}")

  # Tabela principal
  colunas_reais = ['Data Pedido', 'Nome Cliente', 'Produto', 'Quantidade', 'Total Item Líquido', 'Data Entrega']
  st.dataframe(df_filtrado[colunas_reais], use_container_width=True, hide_index=True)