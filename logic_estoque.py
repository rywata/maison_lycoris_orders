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
        self.regras = pd.DataFrame(dados_cadastro).set_index('Item').to_dict('index')
  
    def obter_minimo(self, item):
        return self.regras.get(item, {}).get('Estoque Mínimo', 0)

    def obter_fator(self, item):
        return self.regras.get(item, {}).get('Fator Conversão', 1)