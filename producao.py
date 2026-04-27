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


def renderizar_producao():
    st.title("🏗️ Gestão de Produção")

    if 'mostrar_form_producao' not in st.session_state:
        st.session_state.mostrar_form_producao = False
    if 'mostrar_busca_producao' not in st.session_state:
        st.session_state.mostrar_busca_producao = False

    df_producao = carregar_dados_producao()
    df_receitas = carregar_receitas()
    df_movimentacoes = carregar_movimentacoes()

    # --- PEDIDOS PENDENTES DE CONFIRMAÇÃO ---
    if not df_producao.empty:
        analisador = AnalisadorProducao(df_producao)

        pendentes = df_producao[df_producao['Status'] == 'Pendente']

        if not pendentes.empty:
            st.subheader("⏳ Aguardando confirmação de produção")
            st.caption("Confirme quando o produto estiver pronto. O estoque será atualizado automaticamente.")

            for _, row in pendentes.iterrows():
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                    c1.write(f"**{row['Produto']}**")
                    c2.write(f"Pedido `{row['ID Pedido']}`")
                    c3.write(f"{int(float(row['Quantidade']))} un")
                    c4.write(f"Entrega: {row['Data Entrega']}")

                    if c5.button("✅ Confirmar", key=f"confirmar_{row['ID Produção']}",
                                 use_container_width=True):
                        try:
                            from logic_producao import GerenciadorStatusProducao
                            gestor_status = GerenciadorStatusProducao(df_producao, df_movimentacoes)

                            linha_mov, novo_status = gestor_status.confirmar_producao(
                                id_producao=row['ID Produção'],
                                nome_produto=row['Produto'],
                                quantidade=int(float(row['Quantidade'])),
                                data_entrega=row['Data Entrega']
                            )

                            db = Database()
                            aba_mov = db.conectar_aba("Controle", "Movimentações")
                            aba_prod = db.conectar_aba("Controle", "Produção")

                            # Salva ENT-P no estoque
                            aba_mov.append_row(linha_mov)

                            # Atualiza status na aba Produção
                            # Encontra a linha na planilha pelo ID
                            todos = aba_prod.get_all_values()
                            headers = todos[0]
                            col_id = headers.index('ID Produção') + 1
                            col_status = headers.index('Status') + 1

                            for i, linha in enumerate(todos[1:], start=2):
                                if linha[col_id - 1] == row['ID Produção']:
                                    aba_prod.update_cell(i, col_status, novo_status)
                                    break

                            st.success(f"Produção de {row['Produto']} confirmada! Status: {novo_status}")
                            st.cache_data.clear()
                            st.rerun()

                        except Exception as e:
                            st.error(f"Erro ao confirmar produção: {e}")

            st.divider()

        # --- RESUMO GERAL ---
        st.subheader("Produção por produto")
        st.dataframe(analisador.producao_por_produto, use_container_width=True, hide_index=True)

    else:
        st.info("Nenhuma produção registrada ainda.")

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
                insumos = produtor.calcular_insumos(produto, quantidade)
                if insumos:
                    st.markdown("**Insumos que serão baixados do estoque:**")
                    st.dataframe(pd.DataFrame(insumos, columns=['Item', 'Quantidade', 'Unidade']),
                                 use_container_width=True, hide_index=True)

            btn1, btn2 = st.columns(2)
            with btn1:
                if st.form_submit_button("✅ Confirmar produção", use_container_width=True):
                    try:
                        db = Database()
                        aba_mov = db.conectar_aba("Controle", "Movimentações")
                        aba_prod = db.conectar_aba("Controle", "Produção")

                        produtor = GerenciadorProducao(df_receitas, df_movimentacoes)
                        id_ref_final = id_ref if id_ref else "Avulso"

                        linhas_mov, erro = produtor.gerar_movimentacoes(id_ref_final, produto, quantidade)
                        if erro:
                            st.error(erro)
                        else:
                            ordem = produtor.gerar_ordem_producao(
                                id_ref_final, produto, quantidade, data_entrega.isoformat()
                            )
                            # Produção manual já nasce como Concluído
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
            use_container_width=True,
            hide_index=True
        )