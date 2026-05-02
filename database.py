import streamlit as st
import pandas as pd
from supabase import create_client

class Database:
    def __init__(self):
        self.url = st.secrets["supabase"]["url"]
        self.key = st.secrets["supabase"]["service_role_key"]
        self.sb = create_client(self.url, self.key)

    # --- OPERAÇÕES GENÉRICAS ---
    def buscar(self, tabela, filtros=None, ordem=None, limite=None):
        try:
            query = self.sb.table(tabela).select("*")
            if filtros:
                for coluna, valor in filtros.items():
                    query = query.eq(coluna, valor)
            if ordem:
                query = query.order(ordem, desc=True)
            if limite:
                query = query.limit(limite)
            return pd.DataFrame(query.execute().data)
        except Exception as e:
            st.error(f"Erro ao buscar em {tabela}: {e}")
            return pd.DataFrame()

    def inserir(self, tabela, dados):
        try:
            self.sb.table(tabela).insert(dados).execute()
            return True
        except Exception as e:
            st.error(f"Erro ao inserir em {tabela}: {e}")
            return False

    def inserir_lote(self, tabela, lista):
        try:
            self.sb.table(tabela).insert(lista).execute()
            return True
        except Exception as e:
            st.error(f"Erro ao inserir lote em {tabela}: {e}")
            return False

    def atualizar(self, tabela, filtros, dados):
        try:
            query = self.sb.table(tabela).update(dados)
            for coluna, valor in filtros.items():
                query = query.eq(coluna, valor)
            query.execute()
            return True
        except Exception as e:
            st.error(f"Erro ao atualizar {tabela}: {e}")
            return False

    def rpc(self, funcao, params=None):
        """Chama uma function do PostgreSQL."""
        try:
            response = self.sb.rpc(funcao, params or {}).execute()
            return pd.DataFrame(response.data)
        except Exception as e:
            st.error(f"Erro ao chamar função {funcao}: {e}")
            return pd.DataFrame()

    # --- ESTOQUE ---
    def saldo_estoque(self):
        """Usa a view do SQL — zero pandas."""
        return self.buscar("vw_saldo_estoque")

    def estoque_critico(self):
        return self.buscar("vw_estoque_critico")

    def alertas_validade(self):
        return self.buscar("vw_alertas_validade")

    def movimentacoes(self, filtros=None):
        return self.buscar("movimentacoes", filtros=filtros, ordem="data_mov")

    def salvar_movimentacao(self, linha):
        return self.inserir("movimentacoes", linha)

    def salvar_movimentacoes_lote(self, linhas):
        return self.inserir_lote("movimentacoes", linhas)

    # --- PEDIDOS ---
    def pedidos(self):
        return self.buscar("pedidos", ordem="data_entrega")

    def resumo_pedidos(self):
        return self.buscar("vw_resumo_pedidos")

    def salvar_pedido(self, linhas):
        return self.inserir_lote("pedidos", linhas)

    # --- PRODUÇÃO ---
    def ordens_pendentes(self):
        """Já vem com custo estimado calculado no SQL."""
        return self.buscar("vw_ordens_pendentes")

    def producao(self):
        return self.buscar("producao", ordem="data_producao")

    def salvar_ordem_producao(self, linha):
        return self.inserir("producao", linha)

    def salvar_ordens_lote(self, linhas):
        return self.inserir_lote("producao", linhas)

    def atualizar_status_producao(self, id_producao, novo_status):
        return self.atualizar(
            "producao",
            filtros={"id_producao": id_producao},
            dados={"status": novo_status}
        )

    def custo_receita(self, produto, quantidade):
        """Chama a function do PostgreSQL."""
        return self.rpc("calcular_custo_receita", {
            "p_produto": produto,
            "p_quantidade": quantidade
        })

    def custo_total_receita(self, produto, quantidade):
        df = self.rpc("custo_total_receita", {
            "p_produto": produto,
            "p_quantidade": quantidade
        })
        if not df.empty:
            return float(df.iloc[0, 0])
        return 0.0

    # --- CADASTROS ---
    def insumos(self):
        df = self.buscar("cadastro_insumos")
        mapeamento = {
            'item': 'Item',
            'unidade_compra': 'Unidade Compra',
            'unidade_receita': 'Unidade Receita',
            'fator_conversao': 'Fator Conversão',
            'estoque_minimo': 'Estoque Mínimo'
        }
        return df.rename(columns=mapeamento)

    def precos(self):
        df = self.buscar("preco_insumos")
        mapeamento = {
            'item': 'Item',
            'preco': 'Preço',
            'unidade': 'Unidade',
            'marca': 'Marca'
        }
        return df.rename(columns=mapeamento)

    def receitas(self):
        df = self.buscar("receitas")
        mapeamento = {
            'cod_produto': 'cod_produto',
            'produto': 'Produto',
            'item_insumo': 'Item (Insumo)',
            'qtd_receita': 'Qtd_Receita',
            'unidade': 'Unidade'
        }
        return df.rename(columns=mapeamento)

    # --- OPERACIONAL ---
    def pedidos(self):
        df = self.buscar("pedidos")
        mapeamento = {
            'id_pedido': 'ID Pedido',
            'nome_cliente': 'Nome Cliente',
            'data_entrega': 'Data Entrega',
            'produto': 'Produto',
            'quantidade': 'Quantidade',
            'total_item_bruto': 'Total Item Bruto',
            'desconto': 'Desconto',
            'total_item_liquido': 'Total Item Líquido',
            'data_pedido': 'Data Pedido'
        }
        return df.rename(columns=mapeamento)

    def movimentacoes(self):
        df = self.buscar("movimentacoes")
        mapeamento = {
            'id_mov': 'ID Mov.',
            'data_mov': 'Data Mov.',
            'tipo': 'Tipo',
            'item': 'Item',
            'quantidade': 'Quantidade',
            'unidade_de_medida': 'Unidade de Medida',
            'unidade_de_compra': 'Unidade de Compra',
            'validade': 'Validade',
            'lote': 'Lote',
            'custo_unitario': 'Custo Unitário',
            'custo_total': 'Custo Total'
        }
        return df.rename(columns=mapeamento)

    def producao(self):
        df = self.buscar("producao")
        mapeamento = {
            'id_producao': 'ID Produção',
            'id_pedido': 'ID Pedido',
            'data_producao': 'Data Produção',
            'produto': 'Produto',
            'quantidade': 'Quantidade',
            'data_entrega': 'Data Entrega',
            'status': 'Status'
        }
        return df.rename(columns=mapeamento)