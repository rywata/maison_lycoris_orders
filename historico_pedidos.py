import streamlit as st
import pandas as pd
from database import Database

'''def pagina_consulta():
  st.title("📂 Histórico de Pedidos")

  db = Database()

  dados_brutos = db.conctar_aba("Controle", "Pedidos").get_all_records()

  if dados_brutos:
    df_pedidos = pd.DataFrame(dados_brutos)

    cliente = st.text_input("Filtrar por Cliente")
    if cliente:
      df_pedidos = df_pedidos[df_pedidos['Cliente'].str.contains(cliente, case=FALSE)]

    #tabela
    st.dataframe(df_pedidos, use_container_width=True)

  else:
    st.warning("Nenhum pedido registrado ainda.")'''
