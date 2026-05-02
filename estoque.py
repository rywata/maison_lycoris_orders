import streamlit as st
import pandas as pd
from database import Database
from logic_estoque import GerenciadorMovimentacao as GestorRegras
from datetime import datetime
import pytz

fuso_brasil = pytz.timezone('America/Sao_Paulo')

@st.cache_data(ttl=60)
def carregar_movimentacoes():
    return Database().movimentacoes()

@st.cache_data(ttl=300)
def carregar_cadastro_insumos():
    return Database().insumos()

def renderizar_estoque():
    st.title("📦 Gestão de Estoque")

    df_movimentacoes = carregar_movimentacoes()
    df_cadastro = carregar_cadastro_insumos()

    if 'mostrar_form' not in st.session_state:
        st.session_state.mostrar_form = False
    if 'mostrar_busca' not in st.session_state:
        st.session_state.mostrar_busca = False

    # --- SALDOS ATUAIS ---
    db = Database()
    df_saldo = db.saldo_estoque()

    if df_saldo.empty:
        st.info("Nenhuma movimentação de estoque registrada.")
    else:
        st.subheader("Saldos Atuais")
        st.dataframe(df_saldo, use_container_width=True, hide_index=True)

    # Estoque crítico
    df_critico = db.estoque_critico()
    if not df_critico.empty:
        st.warning(f"⚠️ {len(df_critico)} item(ns) abaixo do estoque mínimo")
        with st.expander("Ver itens críticos"):
            st.dataframe(df_critico, use_container_width=True, hide_index=True)

    st.divider()

    # --- BOTÕES DE AÇÃO ---
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

    if st.button("🔍 Buscar Movimentações", use_container_width=True):
        st.session_state.mostrar_busca = not st.session_state.mostrar_busca
        st.session_state.mostrar_form = False

    # --- PAINEL DE BUSCA ---
    if st.session_state.mostrar_busca:
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_item = st.text_input("Filtrar por item", placeholder="Ex: Farinha")
        with col2:
            tipos_disponiveis = ["Todos"]
            if not df_movimentacoes.empty and 'tipo' in df_movimentacoes.columns:
                tipos_disponiveis += sorted(df_movimentacoes['tipo'].dropna().unique().tolist())
            filtro_tipo = st.selectbox("Tipo de movimentação", tipos_disponiveis)
        with col3:
            filtro_data = st.date_input("Data início", value=None)

        # Filtros direto no Supabase
        query_filtros = {}
        if filtro_tipo != "Todos":
            query_filtros["tipo"] = filtro_tipo

        df_filtrado = db.movimentacoes(filtros=query_filtros if query_filtros else None)

        # Filtros que o Supabase não faz facilmente
        if filtro_item and not df_filtrado.empty:
            df_filtrado = df_filtrado[
                df_filtrado['item'].str.contains(filtro_item, case=False, na=False)
            ]
        if filtro_data and not df_filtrado.empty:
            df_filtrado = df_filtrado[
                pd.to_datetime(df_filtrado['data_mov']) >= pd.Timestamp(filtro_data)
            ]

        st.metric("Registros encontrados", len(df_filtrado))

        if not df_filtrado.empty:
            itens_unicos = df_filtrado['item'].dropna().unique()
            if len(itens_unicos) == 1:
                un = df_filtrado['unidade_medida'].iloc[0]
                ent = df_filtrado[df_filtrado['quantidade'] > 0]['quantidade'].sum()
                sai = df_filtrado[df_filtrado['quantidade'] < 0]['quantidade'].sum()
                m1, m2, m3 = st.columns(3)
                m1.metric("Entradas", f"{ent:.3f} {un}")
                m2.metric("Saídas", f"{abs(sai):.3f} {un}")
                m3.metric("Saldo no período", f"{ent + sai:.3f} {un}")
            else:
                st.caption("Totais por item — unidades diferentes não podem ser somadas.")
                resumo = (
                    df_filtrado.groupby(['item', 'unidade_medida'])['quantidade']
                    .sum().reset_index()
                    .rename(columns={'item': 'Item', 'unidade_medida': 'Unidade', 'quantidade': 'Saldo'})
                )
                st.dataframe(resumo, use_container_width=True, hide_index=True)

            st.dataframe(
                df_filtrado.sort_values('data_mov', ascending=False),
                use_container_width=True,
                hide_index=True
            )

    # --- FORMULÁRIO DE MOVIMENTAÇÃO ---
    if st.session_state.mostrar_form:
        tipo = st.session_state.tipo_mov
        eh_ajuste = tipo in ("ENT-A", "SAI-A")
        st.divider()

        with st.form("form_movimentacao"):
            if eh_ajuste:
                st.markdown("### 🛠️ Ajuste de estoque")
                st.info("Informe a quantidade **real contada**. O sistema calcula a diferença automaticamente.")

                saldo_dict = df_saldo.set_index('item')['saldo'].to_dict() if not df_saldo.empty else {}
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

                gestor = GestorRegras(df_cadastro.to_dict('records')) if not df_cadastro.empty else None
                itens_cadastrados = sorted(df_cadastro['item'].dropna().tolist()) if not df_cadastro.empty else []

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
                                                  help="Em unidades de compra. Ex: 2 sacos")
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
                    now = datetime.now(fuso_brasil)

                    if eh_ajuste:
                        saldo_atual = saldo_dict.get(item, 0)
                        diferenca = qtd_contada - saldo_atual
                        if diferenca == 0:
                            st.warning("Quantidade igual ao saldo. Nenhum ajuste necessário.")
                            st.stop()
                        codigo = "ENT-A" if diferenca > 0 else "SAI-A"
                        qtd_final = abs(diferenca)
                        lote_final = f"Ajuste: {motivo}"
                        un_final = ""
                        un_compra_final = ""
                        custo_final = 0.0
                        validade_final = None
                    else:
                        codigo = tipo
                        qtd_final = qtd
                        lote_final = lote
                        un_final = un_medida
                        un_compra_final = un_compra
                        custo_final = custo / fator if fator else custo
                        validade_final = validade.isoformat() if validade else None

                    qtd_sinal = -abs(qtd_final) if codigo.startswith("SAI") else abs(qtd_final)

                    linha = {
                        "id_mov": f"{'1' if codigo.startswith('ENT') else '2'}{now.strftime('%Y%m%d%H%M%S')}",
                        "data_mov": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "tipo": codigo,
                        "item": item,
                        "quantidade": qtd_sinal,
                        "unidade_medida": un_final,
                        "unidade_compra": un_compra_final,
                        "validade": validade_final,
                        "lote": lote_final,
                        "custo_unitario": round(custo_final, 6),
                        "custo_total": round(abs(qtd_final) * custo_final, 4),
                    }

                    if db.salvar_movimentacao(linha):
                        st.success(f"Movimentação registrada! ID: {linha['id_mov']}")
                        st.session_state.mostrar_form = False
                        st.cache_data.clear()
                        st.rerun()

            with btn_col2:
                if st.form_submit_button("❌ Cancelar", use_container_width=True):
                    st.session_state.mostrar_form = False
                    st.rerun()