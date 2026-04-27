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

        buscador = BuscaEstoque(AnalisadorEstoque(df_movimentacoes).df)
        buscador.filtrar(
            item=filtro_item,
            tipo=filtro_tipo,
            data_inicio=filtro_data if filtro_data else None,
        )

        st.metric("Registros encontrados", len(buscador.df_filtrado))

        resumo = buscador.resumo_por_item
        if not resumo.empty:
            if buscador.item_unico:
                row = resumo.iloc[0]
                un = row['Unidade de Medida']
                m1, m2, m3 = st.columns(3)
                m1.metric("Entradas", f"{row['Entradas']:.3f} {un}")
                m2.metric("Saídas", f"{row['Saídas']:.3f} {un}")
                m3.metric("Saldo no período", f"{row['Saldo período']:.3f} {un}")
            else:
                st.caption("Totais por item — unidades diferentes não podem ser somadas.")
                st.dataframe(resumo, use_container_width=True, hide_index=True)

        st.dataframe(
            buscador.df_filtrado.sort_values('Data Mov.', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Sem dados para buscar.")

    st.divider()



    st.subheader("Registrar Movimentação")

    col1, col2, col3 = st.columns(3)
    if col1.button("📥 Compra (ENT-C)", use_container_width=True):
        st.session_state.tipo_mov = "ENT-C"
        st.session_state.mostrar_form = True
    if col2.button("🏗️ Produção (SAI-P)", use_container_width=True):
        st.session_state.tipo_mov = "SAI-P"
        st.session_state.mostrar_form = True
    if col3.button("🍞 Entrada Prod (ENT-P)", use_container_width=True):
        st.session_state.tipo_mov = "ENT-P"
        st.session_state.mostrar_form = True

    col4, col5, col6 = st.columns(3)
    if col4.button("💰 Venda (SAI-V)", use_container_width=True):
        st.session_state.tipo_mov = "SAI-V"
        st.session_state.mostrar_form = True
    if col5.button("🛠️ Ajuste Entrada (ENT-A)", use_container_width=True):
        st.session_state.tipo_mov = "ENT-A"
        st.session_state.mostrar_form = True
    if col6.button("🛠️ Ajuste Saída (SAI-A)", use_container_width=True):
        st.session_state.tipo_mov = "SAI-A"
        st.session_state.mostrar_form = True

    if st.session_state.get("mostrar_form"):
        tipo = st.session_state.tipo_mov
        eh_ajuste = tipo in ("ENT-A", "SAI-A")

        with st.form("form_movimentacao"):

            # --- FORMULÁRIO DE AJUSTE ---
            if eh_ajuste:
                st.markdown("### 🛠️ Ajuste de estoque")
                st.info("Informe a quantidade **real contada** no inventário. O sistema calcula a diferença automaticamente.")

                analisador = AnalisadorEstoque(df_movimentacoes)
                saldo_dict = analisador.saldo_atual.to_dict()
                itens_disponiveis = sorted(saldo_dict.keys())

                c1, c2 = st.columns(2)
                with c1:
                    item = st.selectbox("Item", itens_disponiveis)
                    saldo_sistema = saldo_dict.get(item, 0)
                    st.metric("Saldo no sistema", f"{saldo_sistema:.3f}")
                with c2:
                    qtd_contada = st.number_input("Quantidade contada", min_value=0.0, step=0.001, format="%.3f")
                    diferenca = qtd_contada - saldo_sistema
                    cor = "normal" if diferenca == 0 else ("inverse" if diferenca < 0 else "off")
                    st.metric("Diferença", f"{diferenca:+.3f}", delta_color=cor)

                motivo = st.selectbox("Motivo", ["Inventário", "Perda/Descarte", "Erro de lançamento", "Outro"])

            # --- FORMULÁRIO PADRÃO ---
            else:
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

            # --- BOTÕES ---
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.form_submit_button("✅ Salvar", use_container_width=True):
                    gerenciador = GerenciadorMovimentacao(df_movimentacoes)

                    if eh_ajuste:
                        linha_final, diferenca = gerenciador.preparar_linha_ajuste(
                            item=item,
                            qtd_contada=qtd_contada,
                            df_saldo_atual=saldo_dict,
                            motivo=motivo
                        )
                        if linha_final is None:
                            st.warning("Quantidade contada igual ao saldo do sistema. Nenhum ajuste necessário.")
                            st.stop()
                    else:
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