import pandas as pd
from datetime import datetime, timedelta

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

class Insumo:
  def __init__(self, nome, unidade_medida, fator_conversao):
    self.nome = nome
    self.unidade = unidade_medida
    self.fator = fator_conversao
  
  def converter_para_receita(self, quantidade_compra):
    return quantidade_compra * self.fator

class CatalogoInsumos:
  def __init__(self, dados_planilha):
    self.df = pd.DataFrame(dados_planilha)
    self.df.set_index('Item', inplace=True)

  def obter_fator(self, nome_item):
    try:
      return float(self.df.loc[nome_item, 'Fator Conversão'])
    except KeyError:
      print(f"Erro: Item '{nome_item}' não encontrado no cadastro.")
      return None

  def obter_estoque_minimo(self, nome_item):
    return float(self.df.loc[nome_item, 'Estoque Mínimo'])