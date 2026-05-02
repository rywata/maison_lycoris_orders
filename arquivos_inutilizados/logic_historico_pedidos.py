import pandas as pd

class HistoricoFiltro:
    def __init__(self, df):
        self._df = df
        self.df_filtrado = df.copy()

    def filtrar(self, nome, produto, intervalo_data):
        temp_df = self._df.copy()

        if nome:
            temp_df = temp_df[temp_df['Nome Cliente'].str.contains(nome, case=False, na=False)]

        if produto != "Todos":
            temp_df = temp_df[temp_df['Produto'] == produto]

        if isinstance(intervalo_data, tuple) and len(intervalo_data) == 2:
            inicio, fim = intervalo_data
            temp_df = temp_df[(temp_df['Data Pedido'] >= inicio) & (temp_df['Data Pedido'] <= fim)]

        self.df_filtrado = temp_df

    @property
    def total_pedidos(self):
        return len(self.df_filtrado)

    @property
    def faturamento_total(self):
        return self.df_filtrado['Valor Numérico'].sum()