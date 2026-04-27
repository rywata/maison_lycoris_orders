import streamlit as st
import pandas as pd
from database import Database
from logic_producao import GerenciadorProducao, AnalisadorProducao


@st.cache_data(ttl=60)
def carregar_dados_producao():
    try:
        db = Database()
        aba = db.conectar_aba("Controle", "Produção")
        dados = aba.get_all_records()
        df = pd.DataFrame(dados)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao acessar aba de Produção: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def carregar_receitas():
    try:
        db = Database()
        aba = db.conectar_aba("Controle", "Receitas Python")
        dados = aba.get_all_records()
        df = pd.DataFrame(dados)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao acessar aba de Receitas: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def carregar_movimentacoes():
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

@st.cache_data(ttl=300)
def carregar_precos():
    try:
        db = Database()
        aba = db.conectar_aba("Controle", "Preço Insumos")
        dados = aba.get_all_records(value_render_option='UNFORMATTED_VALUE')
        df = pd.DataFrame(dados)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao acessar Preço Insumos: {e}")
        return pd.DataFrame()

def renderizar_producao():
    st.title("🏗️ Gestão de Produção")

    if 'mostrar_form_producao' not in st.session_state:
        st.session_state.mostrar_form_producao = False
    if 'mostrar_busca_producao' not in st.session_state:
        st.session_state.mostrar_busca_producao = False

    df_producao = carregar_dados_producao()
    df_receitas = carregar_receitas()
    df_movimentacoes = carregar_movimentacoes()
    df_precos = carregar_precos()


    # --- DASHBOARD DE ORDENS PENDENTES ---
    st.subheader("📋 Ordens de Produção")

    if not df_producao.empty:
        pendentes = df_producao[df_producao['Status'] == 'Pendente'].copy()
        concluidos = df_producao[df_producao['Status'].isin(['Concluído', 'Entregue'])].copy()

        # Métricas rápidas
        m1, m2, m3 = st.columns(3)
        m1.metric("Pendentes", len(pendentes))
        m2.metric("Concluídos", len(concluidos))
        m3.metric("Total", len(df_producao))

        st.divider()

        # --- PENDENTES ---
        if not pendentes.empty:
            st.markdown("### ⏳ Aguardando produção")

            for _, row in pendentes.iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([4, 2, 2, 2])

                    with c1:
                        st.markdown(f"**{row['Produto']}**")
                        st.caption(f"Pedido `{row['ID Pedido']}`")
                        if not df_receitas.empty and not df_precos.empty:
                            from logic_producao import CalculadorCustos, GerenciadorProducao
                            produtor = GerenciadorProducao(df_receitas, df_movimentacoes)
                            calc = CalculadorCustos(df_precos)
                            insumos = produtor.calcular_insumos(
                                row['Produto'], int(float(row['Quantidade']))
                            )
                            if insumos:
                                _, total = calc.calcular_custo_receita(insumos)
                                st.caption(f"Custo estimado: R$ {total:.2f}")

                    with c2:
                        st.markdown("**Qtd**")
                        st.markdown(f"{int(float(row['Quantidade']))} un")

                    with c3:
                        st.markdown("**Entrega**")
                        data_fmt = row.get('Data Entrega', '—')
                        st.markdown(f"{data_fmt}")

                    with c4:
                        st.button(
                            "✅ Concluir",
                            key=f"concluir_{row['ID Produção']}",
                            use_container_width=True,
                            type="primary",
                            on_click=_confirmar_producao,
                            args=(row, df_movimentacoes)
                        )

            st.divider()

        # --- CLUÍDOS RECENTES ---
        if not concluidos.empty:
            with st.expander(f"✅ Histórico de produções concluídas ({len(concluidos)})"):
                st.dataframe(
                    concluidos.sort_values('Data Produção', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )

    else:
        st.info("Nenhuma ordem de produção registrada. Elas aparecem aqui quando um pedido é finalizado.")

    st.divider()

    # --- BOTÕES DE AÇÃO ---
    st.subheader("Ações")

    if st.button("🍞 Registrar Produção Manual", use_container_width=True):
        st.session_state.mostrar_form_producao = not st.session_state.mostrar_form_producao
        st.session_state.mostrar_busca_producao = False

    if st.button("🔍 Buscar Produções", use_container_width=True):
        st.session_state.mostrar_busca_producao = not st.session_state.mostrar_busca_producao
        st.session_state.mostrar_form_producao = False

    # --- FORMULÁRIO DE PRODUÇÃO MANUAL ---
    if st.session_state.mostrar_form_producao and not df_receitas.empty:
        st.divider()
        produtos_disponiveis = sorted(df_receitas['Produto'].dropna().unique().tolist())

        with st.form("form_producao"):
            st.markdown("### 🍞 Registrar produção manual")
            st.info("Use para registrar produções avulsas não vinculadas a um pedido.")

            c1, c2 = st.columns(2)
            with c1:
                produto = st.selectbox("Produto", produtos_disponiveis)
                quantidade = st.number_input("Quantidade produzida", min_value=1, step=1)
            with c2:
                data_entrega = st.date_input("Data de entrega")
                id_ref = st.text_input("Referência (opcional)", placeholder="Ex: Fornada extra")

            if produto:
                produtor = GerenciadorProducao(df_receitas, df_movimentacoes)
                calc = CalculadorCustos(df_precos)
                insumos = produtor.calcular_insumos(produto, quantidade)
                if insumos:
                    df_custos, total = calc.calcular_custo_receita(insumos)
                    st.markdown("**Insumos e custos estimados:**")
                    st.dataframe(
                        df_custos[['Item', 'Quantidade', 'Unidade', 'Custo Total (R$)']],
                        use_container_width=True,
                        hide_index=True
                    )
                    st.metric("Custo total estimado", f"R$ {total:.2f}")

            btn1, btn2 = st.columns(2)
            with btn1:
                if st.form_submit_button("✅ Confirmar produção", use_container_width=True):
                    try:
                        db = Database()
                        aba_mov = db.conectar_aba("Controle", "Movimentações")
                        aba_prod = db.conectar_aba("Controle", "Produção")
                        aba_precos_raw = db.conectar_aba("Controle", "Preço Insumos")

                        df_precos_raw = pd.DataFrame(
                            aba_precos_raw.get_all_records(value_render_option='UNFORMATTED_VALUE')
                        )
                        from logic_producao import CalculadorCustos
                        calc = CalculadorCustos(df_precos_raw)

                        produtor = GerenciadorProducao(df_receitas, df_movimentacoes)
                        id_ref_final = id_ref if id_ref else "Avulso"

                        linhas_mov, erro = produtor.gerar_movimentacoes(
                            id_ref_final, produto, quantidade, calculador=calc
                        )
                        if erro:
                            st.error(erro)
                        else:
                            ordem = produtor.gerar_ordem_producao(
                                id_ref_final, produto, quantidade, data_entrega.isoformat()
                            )
                            ordem[-1] = "Concluído"
                            aba_prod.append_row(ordem)
                            aba_mov.append_rows(linhas_mov, value_input_option='USER_ENTERED')
                            st.success(f"Produção de {quantidade}x {produto} registrada!")
                            st.session_state.mostrar_form_producao = False
                            st.cache_data.clear()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar produção: {e}")

            with btn2:
                if st.form_submit_button("❌ Cancelar", use_container_width=True):
                    st.session_state.mostrar_form_producao = False
                    st.rerun()

    # --- BUSCA ---
    if st.session_state.mostrar_busca_producao and not df_producao.empty:
        st.divider()
        analisador = AnalisadorProducao(df_producao)

        c1, c2 = st.columns(2)
        with c1:
            data_ini = st.date_input("De", key="prod_data_ini")
        with c2:
            data_fim = st.date_input("Até", key="prod_data_fim")

        df_filtrado = analisador.filtrar_por_periodo(data_ini, data_fim)
        st.metric("Produções encontradas", len(df_filtrado))
        st.dataframe(
            df_filtrado.sort_values('Data Produção', ascending=False),
            use_container_width=True, hide_index=True
        )


def _confirmar_producao(row, df_movimentacoes):
    try:
        from logic_producao import GerenciadorStatusProducao, CalculadorCustos

        db = Database()
        aba_mov = db.conectar_aba("Controle", "Movimentações")
        aba_prod = db.conectar_aba("Controle", "Produção")
        aba_precos = db.conectar_aba("Controle", "Preço Insumos")

        df_precos = pd.DataFrame(aba_precos.get_all_records(value_render_option='UNFORMATTED_VALUE'))
        calc = CalculadorCustos(df_precos)

        gestor = GerenciadorStatusProducao(pd.DataFrame(), df_movimentacoes, calc)
        linha_mov, novo_status = gestor.confirmar_producao(
            id_producao=row['ID Produção'],
            nome_produto=row['Produto'],
            quantidade=int(float(row['Quantidade'])),
            data_entrega=row.get('Data Entrega', '')
        )

        aba_mov.append_row(linha_mov)

        todos = aba_prod.get_all_values()
        headers = todos[0]
        col_id = headers.index('ID Produção') + 1
        col_status = headers.index('Status') + 1

        for i, linha in enumerate(todos[1:], start=2):
            if linha[col_id - 1] == row['ID Produção']:
                aba_prod.update_cell(i, col_status, novo_status)
                break

        st.success(f"✅ {row['Produto']} marcado como {novo_status}!")
        st.cache_data.clear()
        st.rerun()

    except Exception as e:
        st.error(f"Erro ao confirmar produção: {e}")