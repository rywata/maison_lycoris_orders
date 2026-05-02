import streamlit as st
import pandas as pd
from database import Database
from datetime import date

@st.cache_data(ttl=60)
def carregar_pedidos():
    return Database().pedidos()

def renderizar_historico():
    st.title("📂 Histórico de Pedidos")

    df = carregar_pedidos()

    if df.empty:
        st.warning("Nenhum pedido encontrado.")
        return

    df.columns = [c.lower() for c in df.columns]
    
    df['data_pedido'] = pd.to_datetime(df['data_pedido'], errors='coerce').dt.date
    df['data_entrega'] = pd.to_datetime(df['data_entrega'], errors='coerce').dt.date
    
    df['total_liquido'] = pd.to_numeric(df['total_liquido'], errors='coerce').fillna(0)

    # --- FILTROS NA SIDEBAR ---
    with st.sidebar:
        st.header("🔍 Filtros")
        busca_nome = st.text_input("Nome do Cliente").strip()

        produtos_disponiveis = ["Todos"] + sorted(df['produto'].dropna().unique().tolist())
        produto_sel = st.selectbox("Produto", produtos_disponiveis)

        datas_validas = df['data_pedido'].dropna()
        
        if not datas_validas.empty:
            lista_datas = list(datas_validas)
            data_min_calc = min(lista_datas)
            data_max_calc = max(lista_datas)
        else:
            data_min_calc = date.today()
            data_max_calc = date.today()

        intervalo = st.date_input(
            "Intervalo de Datas", 
            value=(data_min_calc, data_max_calc)
        )

    # --- FILTRAGEM ---
    df_filtrado = df.copy()

    if busca_nome:
        df_filtrado = df_filtrado[
            df_filtrado['nome_cliente'].str.contains(busca_nome, case=False, na=False)
        ]

    if produto_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado['produto'] == produto_sel]

    if isinstance(intervalo, (list, tuple)) and len(intervalo) == 2:
        inicio, fim = intervalo
        df_filtrado = df_filtrado.dropna(subset=['data_pedido'])
        df_filtrado = df_filtrado[
            (df_filtrado['data_pedido'] >= inicio) &
            (df_filtrado['data_pedido'] <= fim)
        ]

    if df_filtrado.empty:
        st.info("Nenhum pedido atende aos filtros selecionados.")
        return

    # --- MÉTRICAS ---
    pedidos_unicos = df_filtrado.groupby('id_pedido')['total_liquido'].sum()
    total_pedidos = len(pedidos_unicos)
    faturamento = pedidos_unicos.sum()

    col1, col2 = st.columns(2)
    col1.metric("Pedidos Localizados", total_pedidos)
    col2.metric("Faturamento Total", f"R$ {faturamento:,.2f}")

    st.divider()

    # --- TABELA ---
    colunas_visiveis = {
        'data_pedido': 'Data Pedido',
        'nome_cliente': 'Cliente',
        'produto': 'Produto',
        'quantidade': 'Qtd',
        'total_bruto': 'Bruto',
        'desconto': 'Desconto',
        'total_liquido': 'Total Líquido',
        'data_entrega': 'Data Entrega',
    }

    # Garante que apenas colunas existentes sejam usadas
    colunas_reais = [c for c in colunas_visiveis.keys() if c in df_filtrado.columns]
    df_exibir = df_filtrado[colunas_reais].rename(columns=colunas_visiveis)

    st.dataframe(
        df_exibir.sort_values('Data Pedido', ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Bruto": st.column_config.NumberColumn(format="R$ %.2f"),
            "Desconto": st.column_config.NumberColumn(format="R$ %.2f"),
            "Total Líquido": st.column_config.NumberColumn(format="R$ %.2f"),
        }
    )

    st.divider()

    # --- RESUMO POR PRODUTO ---
    with st.expander("📊 Resumo por produto"):
        resumo = (
            df_filtrado.groupby('produto')
            .agg(
                Pedidos=('id_pedido', 'nunique'),
                Quantidade=('quantidade', 'sum'),
                Faturamento=('total_liquido', 'sum')
            )
            .reset_index()
            .rename(columns={'produto': 'Produto'})
            .sort_values('Faturamento', ascending=False)
        )
        st.dataframe(
            resumo,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Faturamento": st.column_config.NumberColumn(format="R$ %.2f"),
            }
        )

    # --- RESUMO POR CLIENTE ---
    with st.expander("👥 Resumo por cliente"):
        por_cliente = (
            df_filtrado.groupby('nome_cliente')
            .agg(
                Pedidos=('id_pedido', 'nunique'),
                Faturamento=('total_liquido', 'sum')
            )
            .reset_index()
            .rename(columns={'nome_cliente': 'Cliente'})
            .sort_values('Faturamento', ascending=False)
        )
        st.dataframe(
            por_cliente,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Faturamento": st.column_config.NumberColumn(format="R$ %.2f"),
            }
        )