import pandas as pd
from datetime import datetime, timedelta
import pytz

fuso_brasil = pytz.timezone('America/Sao_Paulo')

class GerenciadorMovimentacao:
    def __init__(self, df_movimentacoes_atual):
        self.df = df_movimentacoes_atual

    def gerar_id_unico(self, codigo_operacao):
        prefixo = "1" if codigo_operacao.startswith("ENT") else "2"
        hoje_str = datetime.now(fuso_brasil).strftime("%Y%m%d")

        if not self.df.empty and 'ID Mov.' in self.df.columns:
            ids_hoje = self.df[self.df['ID Mov.'].astype(str).str.contains(hoje_str)]
            proximo_sequencial = len(ids_hoje) + 1
        else:
            proximo_sequencial = 1

        return f"{prefixo}{hoje_str}{proximo_sequencial:05d}"

    def preparar_linha(self, codigo, item, qtd, unidade_medida, unidade_compra="", custo_unitario=0.0, validade="", lote=""):
        id_mov = self.gerar_id_unico(codigo)
        
        # Lógica de sinal: Saídas ficam negativas
        qtd_final = -abs(qtd) if codigo.startswith("SAI") else abs(qtd)
        
        # Cálculo do Custo Total
        custo_total = abs(qtd) * custo_unitario

        # Retorna a lista na ordem exata da planilha
        return [
            id_mov,                                           # ID Mov.
            datetime.now(fuso_brasil).strftime("%Y-%m-%d %H:%M:%S"), # Data Mov.
            codigo,                                           # Tipo
            item,                                             # Item
            qtd_final,                                        # Quantidade
            unidade_medida,                                   # Unidade de Medida
            unidade_compra,                                   # Unidade de Compra
            validade,                                         # Validade
            lote,                                             # Lote
            custo_unitario,                                   # Custo Unitário
            custo_total                                       # Custo Total
        ]

    def preparar_linha_ajuste(self, item, qtd_contada, df_saldo_atual, motivo="Inventário"):
        saldo = df_saldo_atual.get(item, 0)
        diferenca = qtd_contada - saldo

        if diferenca == 0:
            return None, 0 

        codigo = "ENT-A" if diferenca > 0 else "SAI-A"
        linha = self.preparar_linha(
            codigo=codigo,
            item=item,
            qtd=abs(diferenca),
            unidade_medida="",
            unidade_compra="",
            custo_unitario=0.0,
            validade="",
            lote=f"Ajuste: {motivo}"
        )
        return linha, diferenca

class AnalisadorEstoque:
    def __init__(self, registros_brutos):
        if isinstance(registros_brutos, pd.DataFrame):
            self.df = registros_brutos.copy()
        else:
            self.df = pd.DataFrame(registros_brutos)
        
        if not self.df.empty:
            self.df.columns = self.df.columns.str.strip()
            self.df['Data Mov.'] = pd.to_datetime(self.df['Data Mov.'], errors='coerce')
            self.df['Validade'] = pd.to_datetime(self.df['Validade'], dayfirst=True, errors='coerce')
            self.df['Quantidade'] = pd.to_numeric(self.df['Quantidade'], errors='coerce').fillna(0)

    @property
    def saldo_atual(self):
        if self.df.empty:
            return pd.Series(dtype=float)
        return self.df.groupby('Item')['Quantidade'].sum()
    
    def verificar_alertas_validade(self, dias_margem=7):
        if self.df.empty: return pd.DataFrame()
        hoje = pd.Timestamp.now().normalize()
        limite = hoje + timedelta(days=dias_margem)
        vencendo = self.df[(self.df['Quantidade'] > 0) & (self.df['Validade'] <= limite) & (self.df['Validade'] >= hoje)]
        return vencendo[['Item', 'Quantidade', 'Validade']]

class GestorRegras:
    def __init__(self, dados_cadastro):
        df = pd.DataFrame(dados_cadastro)
        if not df.empty:
            df.columns = df.columns.str.strip()
            df['Fator Conversão'] = pd.to_numeric(df['Fator Conversão'], errors='coerce').fillna(1)
            df['Estoque Mínimo'] = pd.to_numeric(df['Estoque Mínimo'], errors='coerce').fillna(0)
            self.regras = df.set_index('Item').to_dict('index')
        else:
            self.regras = {}

    def obter_unidade_compra(self, item):
        return self.regras.get(item, {}).get('Unidade Compra', '')

    def obter_unidade_receita(self, item):
        return self.regras.get(item, {}).get('Unidade Receita', '')

    def obter_fator(self, item):
        return self.regras.get(item, {}).get('Fator Conversão', 1)

    def obter_minimo(self, item):
        return self.regras.get(item, {}).get('Estoque Mínimo', 0)

    def converter_compra_para_receita(self, item, qtd_comprada):
        return qtd_comprada * self.obter_fator(item)

class BuscaEstoque:
    def __init__(self, df):
        self._df = df
        self.df_filtrado = df.copy()

    def filtrar(self, item="", tipo="Todos", data_inicio=None, data_fim=None):
        temp = self._df.copy()

        if item:
            temp = temp[temp['Item'].str.contains(item, case=False, na=False)]
        if tipo != "Todos":
            temp = temp[temp['Tipo'] == tipo]
        if data_inicio:
            temp = temp[temp['Data Mov.'] >= pd.Timestamp(data_inicio)]
        if data_fim:
            temp = temp[temp['Data Mov.'] <= pd.Timestamp(data_fim)]

        self.df_filtrado = temp

    @property
    def item_unico(self):
        itens = self.df_filtrado['Item'].dropna().unique()
        return itens[0] if len(itens) == 1 else None

    @property
    def resumo_por_item(self):
        if self.df_filtrado.empty:
            return pd.DataFrame()

        df = self.df_filtrado.copy()
        entradas = (
            df[df['Quantidade'] > 0]
            .groupby(['Item', 'Unidade de Medida'])['Quantidade']
            .sum()
            .reset_index()
            .rename(columns={'Quantidade': 'Entradas'})
        )
        saidas = (
            df[df['Quantidade'] < 0]
            .groupby(['Item', 'Unidade de Medida'])['Quantidade']
            .sum()
            .abs()
            .reset_index()
            .rename(columns={'Quantidade': 'Saídas'})
        )
        resumo = pd.merge(entradas, saidas, on=['Item', 'Unidade de Medida'], how='outer').fillna(0)
        resumo['Saldo período'] = resumo['Entradas'] - resumo['Saídas']
        return resumo