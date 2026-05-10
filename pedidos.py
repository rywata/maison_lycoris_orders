import streamlit as st
import pandas as pd
from datetime import datetime
from logic_pedidos import Carrinho
from logic_producao import GerenciadorProducao, CalculadorCustos
from database import Database
import pytz

fuso_brasil = pytz.timezone('America/Sao_Paulo')

def renderizar_novo_pedido():

    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []

    cardapio = {
        "Pão de Leite": 15.0, "Pão Integral": 17.0, "Pão Semi Integral": 17.0, "Shokupan": 17.0,
        "Pastel de Nata": 7.0, "Pastel de Maçã": 7.0, "Pastel de Ricota com Ervas Finas": 7.0,
        "Pastel de Frango com Parmesão": 7.0
    }
    codigo_pasteis = [k for k in cardapio.keys() if "Pastel" in k]

    # --- DADOS DO CLIENTE ---
    st.header("📝 Novo Pedido")

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            nome_cliente = st.text_input("Nome do Cliente", placeholder="Ex: Zé Bedeu",
                                          key="input_nome_cliente")
        with col2:
            data_sel = st.date_input("Data de Entrega", value=datetime.now(fuso_brasil),
                                      format="DD/MM/YYYY")
        with col3:
            if "horario_sel" not in st.session_state:       
                st.session_state.horario_sel = datetime.now(fuso_brasil).replace(
                    hour=9, minute=0, second=0
                ).time()
            horario_sel = st.time_input(
                'Horário de Entrega',
                value=st.session_state.horario_sel,
                key='horario_sel'
            )

    # --- ADICIONAR PRODUTOS ---
    st.divider()
    st.subheader("Adicionar Produtos")
    c_prod, c_qtd, c_add = st.columns([3, 1, 1])

    with c_prod:
        produto = st.selectbox("Selecione o Produto", list(cardapio.keys()))
    with c_qtd:
        qtd = st.number_input("Qtd", min_value=1, step=1)
    with c_add:
        st.write(" ")
        if st.button("➕ Adicionar", use_container_width=True):
            if nome_cliente:
                st.session_state.carrinho.append({
                    "produto": produto,
                    "qtd": qtd,
                    "preco_unitario": cardapio[produto],
                    "subtotal": qtd * cardapio[produto]
                })
                st.toast(f"{produto} adicionado!", icon="🛒")
            else:
                st.warning("Preencha o nome do cliente antes de adicionar itens!")

    # --- CARRINHO ---
    if st.session_state.carrinho:
        st.divider()
        st.subheader("🛒 Revisão do Pedido")
        st.info("💡 Você pode alterar a quantidade ou excluir linhas (selecione e aperte Delete).")

        df_carrinho = pd.DataFrame(st.session_state.carrinho)
        df_editado = st.data_editor(
            df_carrinho,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "produto": "Produto",
                "qtd": st.column_config.NumberColumn("Quantidade", min_value=1),
                "preco_unitario": st.column_config.NumberColumn("Preço Unit.", format="R$ %.2f",
                                                                  disabled=True),
                "subtotal": st.column_config.NumberColumn("Subtotal", format="R$ %.2f",
                                                           disabled=True),
            },
            hide_index=True,
            key="editor_carrinho"
        )

        if st.button("🔄 Recalcular Totais"):
            st.session_state.carrinho = df_editado.to_dict('records')
            st.rerun()

        meu_carrinho = Carrinho(df_editado.to_dict('records'), codigo_pasteis)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total a Pagar", f"R$ {meu_carrinho.total_final:.2f}")
        with c2:
            if meu_carrinho.desconto_total > 0:
                st.write(f"🎁 Desconto Combo: -R$ {meu_carrinho.desconto_total:.2f}")

        # --- FINALIZAÇÃO ---
        col_cancelar, col_enviar = st.columns(2)

        with col_cancelar:
            if st.button("🗑️ Cancelar Pedido", use_container_width=True):
                st.session_state.carrinho = []
                st.rerun()

        with col_enviar:
            if st.button("🚀 FINALIZAR E ENVIAR", type="primary", use_container_width=True):
                id_p = datetime.now(fuso_brasil).strftime("%Y%m%d%H%M")
                dt_in = datetime.now(fuso_brasil).strftime("%Y-%m-%d %H:%M:%S")
                db = Database()

                # --- DISPARA PRODUÇÃO E CÁLCULO DE CUSTOS ---
                try:
                    df_receitas = db.receitas()
                    df_precos = db.precos()
                    df_mov = db.movimentacoes()

                    calc = CalculadorCustos(df_precos)
                    produtor = GerenciadorProducao(df_receitas, df_mov)

                    todas_mov = []
                    todas_prod = []
                    linhas_pedido = [] 

                    for _, row in df_editado.iterrows():
                        # 1. Gera as movimentações (calcula o custo internamente)
                        linhas_mov, erro = produtor.gerar_movimentacoes(
                            id_pedido=id_p,
                            nome_produto=row['produto'].upper(),
                            quantidade=int(row['qtd']),
                            calculador=calc
                        )
                        
                        # 2. Captura o custo unitário da última linha (ENT-P)
                        custo_unit_calc = 0.0
                        if linhas_mov:
                            custo_unit_calc = float(linhas_mov[-1]['custo_unitario'])
                        
                        if erro:
                            st.warning(f"⚠️ {row['produto']}: {erro}. Estoque não movimentado.")
                            continue

                        todas_mov.extend(linhas_mov[:-1])

                        # 3. Cálculos Financeiros para a tabela de Pedidos
                        tem_desc = meu_carrinho.tem_desconto and row['produto'] in codigo_pasteis
                        bruto = float(row['qtd'] * row['preco_unitario'])
                        valor_desconto = bruto * 0.15 if tem_desc else 0.0
                        
                        faturamento_real = bruto - valor_desconto
                        custo_total_linha = custo_unit_calc * int(row['qtd'])

                        # 4. Monta a linha do pedido com o Lucro Líquido (Faturamento - Custo)
                        linhas_pedido.append({
                            "id_pedido": id_p,
                            "nome_cliente": nome_cliente,
                            "data_entrega": data_sel.isoformat(),
                            "horario_entrega": horario_sel.strftime("%H:%M"),
                            "produto": row['produto'],
                            "quantidade": int(row['qtd']),
                            "total_bruto": bruto,
                            "desconto": valor_desconto,
                            "total_liquido": faturamento_real - custo_total_linha, 
                            "custo_total": custo_total_linha,
                            "data_pedido": dt_in,
                        })

                        # 5. Gera a Ordem de Produção
                        ordem = produtor.gerar_ordem_producao(
                            id_pedido=id_p,
                            nome_produto=row['produto'],
                            quantidade=int(row['qtd']),
                            data_entrega=data_sel.isoformat()
                        )
                        todas_prod.append({
                            "id_producao": ordem[0],
                            "id_pedido": ordem[1],
                            "data_producao": ordem[2],
                            "produto": ordem[3],
                            "quantidade": ordem[4],
                            "data_entrega": ordem[5],
                            'horario_entrega': horario_sel.strftime("%H:%M"), 
                            "status": ordem[6],
                        })

                    # --- SALVAMENTO EM LOTE ---
                    if not db.salvar_pedido(linhas_pedido):
                        st.error("Erro ao salvar pedido.")
                        st.stop()
                        
                    if todas_mov:
                        db.salvar_movimentacoes_lote(todas_mov)
                    if todas_prod:
                        db.salvar_ordens_lote(todas_prod)

                except Exception as e:
                    st.warning(f"Erro ao processar pedido e produção: {e}")

                st.session_state.carrinho = []
                st.session_state.pop("input_nome_cliente", None)
                st.success("✅ Pedido enviado! Lucro e custos registrados.")
                import time
                time.sleep(2)
                st.rerun()