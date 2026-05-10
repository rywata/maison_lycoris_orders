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

    def inserir_retornando(self, tabela, dados):      # <- novo
        """UUID"""
        try:
            response = self.sb.table(tabela).insert(dados).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            st.error(f"Erro ao inserir em {tabela}: {e}")
            return None

    def inserir_lote_retornando(self, tabela, lista):  # <- novo
        """Insere lote e retorna todos os registros criados."""
        try:
            response = self.sb.table(tabela).insert(lista).execute()
            return response.data or []
        except Exception as e:
            st.error(f"Erro ao inserir lote em {tabela}: {e}")
            return []


    def atualizar(self, tabela, filtros, dados):
        try:
            query = self.sb.table(tabela).update(dados)
            for coluna, valor in filtros.items():
                query = query.eq(coluna, valor)
            response = query.execute()
            if response.data is not None:
                return True
            return False
        except Exception as e:
            st.error(f"Erro ao atualizar {tabela}: {e}")
            return False

    def rpc(self, funcao, params=None):
        try:
            response = self.sb.rpc(funcao, params or {}).execute()
            return pd.DataFrame(response.data)
        except Exception as e:
            st.error(f"Erro ao chamar função {funcao}: {e}")
            return pd.DataFrame()

    # --- ESTOQUE ---
    def saldo_estoque(self):
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
        return self.buscar("vw_ordens_pendentes")

    def producao(self):
        return self.buscar("producao", ordem="data_producao")

    def salvar_ordem_producao(self, linha):
        return self.inserir("producao", linha)

    def salvar_ordens_lote(self, linhas):
        return self.inserir_lote("producao", linhas)

    def atualizar_status_producao(self, id_producao, novo_status):
        try:
            response = (
                self.sb.table("producao")
                .update({"status": novo_status})
                .eq("id_producao", id_producao)
                .execute()
            )
            if not response.data:
                st.warning(f"Nenhuma linha atualizada para id_producao: {id_producao}")
                return False
            return True
        except Exception as e:
            st.error(f"Erro ao atualizar status: {e}")
            return False

    def custo_receita(self, produto, quantidade):
        return self.rpc("calcular_custo_receita", {
            "p_produto": produto,
            "p_quantidade": quantidade
        })

    def custo_total_receita(self, produto, quantidade):
        try:
            response = self.sb.rpc("custo_total_receita", {
                "p_produto": produto,
                "p_quantidade": quantidade
            }).execute()
            if response.data is not None:
                return float(response.data)
            return 0.0
        except Exception as e:
            st.error(f"Erro ao chamar função custo_total_receita: {e}")
            return 0.0

    # --- CADASTROS ---
    def insumos(self):
        return self.buscar("cadastro_insumos")

    def precos(self):
        return self.buscar("preco_insumos")

    def receitas(self):
        return self.buscar("receitas")