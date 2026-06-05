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

    hoje = date.today()
    primeiro_dia_mes = hoje.replace(day=1)

    if hoje.month == 12:
        ultimo_dia_mes = hoje.replace(year=hoje.year + 1, month=1, day=1) - pd.Timedelta(days=1)
    else:
        ultimo_dia_mes = hoje.replace(month=hoje.month + 1, day=1) - pd.Timedelta(days=1)
    
    ultimo_dia_mes = ultimo_dia_mes.date() if hasattr(ultimo_dia_mes, 'date') else ultimo_dia_mes

    datas_pedido_validas = df['data_pedido'].dropna()
    data_min_pedido = datas_pedido_validas.min().date() if not datas_pedido_validas.empty else hoje
    data_max_pedido = datas_pedido_validas.max().date() if not datas_pedido_validas.empty else hoje

    datas_entrega_validas = df['data_entrega'].dropna()
    data_min_entrega = datas_entrega_validas.min().date() if not datas_entrega_validas.empty else hoje
    data_max_entrega = datas_entrega_validas.max().date() if not datas_entrega_validas.empty else hoje


    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🔍 Filtros")
        
        busca_nome = st.text_input("Nome do Cliente").strip()

        # Produtos
        produtos_disponiveis = ["Todos"] + sorted(df['produto'].dropna().unique().tolist())
        produto_sel = st.selectbox("Produto", produtos_disponiveis)
        
        # Datas do pedido
        intervalo = st.date_input(
            "Intervalo de Datas (Pedido)", 
            value=(primeiro_dia_mes, ultimo_dia_mes),
            min_value=data_min_pedido,
            max_value=data_max_pedido
        )

        # Datas de entrega
        intervalo_entrega = st.date_input(
            "Intervalo de Entrega",
            value=(primeiro_dia_mes, ultimo_dia_mes),
            min_value=data_min_entrega,
            max_value=data_max_entrega
        )

    # --- FILTROS ---
    mask = pd.Series(True, index=df.index)

    if busca_nome:
        mask &= df['nome_cliente'].str.contains(busca_nome, case=False, na=False)

    if produto_sel != "Todos":
        mask &= (df['produto'] == produto_sel)

    if isinstance(intervalo, (list, tuple)) and len(intervalo) == 2:
        inicio = pd.to_datetime(intervalo[0]).replace(tzinfo=None)
        fim = pd.to_datetime(intervalo[1]).replace(tzinfo=None) + pd.Timedelta(days=1)
        data_pedido_sem_tz = pd.to_datetime(df['data_pedido']).dt.tz_localize(None)
        mask &= data_pedido_sem_tz.notna() & (data_pedido_sem_tz >= inicio) & (data_pedido_sem_tz < fim)

    if isinstance(intervalo_entrega, (list, tuple)) and len(intervalo_entrega) == 2:
        inicio_e = pd.to_datetime(intervalo_entrega[0]).replace(tzinfo=None)
        fim_e = pd.to_datetime(intervalo_entrega[1]).replace(tzinfo=None) + pd.Timedelta(days=1)
        data_entrega_sem_tz = pd.to_datetime(df['data_entrega']).dt.tz_localize(None)
        mask &= data_entrega_sem_tz.notna() & (data_entrega_sem_tz >= inicio_e) & (data_entrega_sem_tz < fim_e)


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
        'data_entrega': 'Data de entrega',
        'nome_cliente': 'Cliente',
        'produto': 'Produto',
        'quantidade': 'Qtd',
        'total_bruto': 'Total Bruto',
        'custo_total': 'Custo Total',
        'desconto': 'Desconto',
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