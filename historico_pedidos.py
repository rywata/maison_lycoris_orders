import streamlit as st
import pandas as pd
from database import Database
from logic_historico_pedidos import HistoricoFiltro

def renderizar_historico():
    st.title("📂 Histórico de Pedidos")

    # 1. Carga e Preparação
    try:
        db = Database()
        df = pd.DataFrame(db.conectar_aba("Controle", "Pedidos").get_all_records())
        
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
        st.error(f"Erro na carga de dados: {e}")
        return

    # 2. Instanciando a Lógica
    historico = HistoricoFiltro(df)

    # 3. Interface de Filtros (Sidebar)
    with st.sidebar:
        st.header("🔍 Filtros")
        busca_nome = st.text_input("Nome do Cliente").strip()
        produto_sel = st.selectbox("Produto", ["Todos"] + sorted(list(df['Produto'].unique())))
        
        intervalo = st.date_input(
            "Intervalo de Datas",
            value=(df['Data Pedido'].min(), df['Data Pedido'].max())
        )

    # 4. Executando a Lógica de Filtragem
    historico.filtrar(busca_nome, produto_sel, intervalo)

    # 5. Dashboard
    col1, col2 = st.columns(2)
    col1.metric("Pedidos Localizados", historico.total_pedidos)
    col2.metric("Soma Total", f"R$ {historico.faturamento_total:,.2f}")

    # 6. Exibição da Tabela
    colunas_visiveis = ['Data Pedido', 'Nome Cliente', 'Produto', 'Quantidade', 'Total Item Líquido', 'Data Entrega']
    st.dataframe(historico.df_filtrado[colunas_visiveis], use_container_width=True, hide_index=True)