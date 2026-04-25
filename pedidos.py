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

    # --- 3. INTERFACE DE SUCESSO ---
    if st.session_state.pedido_enviado:
        st.success("✅ Pedido Confirmado! Os dados já estão na planilha.")
        if st.button("Criar Novo Pedido", use_container_width=True):
            st.session_state.carrinho = []
            st.session_state.pedido_enviado = False
            st.rerun()
        return

    # --- 4. FORMULÁRIO DE PEDIDO ---
    st.header("📝 Novo Pedido")
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            nome_cliente = st.text_input("Nome do Cliente", placeholder="Ex: Zé Bedeu")
        with col2:
            data_sel = st.date_input("Data de Entrega", value=datetime.now(), format="DD/MM/YYYY")

    st.divider()
    st.subheader("Adicionar Produtos")
    c_prod, c_qtd, c_add = st.columns([3, 1, 1])

    with c_prod:
        produto = st.selectbox("Selecione o Produto", list(cardapio.keys()))
    with c_qtd:
        qtd = st.number_input("Qtd", min_value=1, step=1)
    with c_add:
        st.write(" ")
        if st.button("➕ Adicionar"):
            if nome_cliente:
                meu_carrinho_temp = Carrinho(st.session_state.carrinho, codigo_pasteis)
                try:
                    meu_carrinho_temp.adicionar_item(produto, qtd, cardapio[produto])
                    st.session_state.carrinho = meu_carrinho_temp.itens
                    st.toast(f"{produto} adicionado!", icon="🛒")
                except ValueError as e:
                    st.error(f"⚠️ Erro: {e}")
            else:
                st.warning("Preencha o nome do cliente!")

    # --- 5. VISUALIZAÇÃO DO CARRINHO ---
    if st.session_state.carrinho:
        st.divider()
        meu_carrinho = Carrinho(st.session_state.carrinho, codigo_pasteis)
        
        for item in meu_carrinho.itens:
            st.write(f"**{item['qtd']}x {item['produto']}** - R$ {item['subtotal']:.2f}")

        st.divider()
        if meu_carrinho.desconto_total > 0:
            st.write(f"Subtotal Bruto: R$ {meu_carrinho.total_bruto:.2f}")
            st.write(f"🎁 Desconto Combo: -R$ {meu_carrinho.desconto_total:.2f}")
        
        st.metric("Total a Pagar", f"R$ {meu_carrinho.total_final:.2f}")

        if st.button("🚀 FINALIZAR E ENVIAR PEDIDO", use_container_width=True):
            id_p = datetime.now(fuso_brasil).strftime("%Y%m%d%H%M")
            dt_in = datetime.now(fuso_brasil).strftime("%Y-%m-%d %H:%M:%S")
            
            dados_para_planilha = []
            for item in meu_carrinho.itens:
                #Desconto
                d_i = float((item['subtotal'] * 0.15) if (meu_carrinho.tem_desconto and item['produto'] in codigo_pasteis) else 0.0)
                bruto = float(item['subtotal'])
                
                dados_para_planilha.append([
                    id_p, 
                    nome_cliente, 
                    data_sel.isoformat(), 
                    item['produto'], 
                    int(item['qtd']), 
                    bruto, 
                    d_i, 
                    float(bruto - d_i), 
                    dt_in
                ])
            
            if salvar_pedido(aba_pedidos, dados_para_planilha):
                st.session_state.pedido_enviado = True
                st.rerun()

def renderizar_edicao_pedido():
    st.subheader("🛒 Itens do Pedido Atual")

    if "carrinho" not in st.session_state or not st.session_state.carrinho:
        st.info("O carrinho está vazio.")
        return

    df_carrinho = pd.DataFrame(st.session_state.carrinho)

    df_editado = st.data_editor(
        df_carrinho,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Quantidade": st.column_config.NumberColumn(min_value=1),
            "Preço Unitário": st.column_config.NumberColumn(disabled=True)
        }
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Limpar Tudo", type="secondary"):
            st.session_state.carrinho = []
            st.rerun()
    
    with col2:
        if st.button("✅ Confirmar e Salvar Pedido", type="primary"):
            st.session_state.carrinho = df_editado.to_dict('records')

            st.success("Pedido enviado com sucesso!")
            st.session_state.carrinho = []
            st.rerun()