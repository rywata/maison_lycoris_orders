import pandas as pd
from datetime import date

class Carrinho:
    def __init__(self, lista_de_itens=None, nomes_dos_pasteis=None):
        self.itens = lista_de_itens if lista_de_itens is not None else []
        self.pasteis = nomes_dos_pasteis if nomes_dos_pasteis is not None else []

    def adicionar_item(self, produto: str, qtd: int, preco_unitario: float):
        if qtd <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")
        #Gargalo de produção no shokupan
        if produto == "Shokupan" and qtd > 20:
            raise ValueError("Limite diário de Shokupan excedido")

        novo_item = {
            'produto': produto,
            'qtd': qtd,
            'preco_unitario': preco_unitario,
            'subtotal': qtd * preco_unitario
        }
        self.itens.append(novo_item)

    @property
    def total_bruto(self) -> float:
        return sum(
            (item.get('qtd', 0) * item.get('preco_unitario', 0)) 
            for item in self.itens
            if isinstance(item, dict)
        )

    @property
    def tem_desconto(self) -> bool:
        qtd_total_pasteis = sum(item['qtd'] for item in self.itens if item['produto'] in self.pasteis)
        return qtd_total_pasteis >= 4

    @property
    def desconto_total(self) -> float:
        if not self.tem_desconto:
            return 0.0
        return sum(
            (item.get('qtd', 0) * item.get('preco_unitario', 0)) * 0.15
            for item in self.itens 
            if item['produto'] in self.pasteis
        )

    @property
    def total_final(self) -> float:
        return self.total_bruto - self.desconto_total

class BuscaPedidos:
    def __init__(self, df: pd.DataFrame):
        self.df: pd.DataFrame = df

    def por_cliente(self, nome: str) -> 'BuscaPedidos':
        if nome:
            self.df = self.df[self.df['Cliente'].str.contains(nome, case=False, na=False)]
        return self

    def por_intervalo_data(self, inicio: date, fim: date) -> 'BuscaPedidos':
        self.df['Data'] = pd.to_datetime(self.df['Data']).dt.date
        self.df = self.df[(self.df['Data'] >- inicio) & (self.df['Data'] <= fim)]
        return self

    def por_produto(self, produto: str) -> 'BuscaPedidos':
        if produto in produto != 'Todos':
            self.df = self.df[self.df['Produto'] == produto]
        return self

    def obter_resultado(self) -> pd.DataFrame:
        return self.df

class MetricaPedidos:
    def __init__(self, df: pd.DataFrame):
        self.df: pd.DataFrame = df

    @property
    def faturamento_total(self) -> float:
        return float(self.df['Valor Total'].sum())
        
    @property
    def contagem_pedidos(self) -> int:
        return int(len(self.df))