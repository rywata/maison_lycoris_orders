import streamlit as st
import pandas as pd
from database import Database
from logic_estoque import AnalisadorEstoque

#Receber entradas no estoque
#Conectar com pedidos e debitar do estoque os insumos utilizados no pedido
#Criar database com os dados dos insumos utilizados em cada produto
#Gerar etiqueta com dados de cada lote cadastrado

def carregar_dados_estoque():
  try:
    db = Database()
    aba =  db.conectar_aba("Controle", "Movimentações")
    dados = aba.get_all_records()

    df = pd.DataFrame(dados)

    if not df.empty:
      df.columns = df.columns.srt.strip()
      return df
    return pd.DataFrame(dados)
  
  except Exception as e:
    st.error(f"Erro ao acessar aba de Movimentações: {e}")
    return pd.DataFrame()

def renderizar_estoque():
  st.title("📦 Gestão de Estoque")

  #1. Busca de dados brutos
  df_movimentacoes = carregar_dados_estoque()

  if df_movimentacoes.empty():
    st.info("Nenhuma movimentalção de estoque registrada.")
    return

  #2. Envia dados para a lógica
  analisador = AnalisadorEstoque(df_movimentacoes)

  #3. Exibir saldo atual
  st.subheader("Saldos Atuais")
  st.dataframe(analisador.saldo_atual, use_container_width=True)


