import pandas as pd
from datetime import datetime, date
import pytz
from logic_estoque import GerenciadorMovimentacao

fuso_brasil = pytz.timezone('America/Sao_Paulo')

class GerenciadorProducao:
    def __init__(self, df_receitas, df_movimentacoes):
        self.receitas = df_receitas.copy()
        self.gerenciador_mov = GerenciadorMovimentacao(df_movimentacoes)

        if not self.receitas.empty:
            self.receitas.columns = self.receitas.columns.str.strip()
            self.receitas['Qtd_Receita'] = pd.to_numeric(
                self.receitas['Qtd_Receita'], errors='coerce'
            ).fillna(0)

    def calcular_insumos(self, nome_produto, quantidade):
        mask = self.receitas['Produto'].str.upper() == nome_produto.upper()
        receita = self.receitas[mask]
        if receita.empty:
            return None
        return [
            {
                'item': row['Item (Insumo)'],
                'qtd': row['Qtd_Receita'] * quantidade,
                'unidade': row['Unidade']
            }
            for _, row in receita.iterrows()
        ]

    def gerar_movimentacoes(self, id_pedido, nome_produto, quantidade):
        insumos = self.calcular_insumos(nome_produto, quantidade)
        if insumos is None:
            return None, f"Receita não encontrada para '{nome_produto}'"

        linhas = []

        for insumo in insumos:
            linhas.append(self.gerenciador_mov.preparar_linha(
                codigo="SAI-P",
                item=insumo['item'],
                qtd=insumo['qtd'],
                unidade_medida=insumo['unidade'],
                lote=f"Pedido {id_pedido}"
            ))

        linhas.append(self.gerenciador_mov.preparar_linha(
            codigo="ENT-P",
            item=nome_produto,
            qtd=quantidade,
            unidade_medida="un",
            lote=f"Pedido {id_pedido}"
        ))

        return linhas, None

    def gerar_ordem_producao(self, id_pedido, nome_produto, quantidade, data_entrega):
        id_prod = f"PROD{datetime.now(fuso_brasil).strftime('%Y%m%d%H%M%S')}"
        return [
            id_prod,
            id_pedido,
            datetime.now(fuso_brasil).strftime("%Y-%m-%d %H:%M:%S"),
            nome_produto,
            quantidade,
            data_entrega,
            "Pendente"
        ]

class GerenciadorStatusProducao:
    def __init__(self, df_producao, df_movimentacoes):
        self.df_producao = df_producao.copy()
        self.gerenciador_mov = GerenciadorMovimentacao(df_movimentacoes)

    def confirmar_producao(self, id_producao, nome_produto, quantidade, data_entrega):
        """
        Gera a ENT-P do produto acabado e retorna o novo status.
        Se a data de entrega já passou, marca como Entregue.
        """
        hoje = date.today()

        linha_mov = self.gerenciador_mov.preparar_linha(
            codigo="ENT-P",
            item=nome_produto,
            qtd=quantidade,
            unidade_medida="un",
            lote=f"Produção {id_producao}"
        )

        if isinstance(data_entrega, str):
            data_entrega = date.fromisoformat(data_entrega)

        novo_status = "Entregue" if data_entrega <= hoje else "Concluído"
        return linha_mov, novo_status

class AnalisadorProducao:
    def __init__(self, df_producao):
        self.df = df_producao.copy() if not df_producao.empty else pd.DataFrame()

        if not self.df.empty:
            self.df.columns = self.df.columns.str.strip()
            self.df['Data Produção'] = pd.to_datetime(self.df['Data Produção'], errors='coerce')
            self.df['Quantidade'] = pd.to_numeric(self.df['Quantidade'], errors='coerce').fillna(0)

    @property
    def producao_por_produto(self):
        if self.df.empty:
            return pd.DataFrame()
        return (
            self.df.groupby('Produto')['Quantidade']
            .sum()
            .reset_index()
            .sort_values('Quantidade', ascending=False)
        )

    def filtrar_por_periodo(self, data_inicio=None, data_fim=None):
        temp = self.df.copy()
        if data_inicio:
            temp = temp[temp['Data Produção'] >= pd.Timestamp(data_inicio)]
        if data_fim:
            temp = temp[temp['Data Produção'] <= pd.Timestamp(data_fim)]
        return temp

    def filtrar_por_pedido(self, id_pedido):
        return self.df[self.df['ID Pedido'] == id_pedido]