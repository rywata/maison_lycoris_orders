import pandas as pd
from datetime import dateetime, timedelta

class AnalisadorEstoque:
  def __init__(self, registros_brutos):
    self.df = pd.DataFrame(registros_brutos)

    if not self.df.empty:
      self.df['data_movimento'] = pd.to_datetime(self.df['data_movimento'])
      self.df['validade'] = pd.to_datetime(self.df['validade'], dayfirst=True)
      self.df['quantidade'] = pd.to_numeric(self.df['quantidade'])

  @property
  def saldo_atual(self):
    if self.df.empty:
      return pd.Series()
    return self.df.groupby('item')['quantidade'].sum()
  
  def verificar_alertas_validade(self, dias_margem=7):
    hoje = pd.Timestamp.now().normalize()
    limite = hoje + timedelta(days=dias_margem)

    vencendo = self.df[
      (self.df['quantidade'] > 0) &
      (self.df['validade'] <= limite) &
      (self.df['validade'] >= hoje)
    ]
    return vencendo[['item', 'quantidade', 'validade']]