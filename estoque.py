import streamlit as st
import pandas as pd
from database import Database
from logic_estoque import AnalisadorEstoque, GerenciadorMovimentacao, BuscaEstoque
from datetime import datetime

def carregar_dados_estoque():
    try:
        db = Database()
        aba = db.conectar_aba("Controle", "Movimentações")
        dados = aba.get_all_records()
        df = pd.DataFrame(dados)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao acessar aba de Movimentações: {e}")
        return pd.DataFrame()

def renderizar_estoque():
    st.title("📦 Gestão de Estoque")

    df_movimentacoes = carregar_dados_estoque()

    if df_movimentacoes.empty:
        st.info("Nenhuma movimentação de estoque registrada.")
    else:
        analisador = AnalisadorEstoque(df_movimentacoes)
        st.subheader("Saldos Atuais")
        st.dataframe(analisador.saldo_atual, use_container_width=True)

    st.divider()

    # --- BUSCA ---
    st.subheader("🔍 Buscar movimentações")

    if not df_movimentacoes.empty:
        col1, col2, col3 = st.columns(3)

        with col1:
            filtro_item = st.text_input("Filtrar por item", placeholder="Ex: Farinha")
        with col2:
            tipos = ["Todos"] + sorted(df_movimentacoes['Tipo'].dropna().unique().tolist())
            filtro_tipo = st.selectbox("Tipo de movimentação", tipos)
        with col3:
            filtro_data = st.date_input("Data início", value=None)

        # Aplica filtros via BuscaEstoque
        buscador = BuscaEstoque(AnalisadorEstoque(df_movimentacoes).df)
        buscador.filtrar(
            item=filtro_item,
            tipo=filtro_tipo,
            data_inicio=filtro_data if filtro_data else None,
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("Registros encontrados", len(buscador.df_filtrado))
        m2.metric("Total entradas", f"{buscador.total_entradas:.3f}")
        m3.metric("Total saídas", f"{abs(buscador.total_saidas):.3f}")

        st.dataframe(
            buscador.df_filtrado.sort_values('Data Mov.', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Sem dados para buscar.")

    st.divider()



    st.subheader("Registrar Movimentação")

    col1, col2, col3, col4 = st.columns(4)

    if col1.button("📥 Compra (ENT-C)", use_container_width=True):
        st.session_state.tipo_mov = "ENT-C"
        st.session_state.mostrar_form = True
    if col2.button("🏗️ Produção (SAI-P)", use_container_width=True):
        st.session_state.tipo_mov = "SAI-P"
        st.session_state.mostrar_form = True
    if col3.button("🍞 Entrada Prod (ENT-P)", use_container_width=True):
        st.session_state.tipo_mov = "ENT-P"
        st.session_state.mostrar_form = True
    if col4.button("💰 Venda (SAI-V)", use_container_width=True):
        st.session_state.tipo_mov = "SAI-V"
        st.session_state.mostrar_form = True

    if st.session_state.get("mostrar_form"):
        tipo = st.session_state.tipo_mov
        
        with st.form("form_movimentacao"):
            st.markdown(f"### Registro: **{tipo}**")
            
            c1, c2 = st.columns(2)
            with c1:
                item = st.text_input("Item")
                qtd = st.number_input("Quantidade", min_value=0.0, step=0.001, format="%.3f")
                un_medida = st.selectbox("Unidade de Medida", ["kg", "g", "L", "ml", "un"])
                un_compra = st.text_input("Unidade de Compra (Ex: Saco 25kg)")
            
            with c2:
                validade = st.date_input("Validade", value=None)
                lote = st.text_input("Lote")
                custo = st.number_input("Custo Unitário", min_value=0.0, step=0.01)

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.form_submit_button("✅ Salvar", use_container_width=True):
                    gerenciador = GerenciadorMovimentacao(df_movimentacoes)
                    
                    linha_final = gerenciador.preparar_linha(
                        codigo=tipo,
                        item=item,
                        qtd=qtd,
                        unidade_medida=un_medida,
                        unidade_compra=un_compra,
                        custo_unitario=custo,
                        validade=validade.strftime("%d/%m/%Y") if validade else "",
                        lote=lote
                    )

                    try:
                        db = Database()
                        aba = db.conectar_aba("Controle", "Movimentações")
                        aba.append_row(linha_final)
                        st.success(f"Movimentação registrada! ID: {linha_final[0]}")
                        st.session_state.mostrar_form = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

            with btn_col2:
                if st.form_submit_button("❌ Cancelar", use_container_width=True):
                    st.session_state.mostrar_form = False
                    st.rerun()