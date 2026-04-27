import pandas as pd
from datetime import datetime, date, timedelta
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

    def gerar_movimentacoes(self, id_pedido, nome_produto, quantidade, calculador=None):
        insumos = self.calcular_insumos(nome_produto, quantidade)
        if insumos is None:
            return None, f"Receita não encontrada para '{nome_produto}'"

        # Validade = hoje + 4 dias
        validade_produto = (datetime.now(fuso_brasil) + timedelta(days=4)).strftime("%d/%m/%Y")

        linhas = []
        custo_total_producao = 0.0

        for insumo in insumos:
            custo_unit = calculador.custo_por_unidade(insumo['item']) if calculador else 0.0
            custo_unit = custo_unit if custo_unit is not None else 0.0

            custo_total_producao += (custo_unit * insumo['qtd'])

            linhas.append(self.gerenciador_mov.preparar_linha(
                codigo="SAI-P",
                item=insumo['item'],
                qtd=insumo['qtd'],
                unidade_medida=insumo['unidade'],
                unidade_compra="",
                custo_unitario=round(custo_unit, 6),
                validade="",
                lote=f"Pedido {id_pedido}"
            ))
        
        custo_unitario_produto = custo_total_producao / quantidade if quantidade > 0 else 0.0

        linhas.append(self.gerenciador_mov.preparar_linha(
            codigo="ENT-P",
            item=nome_produto,
            qtd=quantidade,
            unidade_medida="un",
            unidade_compra="",
            custo_unitario=round(custo_total_producao / quantidade if quantidade > 0 else 0.0),
            validade=validade_produto,  
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

class CalculadorCustos:
    def __init__(self, df_precos):
        self.precos = pd.DataFrame(df_precos)
        if not self.precos.empty:
            self.precos.columns = self.precos.columns.str.strip()

            def limpar_valor_numerico(serie):
                # Remove R$, espaços e pontos de milhar, troca vírgula por ponto
                s = serie.astype(str).str.replace(r'R\$', '', regex=True).str.strip()
                s = s.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                return pd.to_numeric(s, errors='coerce')

            precos_limpos = limpar_valor_numerico(self.precos['Preço']).fillna(0)
            unidades_limpas = limpar_valor_numerico(self.precos['Unidade']).fillna(1)
            
            unidades_limpas = unidades_limpas.replace(0, 1)

            self.precos['Custo Calculado'] = precos_limpos / unidades_limpas
            
            self.mapa_custos = {
                str(item).strip().upper(): custo 
                for item, custo in zip(self.precos['Item'], self.precos['Custo Calculado'])
            }

    def custo_por_unidade(self, item):
        item_busca = str(item).strip().upper()
        return self.mapa_custos.get(item_busca, 0.0)

    def calcular_custo_receita(self, insumos):
        linhas = []
        custo_total_geral = 0.0
        
        for insumo in insumos:
            custo_unit = self.custo_por_unidade(insumo['item'])
            custo_total_insumo = custo_unit * insumo['qtd']
            custo_total_geral += custo_total_insumo
            
            linhas.append({
                'Item': insumo['item'],
                'Quantidade': insumo['qtd'],
                'Unidade': insumo['unidade'],
                'Custo Unit. (R$/un)': round(custo_unit, 6),
                'Custo Total (R$)': round(custo_total_insumo, 4),
                'Obs': "" if custo_unit > 0 else "⚠️ Preço não cadastrado"
            })

        return pd.DataFrame(linhas), custo_total_geral

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