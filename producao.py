import streamlit as st
import pandas as pd
from database import Database
from logic_producao import GerenciadorProducao, GerenciadorStatusProducao, AnalisadorProducao, CalculadorCustos
from datetime import datetime
import pytz

fuso_brasil = pytz.timezone('America/Sao_Paulo')

@st.cache_data(ttl=60)
def carregar_dados_producao():
    return Database().producao()

@st.cache_data(ttl=300)
def carregar_receitas():
    return Database().receitas()

@st.cache_data(ttl=60)
def carregar_movimentacoes():
    return Database().movimentacoes()

@st.cache_data(ttl=300)
def carregar_precos():
    return Database().precos()


def renderizar_producao():
    st.title("🏗️ Gestão de Produção")

    if 'mostrar_form_producao' not in st.session_state:
        st.session_state.mostrar_form_producao = False
    if 'mostrar_busca_producao' not in st.session_state:
        st.session_state.mostrar_busca_producao = False

    # Trata resultado do callback fora do on_click
    if st.session_state.get('_producao_confirmada'):
        st.success(st.session_state.pop('_producao_msg', ''))
        st.session_state._producao_confirmada = False
        st.cache_data.clear()
        st.rerun()
    if st.session_state.get('_producao_erro'):
        st.error(f"Erro ao confirmar: {st.session_state.pop('_producao_erro')}")

    df_producao = carregar_dados_producao()
    df_receitas = carregar_receitas()
    df_movimentacoes = carregar_movimentacoes()
    df_precos = carregar_precos()

    # --- DASHBOARD ---
    st.subheader("📋 Ordens de Produção")

    if not df_producao.empty:
        # Normaliza nome da coluna status (SQL retorna minúsculo)
        df_producao.columns = [c.lower() for c in df_producao.columns]

        pendentes = df_producao[df_producao['status'] == 'Pendente'].copy()
        concluidos = df_producao[df_producao['status'].isin(['Concluído', 'Entregue'])].copy()

        m1, m2, m3 = st.columns(3)
        m1.metric("Pendentes", len(pendentes))
        m2.metric("Concluídos", len(concluidos))
        m3.metric("Total", len(df_producao))

        st.divider()

        # --- PENDENTES ---
        if not pendentes.empty:
            st.markdown("### ⏳ Aguardando produção")

            # Usa a view do SQL que já traz custo estimado
            db = Database()
            df_pendentes_sql = db.ordens_pendentes()

            for _, row in df_pendentes_sql.iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([4, 2, 2, 2])

                    with c1:
                        st.markdown(f"**{row['produto']}**")
                        st.caption(f"Pedido `{row['id_origem']}`")
                        custo = row.get('custo_estimado', 0) or 0
                        st.caption(f"Custo estimado: R$ {custo:.2f}")

                    with c2:
                        st.markdown("**Qtd**")
                        st.markdown(f"{int(float(row['quantidade']))} un")

                    with c3:
                        st.markdown("**Entrega**")
                        st.markdown(f"{row.get('data_entrega', '—')}")

                    with c4:
                        st.button(
                            "✅ Concluir",
                            key=f"concluir_{row['id_producao']}",
                            use_container_width=True,
                            type="primary",
                            on_click=_confirmar_producao,
                            args=(row, df_movimentacoes, df_receitas)
                        )

            st.divider()

        # --- HISTÓRICO ---
        if not concluidos.empty:
            with st.expander(f"✅ Histórico de produções concluídas ({len(concluidos)})"):
                st.dataframe(
                    concluidos.sort_values('data_producao', ascending=False),
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
        produtos_disponiveis = sorted(df_receitas['produto'].dropna().unique().tolist())

        st.markdown("### 🍞 Registrar produção manual")
        st.info("Use para registrar produções avulsas não vinculadas a um pedido.")

        c1, c2 = st.columns(2)
        with c1:
            produto = st.selectbox("Produto", produtos_disponiveis, key="sel_prod_manual")
            quantidade = st.number_input("Quantidade produzida", min_value=1, step=1,
                                          value=1, key="qtd_prod_manual")
        with c2:
            data_entrega = st.date_input("Data de entrega", key="data_prod_manual")
            id_ref = st.text_input("Referência (opcional)", placeholder="Ex: Fornada extra",
                                    key="ref_prod_manual")
        # Preview de custo via SQL
        db = Database()
        df_custo = db.custo_receita(produto, quantidade)
        if not df_custo.empty:
            st.markdown("**Insumos e custos estimados:**")
            st.dataframe(
                df_custo[['item_insumo', 'qtd_total', 'unidade', 'custo_total']],
                use_container_width=True,
                hide_index=True
            )
            total = db.custo_total_receita(produto, quantidade)
            if total > 0:
                st.metric("Custo total estimado", f"R$ {total:.2f}")
            else:
                st.warning("⚠️ Alguns insumos estão sem preço cadastrado.")

        with st.form("confirmar_producao"):
            btn1, btn2 = st.columns(2)
            with btn1:
                if st.form_submit_button("✅ Confirmar produção", use_container_width=True):
                    try:
                        db = Database()
                        calc = CalculadorCustos(df_precos)
                        produtor = GerenciadorProducao(df_receitas, df_movimentacoes)
                        id_ref_final = st.session_state.get("ref_prod_manual", "") or "Avulso"
                        produto_final = st.session_state.get("sel_prod_manual", produto)
                        quantidade_final = st.session_state.get("qtd_prod_manual", quantidade)
                        data_final = st.session_state.get("data_prod_manual", data_entrega)

                        linhas_mov, erro = produtor.gerar_movimentacoes(
                            id_ref_final, produto_final, quantidade_final, calculador=calc
                        )
                        if erro:
                            st.error(erro)
                        else:
                            db.salvar_movimentacoes_lote(linhas_mov)

                            ordem = produtor.gerar_ordem_producao(
                                id_ref_final, produto_final, quantidade_final,
                                data_final.isoformat()
                            )
                            db.salvar_ordem_producao({
                                "id_pedido": ordem[0],
                                "data_producao": ordem[1],
                                "produto": ordem[2],
                                "quantidade": ordem[3],
                                "data_entrega": ordem[4],
                                "status": "Concluído",
                            })
                            
                            st.success(f"Produção registrada!")
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

        c1, c2 = st.columns(2)
        with c1:
            data_ini = st.date_input("De", key="prod_data_ini")
        with c2:
            data_fim = st.date_input("Até", key="prod_data_fim")

        analisador = AnalisadorProducao(df_producao)
        df_filtrado = analisador.filtrar_por_periodo(data_ini, data_fim)
        st.metric("Produções encontradas", len(df_filtrado))
        st.dataframe(
            df_filtrado.sort_values('data_producao', ascending=False),
            use_container_width=True,
            hide_index=True
        )


def _confirmar_producao(row, df_movimentacoes, df_receitas):
    try:
        db = Database()
        calc = CalculadorCustos(db.precos())

        gestor = GerenciadorStatusProducao(
            pd.DataFrame(),
            df_movimentacoes,
            calculador=calc,
            df_receitas=df_receitas
        )
        linha_mov, novo_status = gestor.confirmar_producao(
            id_producao=row['id_producao'],
            nome_produto=row['produto'],
            quantidade=int(float(row['quantidade'])),
            data_entrega=row.get('data_entrega', '')
        )

        # Salva ENT-P no estoque
        ok_mov = db.salvar_movimentacao(linha_mov)
        if not ok_mov:
            st.session_state._producao_erro = "Falha ao salvar movimentação no estoque."
            return

        # Atualiza status
        ok_status = db.atualizar_status_producao(row['id_producao'], novo_status)
        if not ok_status:
            st.session_state._producao_erro = f"Falha ao atualizar status. ID: {row['id_producao']}"
            return

        st.session_state._producao_confirmada = True
        st.session_state._producao_msg = f"✅ {row['produto']} marcado como {novo_status}!"

    except Exception as e:
        st.session_state._producao_erro = f"Exceção: {type(e).__name__}: {e}"