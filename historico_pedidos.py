import streamlit as st
import pandas as pd
from database import Database
from datetime import date

@st.cache_data(ttl=60)
def carregar_pedidos():
    df = Database().pedidos()
    
    if df is None or df.empty:
        return pd.DataFrame()
    
    df.columns = [c.lower() for c in df.columns]
    df['data_pedido'] = pd.to_datetime(df['data_pedido'], errors='coerce')
    df['data_entrega'] = pd.to_datetime(df['data_entrega'], errors='coerce')
    cols_financeiras = ['total_liquido', 'total_bruto', 'desconto']
    for col in cols_financeiras:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

def renderizar_historico():
    st.title("📂 Histórico de Pedidos")

    df_raw = carregar_pedidos()

    if df_raw.empty:
        st.warning("Nenhum pedido encontrado no banco de dados.")
        return

    df = df_raw.copy()
    df['data_pedido_limpa'] = df['data_pedido'].dt.date

    # --- FILTROS NA SIDEBAR ---
    with st.sidebar:
        st.header("🔍 Filtros")
        
        busca_nome = st.text_input("Nome do Cliente").strip()

        produtos_disponiveis = ["Todos"] + sorted(df['produto'].dropna().unique().tolist())
        produto_sel = st.selectbox("Produto", produtos_disponiveis)
        datas_lista = [d for d in df['data_pedido_limpa'].tolist() if isinstance(d, date)]
        
        if datas_lista:
            data_min_calc = min(datas_lista)
            data_max_calc = max(datas_lista)
        else:
            data_min_calc = data_max_calc = date.today()

        intervalo = st.date_input(
            "Intervalo de Datas", 
            value=(data_min_calc, data_max_calc)
        )

    # --- LÓGICA DE FILTRAGEM ---
    mask = pd.Series(True, index=df.index)

    if busca_nome:
        mask &= df['nome_cliente'].str.contains(busca_nome, case=False, na=False)

    if produto_sel != "Todos":
        mask &= (df['produto'] == produto_sel)

    if isinstance(intervalo, (list, tuple)) and len(intervalo) == 2:
        inicio, fim = intervalo
        mask &= (df['data_pedido_limpa'] >= inicio) & (df['data_pedido_limpa'] <= fim)

    df_filtrado = df[mask]

    if df_filtrado.empty:
        st.info("Nenhum pedido atende aos filtros selecionados.")
        return

    # --- MÉTRICAS ---
    pedidos_unicos = df_filtrado.groupby('id_pedido')['total_liquido'].first()
    total_pedidos = len(pedidos_unicos)
    faturamento = pedidos_unicos.sum()

    col1, col2 = st.columns(2)
    col1.metric("Pedidos Localizados", total_pedidos)
    col2.metric("Faturamento Total", f"R$ {faturamento:,.2f}")

    st.divider()

    # --- EXIBIÇÃO DA TABELA ---
    colunas_visiveis = {
        'data_pedido_limpa': 'Data',
        'nome_cliente': 'Cliente',
        'produto': 'Produto',
        'quantidade': 'Qtd',
        'total_liquido': 'Total Líquido'
    }

    colunas_finais = [c for c in colunas_visiveis.keys() if c in df_filtrado.columns]
    df_exibir = df_filtrado[colunas_finais].rename(columns=colunas_visiveis)

    st.dataframe(
        df_exibir.sort_values('Data', ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total Líquido": st.column_config.NumberColumn(format="R$ %.2f"),
        }
    )

    # --- RESUMOS EXPANSÍVEIS ---
    with st.expander("📊 Resumo por Produto"):
        resumo_prod = (
            df_filtrado.groupby('produto')
            .agg(Qtd_Total=('quantidade', 'sum'), Valor_Total=('total_liquido', 'sum'))
            .sort_values('Valor_Total', ascending=False)
        )
        st.table(resumo_prod) 