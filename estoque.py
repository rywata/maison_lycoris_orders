import streamlit as st
import pandas as pd
from database import Database
from logic_estoque import AnalisadorEstoque, GerenciadorMovimentacao, BuscaEstoque
from datetime import datetime

@st.cache_data(ttl=300)
def carregar_cadastro_insumos():
    try:
        db = Database()
        aba = db.conectar_aba("Controle", "Cadastro de Insumos")
        dados = aba.get_all_records()
        df = pd.DataFrame(dados)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao acessar Cadastro de Insumos: {e}")
        return pd.DataFrame()

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
    df_cadastro = carregar_cadastro_insumos()

    # --- SALDOS ATUAIS ---
    if df_movimentacoes.empty:
        st.info("Nenhuma movimentação de estoque registrada.")
    else:
        analisador = AnalisadorEstoque(df_movimentacoes)
        st.subheader("Saldos Atuais")
        st.dataframe(analisador.saldo_atual, use_container_width=True)

    st.divider()

    # --- AÇÕES ---
    st.subheader("Ações")

    col1, col2, col3 = st.columns(3)
    if col1.button("📥 Compra (ENT-C)", use_container_width=True):
        st.session_state.tipo_mov = "ENT-C"
        st.session_state.mostrar_form = True
        st.session_state.mostrar_busca = False
    if col2.button("🏗️ Produção (SAI-P)", use_container_width=True):
        st.session_state.tipo_mov = "SAI-P"
        st.session_state.mostrar_form = True
        st.session_state.mostrar_busca = False
    if col3.button("🍞 Entrada Prod (ENT-P)", use_container_width=True):
        st.session_state.tipo_mov = "ENT-P"
        st.session_state.mostrar_form = True
        st.session_state.mostrar_busca = False

    col4, col5, col6 = st.columns(3)
    if col4.button("💰 Venda (SAI-V)", use_container_width=True):
        st.session_state.tipo_mov = "SAI-V"
        st.session_state.mostrar_form = True
        st.session_state.mostrar_busca = False
    if col5.button("🛠️ Ajuste Entrada (ENT-A)", use_container_width=True):
        st.session_state.tipo_mov = "ENT-A"
        st.session_state.mostrar_form = True
        st.session_state.mostrar_busca = False
    if col6.button("🛠️ Ajuste Saída (SAI-A)", use_container_width=True):
        st.session_state.tipo_mov = "SAI-A"
        st.session_state.mostrar_form = True
        st.session_state.mostrar_busca = False

    # Botão de busca separado, ocupa linha própria
    if st.button("🔍 Buscar Movimentações", use_container_width=True):
        st.session_state.mostrar_busca = not st.session_state.get("mostrar_busca", False)
        st.session_state.mostrar_form = False

    # --- PAINEL DE BUSCA ---
    if st.session_state.get("mostrar_busca") and not df_movimentacoes.empty:
        st.divider()
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

    # --- FORMULÁRIO DE MOVIMENTAÇÃO ---
    if st.session_state.get("mostrar_form"):
        tipo = st.session_state.tipo_mov
        eh_ajuste = tipo in ("ENT-A", "SAI-A")
        st.divider()

        with st.form("form_movimentacao"):
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

            else:
                st.markdown(f"### Registro: **{tipo}**")
                c1, c2 = st.columns(2)

                from logic_estoque import GestorRegras
                gestor = GestorRegras(df_cadastro.to_dict('records')) if not df_cadastro.empty else None

                itens_cadastrados = sorted(df_cadastro['Item'].dropna().tolist()) if not df_cadastro.empty else []

                with c1:
                    if itens_cadastrados:
                        item = st.selectbox("Item", ["(digitar manualmente)"] + itens_cadastrados)
                        if item == "(digitar manualmente)":
                            item = st.text_input("Nome do item")
                    else:
                        item = st.text_input("Item")

                    un_compra_default = gestor.obter_unidade_compra(item) if gestor and item else ""
                    un_receita_default = gestor.obter_unidade_receita(item) if gestor and item else ""
                    fator = gestor.obter_fator(item) if gestor and item else 1

                    qtd_compra = st.number_input("Quantidade comprada", min_value=0.0, step=1.0, format="%.0f",
                                                  help=f"Em unidades de compra. Ex: 2 sacos")
                    un_compra = st.text_input("Unidade de Compra", value=un_compra_default)

                with c2:
                    un_medida = st.text_input("Unidade de Receita", value=un_receita_default)
                    qtd_convertida = qtd_compra * fator
                    st.metric("Quantidade convertida", f"{qtd_convertida:.0f} {un_medida}",
                              help="Calculado automaticamente pelo fator de conversão")
                    validade = st.date_input("Validade", value=None)
                    lote = st.text_input("Lote")
                    custo = st.number_input("Custo Unitário (por unidade de compra)", min_value=0.0, step=0.01)

                qtd = qtd_convertida

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