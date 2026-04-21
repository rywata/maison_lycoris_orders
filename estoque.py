from database import Database

#Receber entradas no estoque
#Conectar com pedidos-gui e debitar do estoque os insumos utilizados no pedido
#Criar database com os dados dos insumos utilizados em cada produto
#Gerar etiqueta com dados de cada lote cadastrado

db = Database()
aba_estoque =  db.conectar_aba("Controle", "Estoque")