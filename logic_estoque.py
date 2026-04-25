import pandas as pd
from datetime import datetime, timedelta

class AnalisadorEstoque:
  def __init__(self, registros_brutos):
    self.df = pd.DataFrame(registros_brutos)

    if not self.df.empty:
      self.df['Data Mov.'] = pd.to_datetime(self.df['Data Mov.'], errors='coerce')
      self.df['Validade'] = pd.to_datetime(self.df['Validade'], dayfirst=True, errors='coerce')
      self.df['Quantidade'] = pd.to_numeric(self.df['Quantidade'], errors='coerce').fillna(0)

  @property
  def saldo_atual(self):
    if self.df.empty:
      return pd.Series()
    return self.df.groupby('Item')['Quantidade'].sum()
  
  def verificar_alertas_validade(self, dias_margem=7):
    hoje = pd.Timestamp.now().normalize()
    limite = hoje + timedelta(days=dias_margem)

    vencendo = self.df[
      (self.df['Quantidade'] > 0) &
      (self.df['Validade'] <= limite) &
      (self.df['Validade'] >= hoje)
    ]
    return vencendo[['Item', 'Quantidade', 'Validade']]

class GestorRegras:
  def __init__(self, dados_cadastro):
    self.regras - pd.DataFrame(dados_cadastro).set_index('Item').to_dict('index')
  
  def obter_minimo(self, item):
    return self.regras.get(item, {}).get('Estoque Mínimo', 0)

  def obter_fator(self, item):
    return self.regras.get(item, {}).get('Fator Conversão', 1)

class AnalisadorEstoque:
  def __init__(self, df_movimentacoes):
    self.df = df_movimentacoes
    if not self.df.empty:
      self.df.columns = self.df.columns.str.strip()
      self.df['Quantidade'] = pd.to_numeric(self.df['Quantidade'], errors='coerce').fillna(0)

      @property
      def saldos(self):
        return self.df.groupby('Item')['Quantidade'].sum()
