import streamlit as st
import pandas as pd
from datetime import datetime
from logic_pedidos import Carrinho
from database import Database, salvar_pedido
import pytz

fuso_brasil = pytz.timezone('America/Sao_Paulo')

def renderizar_novo_pedido():
    # --- 1. CONEXÃO ---
    @st.cache_resource
    def iniciar_conexao():
        db = Database() 
        return db.conectar_aba("Controle", "Pedidos")

    try:
        aba_pedidos = iniciar_conexao()
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return

    # --- 2. ESTADO E CARDÁPIO ---
    if 'carrinho' not in st.session_state: st.session_state.carrinho = []
    if 'pedido_enviado' not in st.session_state: st.session_state.pedido_enviado = False

    cardapio = {
        "Pão de Leite": 15.0, "Pão Integral": 17.0, "Pão Semi Integral": 17.0, "Shokupan": 17.0,
        "Pastel de Nata": 7.0, "Pastel de Maçã": 7.0, "Pastel de Ricota com Ervas Finas": 7.0, "Pastel de Frango com Parmesão": 7.0
    }
    codigo_pasteis = [k for k in cardapio.keys() if "Pastel" in k]

    # --- 3. DADOS DO CLIENTE ---
    st.header("📝 Novo Pedido")
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            nome_cliente = st.text_input("Nome do Cliente", placeholder="Ex: Zé Bedeu")
        with col2:
            data_sel = st.date_input("Data de Entrega", value=datetime.now(fuso_brasil), format="DD/MM/YYYY")

    # --- 4. ADICIONAR PRODUTOS ---
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
                novo_item = {
                    "produto": produto,
                    "qtd": qtd,
                    "preco_unitario": cardapio[produto],
                    "subtotal": qtd * cardapio[produto]
                }
                st.session_state.carrinho.append(novo_item)
                st.toast(f"{produto} adicionado!", icon="🛒")
            else:
                st.warning("Preencha o nome do cliente antes de adicionar itens!")
    
    # --- 5. EDITOR DO CARRINHO E EXECUçÂO ---
    if st.session_state.carrinho:
        st.divider()
        st.subheader("🛒 Revisão do Pedido")
        st.info("💡 Você pode alterar a quantidade ou excluir linhas (selecione a linha e aperte Delete).")
        
        df_carrinho = pd.DataFrame(st.session_state.carrinho)
        df_editado = st.data_editor(
            df_carrinho,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "produto": "Produto",
                "qtd": st.column_config.NumberColumn("Quantidade", min_value=1),
                "preco_unitario": st.column_config.NumberColumn("Preço Unit.", format="R$ %.2f", disabled=True),
                "subtotal": st.column_config.NumberColumn("Subtotal", format="R$ %.2f", disabled=True),
            },
            hide_index=True,
            key="editor_carrinho"
        )

        if st.button("🔄 Recalcular Totais"):
            st.session_state.carrinho = df_editado.to_dict('records')
            st.rerun()

        # --- CÁLCULO DE TOTAIS ---
        meu_carrinho = Carrinho(df_editado.to_dict('records'), codigo_pasteis)
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total a Pagar", f"R$ {meu_carrinho.total_final:.2f}")
        with c2:
            if meu_carrinho.desconto_total > 0:
                st.write(f"🎁 Desconto Combo: -R$ {meu_carrinho.desconto_total:.2f}")

        # --- 6. FINALIZAÇÃO ---
        col_cancelar, col_enviar = st.columns(2)
        
        with col_cancelar:
            if st.button("🗑️ Cancelar Pedido", use_container_width=True):
                st.session_state.carrinho = []
                st.rerun()

        with col_enviar:
            if st.button("🚀 FINALIZAR E ENVIAR", type="primary", use_container_width=True):
                id_p = datetime.now(fuso_brasil).strftime("%Y%m%d%H%M")
                dt_in = datetime.now(fuso_brasil).strftime("%Y-%m-%d %H:%M:%S")
                
                dados_para_planilha = []
                for _, row in df_editado.iterrows():
                    # Lógica de desconto individual para a planilha
                    tem_desc = meu_carrinho.tem_desconto and row['produto'] in codigo_pasteis
                    d_i = float((row['qtd'] * row['preco_unitario'] * 0.15) if tem_desc else 0.0)
                    bruto = float(row['qtd'] * row['preco_unitario'])
                    
                    dados_para_planilha.append([
                        id_p, 
                        nome_cliente, 
                        data_sel.isoformat(), 
                        row['produto'], 
                        int(row['qtd']), 
                        bruto, 
                        d_i, 
                        float(bruto - d_i), 
                        dt_in
                    ])
                
                if salvar_pedido(aba_pedidos, dados_para_planilha):
                    st.session_state.carrinho = [] 
                    st.success("✅ Pedido enviado com sucesso!")
                    import time
                    time.sleep(2)
                    st.rerun()