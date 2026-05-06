import streamlit as st
import pandas as pd
from database import Database
from datetime import date

@st.cache_data(ttl=60)
def carregar_pedidos():
    db = Database()
    df = db.pedidos()
    
    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [c.lower() for c in df.columns]
    
    # Conversão segura de datas
    df['data_pedido'] = pd.to_datetime(df['data_pedido'], errors='coerce')
    df['data_entrega'] = pd.to_datetime(df['data_entrega'], errors='coerce')
    
    # Conversão de valores financeiros
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

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🔍 Filtros")
        
        busca_nome = st.text_input("Nome do Cliente").strip()

        # Produtos
        produtos_disponiveis = ["Todos"] + sorted(df['produto'].dropna().unique().tolist())
        produto_sel = st.selectbox("Produto", produtos_disponiveis)
        
        # Datas seguras
        datas_validas = df['data_pedido'].dropna()
        if not datas_validas.empty:
            data_min_calc = datas_validas.min().date()
            data_max_calc = datas_validas.max().date()
        else:
            data_min_calc = data_max_calc = date.today()

        intervalo = st.date_input(
            "Intervalo de Datas", 
            value=(data_min_calc, data_max_calc)
        )

    # --- FILTROS ---
    mask = pd.Series(True, index=df.index)

    if busca_nome:
        mask &= df['nome_cliente'].str.contains(busca_nome, case=False, na=False)

    if produto_sel != "Todos":
        mask &= (df['produto'] == produto_sel)

    if isinstance(intervalo, (list, tuple)) and len(intervalo) == 2:
        inicio, fim = intervalo
        
        inicio = pd.to_datetime(inicio).replace(tzinfo=None)
        fim = pd.to_datetime(fim).replace(tzinfo=None) + pd.Timedelta(days=1)

        data_pedido_sem_tz = pd.to_datetime(df['data_pedido']).dt.tz_localize(None)

        mask &= (
            data_pedido_sem_tz.notna() &
            (data_pedido_sem_tz >= inicio) &
            (data_pedido_sem_tz < fim)
        )

    df_filtrado = df[mask]

    if df_filtrado.empty:
        st.info("Nenhum pedido atende aos filtros selecionados.")
        return

    # --- MÉTRICAS ---
    total_pedidos = df_filtrado['id_pedido'].nunique()
    faturamento = df_filtrado['total_liquido'].sum()

    m1, m2 = st.columns(2)
    m1.metric("Pedidos Localizados", total_pedidos)
    m2.metric("Faturamento Total", f"R$ {faturamento:,.2f}")

    st.divider()

    # --- TABELA ---
    colunas_visiveis = {
        'data_pedido': 'Data',
        'nome_cliente': 'Cliente',
        'produto': 'Produto',
        'quantidade': 'Qtd',
        'total_liquido': 'Total Líquido'
    }

    colunas_existentes = [c for c in colunas_visiveis.keys() if c in df_filtrado.columns]

    df_exibir = df_filtrado[colunas_existentes].copy()
    df_exibir = df_exibir.rename(columns=colunas_visiveis)

    # Converter data só para exibição
    if 'Data' in df_exibir.columns:
        df_exibir['Data'] = pd.to_datetime(df_exibir['Data'], errors='coerce').dt.date

    # Ordenação segura
    df_exibir = df_exibir.sort_values('Data', ascending=False, na_position='last')

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total Líquido": st.column_config.NumberColumn(format="R$ %.2f"),
        }
    )

    # --- RESUMO ---
    with st.expander("📊 Resumo por Produto"):
        resumo_prod = (
            df_filtrado.groupby('produto')
            .agg(
                Qtd_Total=('quantidade', 'sum'),
                Valor_Total=('total_liquido', 'sum')
            )
            .sort_values('Valor_Total', ascending=False)
        )
        st.table(resumo_prod)