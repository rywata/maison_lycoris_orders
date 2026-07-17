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
        "Pão de Leite": 15.0,
        "Pão Integral": 17.0,
        "Pão Semi Integral": 17.0,
        "Shokupan": 17.0,
        "Pastel de Nata": 7.0,
        "Pastel de Maçã": 7.0,
        "Pastel de Ricota com Ervas Finas": 7.0,
        "Pastel de Frango com Parmesão": 7.0,
        "Pastel de Amendoim": 7.0,
        "Croissant Amanteigado": 8.0,
        "Brownie": 8.0
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
        
        itens_editados = df_editado.dropna(subset=['produto']).to_dict('records')
        if itens_editados != st.session_state.carrinho:
            st.session_state.carrinho = itens_editados
    
        for item in st.session_state.carrinho:
            if 'qtd' in item and 'preco_unitario' in item:
                item['subtotal'] = item['qtd'] * item['preco_unitario']

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
                
                # --- ETAPA 1: GERAÇÃO DO IDENTIFICADOR DE NEGÓCIO (SMART ID) ---
                # ID que será usado no Código de Barras.
                data_slug = datetime.now(fuso_brasil).strftime("%Y%m")
                ts_pedido = datetime.now(fuso_brasil).strftime("%H%M%S")
                id_origem_smart = f"PED-{data_slug}-{ts_pedido}"

                db = Database()

                try:
                    # --- ETAPA 2: PREPARAÇÃO DOS DADOS E MOTORES DE CÁLCULO ---
                    # Carregamos as tabelas necessárias para calcular custos e receitas.
                    df_receitas = db.receitas()
                    df_precos = db.precos()
                    df_mov = db.movimentacoes()
                    
                    calc = CalculadorCustos(df_precos)
                    produtor = GerenciadorProducao(df_receitas, df_mov)

                    linhas_pedido_para_banco = []
                    estoque_temporario = [] 

                    # --- ETAPA 3: LOOP DE PROCESSAMENTO E CÁLCULO DE CUSTOS ---
                    for _, row in df_editado.iterrows():
                        linhas_mov, erro = produtor.gerar_movimentacoes(
                            id_pedido=id_origem_smart, 
                            nome_produto=row['produto'].upper(),
                            quantidade=int(row['qtd']),
                            calculador=calc
                        )
                        
                        # Extração do custo total da linha
                        custo_unit_calc = float(linhas_mov[-1]['custo_unitario']) if not erro and linhas_mov else 0.0
                        custo_total_item = custo_unit_calc * int(row['qtd'])

                        # Cálculos de preço e descontos (Combo Maison Lycoris)
                        tem_desc = meu_carrinho.tem_desconto and row['produto'] in codigo_pasteis
                        bruto = float(row['qtd'] * row['preco_unitario'])
                        valor_desconto = bruto * 0.15 if tem_desc else 0.0

                        # Montagem do dicionário que irá para a tabela 'pedidos'
                        linhas_pedido_para_banco.append({
                            "id_origem": id_origem_smart,     # Chave de Negócio (Barcode)
                            "nome_cliente": nome_cliente,
                            "data_entrega": data_sel.isoformat(),
                            "horario_entrega": horario_sel.strftime("%H:%M"),
                            "produto": row['produto'],
                            "quantidade": int(row['qtd']),
                            "total_bruto": bruto,
                            "desconto": valor_desconto,
                            "total_liquido": bruto - valor_desconto,
                            "custo_total": custo_total_item,
                            "data_pedido": datetime.now(fuso_brasil).strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        estoque_temporario.append(linhas_mov)

                    # --- ETAPA 4: PERSISTÊNCIA DO PEDIDO E CAPTURA DE UUIDs ---
                    pedidos_confirmados = db.inserir_lote_retornando("pedidos", linhas_pedido_para_banco)

                    if not pedidos_confirmados:
                        st.error("Erro crítico: O banco de dados não retornou as confirmações de pedido.")
                        st.stop()

                    # --- ETAPA 5: VINCULAÇÃO TÉCNICA (UUID) E FINALIZAÇÃO DE PRODUÇÃO ---
                    todas_movimentacoes_finais = []
                    todas_ordens_producao = []

                    for i, pedido_db in enumerate(pedidos_confirmados):
                        uuid_tecnico = pedido_db['id_pedido']

                        for mov in estoque_temporario[i]:
                            mov['lote'] = id_origem_smart
                            mov['id_origem'] = id_origem_smart
                            mov['id_pedido'] = uuid_tecnico
                        todas_movimentacoes_finais.extend(estoque_temporario[i])

                        todas_ordens_producao.append({
                            "id_pedido": uuid_tecnico,
                            "id_origem": id_origem_smart,
                            "data_producao": datetime.now(fuso_brasil).strftime("%Y-%m-%d %H:%M:%S"),
                            "produto": pedido_db['produto'],
                            "quantidade": pedido_db['quantidade'],
                            "data_entrega": pedido_db['data_entrega'],
                            "horario_entrega": pedido_db.get('horario_entrega', ''),
                            "status": "Pendente"
                        })

                    # --- ETAPA 6: SALVAMENTO FINAL EM LOTE ---
                    if todas_movimentacoes_finais:
                        db.salvar_movimentacoes_lote(todas_movimentacoes_finais)
                    
                    if todas_ordens_producao:
                        db.salvar_ordens_lote(todas_ordens_producao)

                    # --- ETAPA 7: LIMPEZA DE INTERFACE E FEEDBACK ---
                    st.session_state.carrinho = []
                    st.session_state.pop("input_nome_cliente", None)
                    st.success(f"✅ Pedido {id_origem_smart} finalizado com sucesso!")
                    import time
                    time.sleep(1.5)
                    st.rerun()

                except Exception as e:
                    st.error(f"Ocorreu um erro no processamento: {str(e)}")
                    st.stop()