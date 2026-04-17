class Carrinho:
    def __init__(self, lista_de_itens, nomes_dos_pasteis):
        self.itens = lista_de_itens
        self.pasteis = nomes_dos_pasteis

    @property
    def total_bruto(self):
        return sum(item['subtotal'] for item in self.itens)

    @property
    def tem_desconto(self):
        qtd_total_pasteis = sum(item['qtd'] for item in self.itens if item['produto'] in self.pasteis)
        return qtd_total_pasteis >= 4

    @property
    def desconto_total(self):
        if not self.tem_desconto:
            return 0.0
        return sum(item['subtotal'] * 0.15 for item in self.itens if item['produto'] in self.pasteis)

    @property
    def total_final(self):
        return self.total_bruto - self.desconto_total

