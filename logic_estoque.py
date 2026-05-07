import pandas as pd
from datetime import datetime, timedelta
import pytz

fuso_brasil = pytz.timezone('America/Sao_Paulo')

class GerenciadorMovimentacao:
    def __init__(self, df_movimentacoes_atual=None):

        if df_movimentacoes_atual is not None and not df_movimentacoes_atual.empty:
            df_movimentacoes_atual.columns = [c.lower() for c in df_movimentacoes_atual.columns]
            self.df = df_movimentacoes_atual
        else:
            self.df = pd.DataFrame()

    def gerar_id_unico(self, codigo_operacao):
        """Gera ID baseado em prefixo (1-Entrada, 2-Saída), Data e Sequencial."""
        prefixo = "1" if codigo_operacao.startswith("ENT") else "2"
        hoje_str = datetime.now(fuso_brasil).strftime("%Y%m%d")

        # Busca IDs gerados hoje no DataFrame atual para definir o próximo sequencial
        if not self.df.empty and 'id_mov' in self.df.columns:
            ids_hoje = self.df[self.df['id_mov'].astype(str).str.contains(hoje_str)]
            proximo_sequencial = len(ids_hoje) + 1
        else:
            proximo_sequencial = 1

        return f"{prefixo}{hoje_str}{proximo_sequencial:05d}"

    def preparar_linha(self, codigo, item, qtd, unidade_medida, unidade_compra="", custo_unitario=0.0, validade="", lote=""):
        """Prepara os dados para inserção no banco de dados SQL."""
        id_mov = self.gerar_id_unico(codigo)
        
        # Lógica de sinal: Saídas ficam negativas no estoque
        qtd_final = -abs(qtd) if codigo.startswith("SAI") else abs(qtd)
        
        # Cálculo do Custo Total
        custo_total = abs(qtd) * custo_unitario

        # Retorna dicionário pronto para o Supabase (sb.table().insert())
        return {
            "id_mov": id_mov,
            "data_mov": datetime.now(fuso_brasil).isoformat(),
            "tipo": codigo,
            "item": item,
            "quantidade": qtd_final,
            "unidade_medida": unidade_medida,
            "unidade_compra": unidade_compra,
            "validade": validade if validade else None,
            "lote": lote,
            "custo_unitario": custo_unitario,
            "custo_total": custo_total
        }

class AnalisadorEstoque:
    def __init__(self, registros_brutos):
        """Converte os dados do SQL em um DataFrame utilizável para análise."""
        if isinstance(registros_brutos, pd.DataFrame):
            self.df = registros_brutos.copy()
        else:
            self.df = pd.DataFrame(registros_brutos)
        
        if not self.df.empty:
            # Normaliza colunas para evitar erros de case-sensitive
            self.df.columns = [c.lower().strip() for c in self.df.columns]
            self.df['data_mov'] = pd.to_datetime(self.df['data_mov'], errors='coerce')
            self.df['validade'] = pd.to_datetime(self.df['validade'], errors='coerce')
            self.df['quantidade'] = pd.to_numeric(self.df['quantidade'], errors='coerce').fillna(0)

    @property
    def saldo_atual(self):
        """Calcula o saldo real de cada item no estoque."""
        if self.df.empty:
            return pd.Series(dtype=float)
        return self.df.groupby('item')['quantidade'].sum()
    
    def verificar_alertas_validade(self, dias_margem=7):
        """Identifica itens próximos do vencimento."""
        if self.df.empty: return pd.DataFrame()
        hoje = pd.Timestamp.now(tz=fuso_brasil).normalize()
        limite = hoje + timedelta(days=dias_margem)
        
        # Filtra itens com saldo positivo que vencem em breve
        vencendo = self.df[
            (self.df['quantidade'] > 0) & 
            (self.df['validade'] <= limite) & 
            (self.df['validade'] >= hoje)
        ]
        return vencendo[['item', 'quantidade', 'validade']]

class BuscaEstoque:
    def __init__(self, df):
        self._df = df
        if not self._df.empty:
            self._df.columns = [c.lower() for c in self._df.columns]
        self.df_filtrado = self._df.copy()

    def filtrar(self, item="", tipo="Todos", data_inicio=None, data_fim=None):
        """Aplica filtros dinâmicos para visualização no Streamlit."""
        temp = self._df.copy()

        if item:
            temp = temp[temp['item'].str.contains(item, case=False, na=False)]
        if tipo != "Todos":
            temp = temp[temp['tipo'] == tipo]
        if data_inicio:
            temp = temp[temp['data_mov'].dt.date >= data_inicio]
        if data_fim:
            temp = temp[temp['data_mov'].dt.date <= data_fim]

        self.df_filtrado = temp

    @property
    def resumo_por_item(self):
        """Gera um resumo de Entradas, Saídas e Saldo do período filtrado."""
        if self.df_filtrado.empty:
            return pd.DataFrame()

        df = self.df_filtrado.copy()
        entradas = df[df['quantidade'] > 0].groupby(['item', 'unidade_medida'])['quantidade'].sum().reset_index(name='entradas')
        saidas = df[df['quantidade'] < 0].groupby(['item', 'unidade_medida'])['quantidade'].sum().abs().reset_index(name='saidas')
        
        resumo = pd.merge(entradas, saidas, on=['item', 'unidade_medida'], how='outer').fillna(0)
        resumo['saldo_periodo'] = resumo['entradas'] - resumo['saidas']
        return resumo

GestorRegras = GerenciadorMovimentacao