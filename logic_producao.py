import pandas as pd
from datetime import datetime, date, timedelta
import pytz
from logic_estoque import GerenciadorMovimentacao
import unicodedata

fuso_brasil = pytz.timezone('America/Sao_Paulo')

def normalizar(texto):
    texto = str(texto).strip().upper()
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

class GerenciadorProducao:
    def __init__(self, df_receitas, df_movimentacoes):
        self.receitas = df_receitas.copy()
        self.gerenciador_mov = GerenciadorMovimentacao(df_movimentacoes)

        if not self.receitas.empty:
            # Normaliza colunas do Supabase (minúsculo) para o padrão esperado
            self.receitas.columns = self.receitas.columns.str.strip().str.lower()
            self.receitas = self.receitas.rename(columns={
                'produto': 'Produto',
                'item_insumo': 'Item (Insumo)',
                'qtd_receita': 'Qtd_Receita',
                'unidade': 'Unidade'
            })
            self.receitas['Qtd_Receita'] = pd.to_numeric(
                self.receitas['Qtd_Receita'], errors='coerce'
            ).fillna(0)

    def calcular_insumos(self, nome_produto, quantidade):
        if self.receitas.empty or 'Produto' not in self.receitas.columns:
            return None
        mask = self.receitas['Produto'].str.upper() == nome_produto.upper()
        receita = self.receitas[mask]
        if receita.empty:
            return None
        rendimento = 1

        fator_multiplicador = quantidade / rendimento
        return [
            {
                'item': row['Item (Insumo)'],
                'qtd': row['Qtd_Receita'] * fator_multiplicador,
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

        for i, insumo in enumerate(insumos):
            custo_unit = calculador.custo_por_unidade(insumo['item']) if calculador else None

            if custo_unit is None:
                custo_unit = 0.0

            custo_total_producao += (custo_unit * insumo['qtd'])

            # Preparação da linha de SAÍDA
            linha_insumo = self.gerenciador_mov.preparar_linha(
                codigo="SAI-P",
                item=insumo['item'],
                qtd=insumo['qtd'],
                unidade_medida=insumo['unidade'],
                unidade_compra="",
                custo_unitario=round(custo_unit, 4),
                validade="",
                lote=f"Pedido {id_pedido}"
            )
            
            # FORÇAR ID ÚNICO
            linha_insumo['id_mov'] = f"{linha_insumo['id_mov']}_{i}"
            
            linhas.append(linha_insumo)
        
        custo_unitario_produto = custo_total_producao / quantidade if quantidade > 0 else 0.0

        # Preparação da linha de ENTRADA do produto acabado
        linha_produto = self.gerenciador_mov.preparar_linha(
            codigo="ENT-P",
            item=nome_produto,
            qtd=quantidade,
            unidade_medida="un",
            unidade_compra="",
            custo_unitario=round(float(custo_unitario_produto), 4),
            validade=validade_produto,  
            lote=f"Pedido {id_pedido}"
        )
        
        # ID da entrada único
        linha_produto['id_mov'] = f"{linha_produto['id_mov']}_final"
        
        linhas.append(linha_produto)

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
    def __init__(self, df_producao, df_movimentacoes, calculador=None, df_receitas=None):
        self.df_producao = df_producao.copy()
        self.gerenciador_mov = GerenciadorMovimentacao(df_movimentacoes)
        self.calculador = calculador
        self.df_receitas = df_receitas

    def confirmar_producao(self, id_producao, nome_produto, quantidade, data_entrega):
        hoje = date.today()

        # Calcula custo unitário do produto acabado
        custo_unitario_produto = 0.0
        if self.calculador and self.df_receitas is not None:
            produtor_temp = GerenciadorProducao(self.df_receitas, pd.DataFrame())
            insumos = produtor_temp.calcular_insumos(nome_produto, quantidade)
            if insumos:
                _, custo_total = self.calculador.calcular_custo_receita(insumos)
                custo_unitario_produto = custo_total / quantidade if quantidade > 0 else 0.0

        validade_produto = (datetime.now(fuso_brasil) + timedelta(days=4)).strftime("%d/%m/%Y")

        linha_mov = self.gerenciador_mov.preparar_linha(
            codigo="ENT-P",
            item=nome_produto,
            qtd=quantidade,
            unidade_medida="un",
            unidade_compra="",
            custo_unitario=round(float(custo_unitario_produto), 4),
            validade=validade_produto,
            lote=f"Produção {id_producao}"
        )

        if isinstance(data_entrega, str) and data_entrega:
            try:
                data_entrega = date.fromisoformat(data_entrega)
            except ValueError:
                data_entrega = hoje

        novo_status = "Entregue" if data_entrega <= hoje else "Concluído"
        return linha_mov, novo_status

class CalculadorCustos:
    def __init__(self, df_precos):
        self.precos = pd.DataFrame(df_precos).copy()

        if not self.precos.empty:
            self.precos.columns = self.precos.columns.str.strip().str.lower()

            self.precos = self.precos.rename(columns={
                'preco': 'Preço',
                'unidade': 'Unidade',
                'item': 'Item',
                'marca': 'Marca'
            })

            self.precos['Preço'] = pd.to_numeric(self.precos['Preço'], errors='coerce').fillna(0)
            self.precos['Unidade'] = pd.to_numeric(self.precos['Unidade'], errors='coerce').fillna(1)
            self.precos['Unidade'] = self.precos['Unidade'].replace(0, 1)
            self.precos['Custo Unitário'] = self.precos['Preço'] / self.precos['Unidade']
            self._idx = self.precos.set_index('Item')

            self.mapa_itens = {
                normalizar(k): k for k in self._idx.index
            }
        else:
            self._idx = pd.DataFrame()
            self.mapa_itens = {}

    def custo_por_unidade(self, item):
        item_norm = normalizar(item)
        item_original = self.mapa_itens.get(item_norm)

        try:
            if item_original and item_original in self._idx.index:
                valor = self._idx.loc[item_original, 'Custo Unitário']

                if isinstance(valor, pd.Series):
                    return float(valor.iloc[0])
                return float(valor)
        except Exception as e:
            print(f"Erro ao buscar custo do item {item}: {e}")
            return 0.0

        return 0.0

    def calcular_custo_receita(self, insumos):
        linhas = []
        custo_total_geral = 0.0

        for insumo in insumos:
            custo_unit = self.custo_por_unidade(insumo['item'])

            if custo_unit is None:
                custo_total_insumo = 0.0
                obs = "⚠️ Preço não cadastrado"
                custo_unit_exibir = 0.0
            else:
                custo_total_insumo = custo_unit * insumo['qtd']
                obs = ""
                custo_unit_exibir = round(custo_unit, 6)

            custo_total_geral += custo_total_insumo

            linhas.append({
                'Item': insumo['item'],
                'Quantidade': insumo['qtd'],
                'Unidade': insumo['unidade'],
                'Custo Unit. (R$/un)': custo_unit_exibir,
                'Custo Total (R$)': round(custo_total_insumo, 4),
                'Obs': obs
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