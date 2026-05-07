import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from logic_producao import GerenciadorProducao, CalculadorCustos, GerenciadorStatusProducao

# =====================
# FIXTURES
# =====================

@pytest.fixture
def mock_receitas():
    return pd.DataFrame({
        'produto': ['PASTEL DE NATA', 'PASTEL DE NATA'],
        'item_insumo': ['MASSA FOLHADA PASTEL', 'Ovos'],
        'qtd_receita': [0.07142857, 0.28571428],
        'unidade': ['un', 'un']
    })

@pytest.fixture
def mock_precos():
    return pd.DataFrame({
        'item': ['MASSA FOLHADA PASTEL', 'Ovos'],
        'preco': [14.0, 18.0],
        'unidade': [1, 30]
    })

@pytest.fixture
def mock_movimentacoes():
    return pd.DataFrame(columns=[
        'id_mov', 'data_mov', 'tipo', 'item',
        'quantidade', 'unidade_medida', 'unidade_compra',
        'validade', 'lote', 'custo_unitario', 'custo_total'
    ])

# =====================
# TESTES DE CÁLCULO DE INSUMOS
# =====================

def test_calculo_insumos_quantidade_correta(mock_receitas):
    """14 pastéis devem consumir 1 unidade de massa e ~4 ovos"""
    produtor = GerenciadorProducao(mock_receitas, pd.DataFrame())
    resultado = produtor.calcular_insumos('PASTEL DE NATA', 14)

    assert resultado is not None
    assert len(resultado) == 2

    massa = next(i for i in resultado if i['item'] == 'MASSA FOLHADA PASTEL')
    ovos = next(i for i in resultado if i['item'] == 'Ovos')

    assert round(massa['qtd'], 2) == 1.0
    assert round(ovos['qtd'], 2) == 4.0

def test_calculo_insumos_produto_inexistente(mock_receitas):
    """Produto sem receita deve retornar None"""
    produtor = GerenciadorProducao(mock_receitas, pd.DataFrame())
    resultado = produtor.calcular_insumos('PRODUTO FANTASMA', 1)
    assert resultado is None

def test_calculo_insumos_case_insensitive(mock_receitas):
    """Busca por nome deve ser case-insensitive"""
    produtor = GerenciadorProducao(mock_receitas, pd.DataFrame())
    resultado_upper = produtor.calcular_insumos('PASTEL DE NATA', 1)
    resultado_lower = produtor.calcular_insumos('pastel de nata', 1)
    assert resultado_upper is not None
    assert resultado_lower is not None
    assert resultado_upper[0]['qtd'] == resultado_lower[0]['qtd']

def test_calculo_insumos_quantidade_zero(mock_receitas):
    """Quantidade zero não deve gerar insumos negativos"""
    produtor = GerenciadorProducao(mock_receitas, pd.DataFrame())
    resultado = produtor.calcular_insumos('PASTEL DE NATA', 0)
    assert resultado is not None
    for insumo in resultado:
        assert insumo['qtd'] == 0

# =====================
# TESTES DO CALCULADOR DE CUSTOS
# =====================

def test_calculador_custo_unitario_simples(mock_precos):
    """Massa: R$14 por 1 unidade = R$14/un"""
    calc = CalculadorCustos(mock_precos)
    assert calc.custo_por_unidade('MASSA FOLHADA PASTEL') == 14.0

def test_calculador_custo_unitario_com_divisao(mock_precos):
    """Ovos: R$18 por 30 unidades = R$0.60/un"""
    calc = CalculadorCustos(mock_precos)
    custo = calc.custo_por_unidade('Ovos')
    assert round(custo, 2) == 0.60

def test_calculador_item_inexistente(mock_precos):
    """Item sem preço cadastrado deve retornar 0"""
    calc = CalculadorCustos(mock_precos)
    assert calc.custo_por_unidade('ITEM INEXISTENTE') == 0.0

def test_calculador_case_insensitive_e_acentos(mock_precos):
    """Busca deve ignorar maiúsculas e acentos"""
    calc = CalculadorCustos(mock_precos)
    assert calc.custo_por_unidade('massa folhada pastel') == 14.0
    assert calc.custo_por_unidade('MASSA FOLHADA PASTEL') == 14.0

def test_calculador_df_vazio():
    """CalculadorCustos com DataFrame vazio não deve quebrar"""
    calc = CalculadorCustos(pd.DataFrame())
    assert calc.custo_por_unidade('qualquer') == 0.0

def test_calcular_custo_receita_total(mock_receitas, mock_precos):
    """Custo total de 14 pastéis: 1 massa (R$14) + 4 ovos (R$2.40) = R$16.40"""
    produtor = GerenciadorProducao(mock_receitas, pd.DataFrame())
    calc = CalculadorCustos(mock_precos)
    insumos = produtor.calcular_insumos('PASTEL DE NATA', 14)
    df_custo, total = calc.calcular_custo_receita(insumos)

    assert round(total, 2) == 16.40
    assert len(df_custo) == 2
    assert 'Custo Total (R$)' in df_custo.columns

# =====================
# TESTES DE MOVIMENTAÇÕES
# =====================

def test_gerar_movimentacoes_estrutura(mock_receitas, mock_precos, mock_movimentacoes):
    """Deve gerar SAI-P para cada insumo + ENT-P do produto final"""
    calc = CalculadorCustos(mock_precos)
    produtor = GerenciadorProducao(mock_receitas, mock_movimentacoes)

    linhas, erro = produtor.gerar_movimentacoes("PED001", "PASTEL DE NATA", 14, calculador=calc)

    assert erro is None
    assert linhas is not None

    tipos = [l['tipo'] for l in linhas]
    assert tipos.count('SAI-P') == 2   # um por insumo
    assert tipos.count('ENT-P') == 1   # produto acabado

def test_gerar_movimentacoes_saidas_negativas(mock_receitas, mock_precos, mock_movimentacoes):
    """SAI-P deve ter quantidade negativa"""
    calc = CalculadorCustos(mock_precos)
    produtor = GerenciadorProducao(mock_receitas, mock_movimentacoes)
    linhas, _ = produtor.gerar_movimentacoes("PED001", "PASTEL DE NATA", 14, calculador=calc)

    for linha in linhas:
        if linha['tipo'] == 'SAI-P':
            assert linha['quantidade'] < 0
        elif linha['tipo'] == 'ENT-P':
            assert linha['quantidade'] > 0

def test_gerar_movimentacoes_produto_inexistente(mock_movimentacoes):
    """Produto sem receita deve retornar erro"""
    df_vazio = pd.DataFrame(columns=['produto', 'item_insumo', 'qtd_receita', 'unidade'])
    produtor = GerenciadorProducao(df_vazio, mock_movimentacoes)
    linhas, erro = produtor.gerar_movimentacoes("ID_ERRO", "PRODUTO FANTASMA", 1)

    assert linhas is None
    assert "Receita não encontrada" in erro

def test_gerar_movimentacoes_sem_calculador(mock_receitas, mock_movimentacoes):
    """Sem calculador de custos, custo deve ser 0 mas não quebrar"""
    produtor = GerenciadorProducao(mock_receitas, mock_movimentacoes)
    linhas, erro = produtor.gerar_movimentacoes("PED001", "PASTEL DE NATA", 14)

    assert erro is None
    for linha in linhas:
        assert linha['custo_unitario'] == 0.0

def test_gerar_movimentacoes_ids_unicos(mock_receitas, mock_precos, mock_movimentacoes):
    """Cada movimentação deve ter ID único"""
    calc = CalculadorCustos(mock_precos)
    produtor = GerenciadorProducao(mock_receitas, mock_movimentacoes)
    linhas, _ = produtor.gerar_movimentacoes("PED001", "PASTEL DE NATA", 14, calculador=calc)

    ids = [l['id_mov'] for l in linhas]
    assert len(ids) == len(set(ids))

# =====================
# TESTES DO GERENCIADOR DE STATUS
# =====================

def test_confirmar_producao_status_futuro(mock_receitas, mock_precos, mock_movimentacoes):
    """Data de entrega futura deve gerar status Concluído"""
    from datetime import date, timedelta
    calc = CalculadorCustos(mock_precos)
    gestor = GerenciadorStatusProducao(
        pd.DataFrame(), mock_movimentacoes,
        calculador=calc, df_receitas=mock_receitas
    )
    data_futura = (date.today() + timedelta(days=3)).isoformat()
    _, status = gestor.confirmar_producao("PROD001", "PASTEL DE NATA", 14, data_futura)
    assert status == "Concluído"

def test_confirmar_producao_status_passado(mock_receitas, mock_precos, mock_movimentacoes):
    """Data de entrega passada deve gerar status Entregue"""
    from datetime import date, timedelta
    calc = CalculadorCustos(mock_precos)
    gestor = GerenciadorStatusProducao(
        pd.DataFrame(), mock_movimentacoes,
        calculador=calc, df_receitas=mock_receitas
    )
    data_passada = (date.today() - timedelta(days=1)).isoformat()
    _, status = gestor.confirmar_producao("PROD001", "PASTEL DE NATA", 14, data_passada)
    assert status == "Entregue"

def test_confirmar_producao_custo_calculado(mock_receitas, mock_precos, mock_movimentacoes):
    """ENT-P deve ter custo unitário maior que zero"""
    calc = CalculadorCustos(mock_precos)
    gestor = GerenciadorStatusProducao(
        pd.DataFrame(), mock_movimentacoes,
        calculador=calc, df_receitas=mock_receitas
    )
    from datetime import date, timedelta
    data_futura = (date.today() + timedelta(days=3)).isoformat()
    linha_mov, _ = gestor.confirmar_producao("PROD001", "PASTEL DE NATA", 14, data_futura)
    assert linha_mov['custo_unitario'] > 0

def test_fluxo_inicializacao_estoque():
    """Valida se a lógica de estoque suporta o formato vindo do banco/Streamlit"""
    from logic_estoque import GerenciadorMovimentacao
    import pandas as pd

    # Simula o df_cadastro vindo do carregar_cadastro_insumos()
    dados_exemplo = pd.DataFrame([
        {'item': 'Farinha', 'unidade_compra': 'Saco', 'unidade_receita': 'kg', 'fator': 25}
    ])

    # Teste 1: Inicialização com DataFrame (como corrigido no estoque.py)
    gestor = GerenciadorMovimentacao(dados_exemplo)
    assert gestor.obter_fator('Farinha') == 25

    # Teste 2: Inicialização com Lista (evita quebra se o código antigo persistir)
    gestor_lista = GerenciadorMovimentacao(dados_exemplo.to_dict('records'))
    assert gestor_lista.obter_fator('Farinha') == 25

# =====================
# TESTES DE INTEGRAÇÃO (requerem Supabase)
# =====================

@pytest.mark.integration
def test_conexao_supabase():
    """Verifica se a conexão com o Supabase está ativa"""
    from database import Database
    db = Database()
    df = db.receitas()
    assert not df.empty

@pytest.mark.integration
def test_rpc_custo_total():
    """Verifica se a function SQL retorna float >= 0"""
    from database import Database
    db = Database()
    total = db.custo_total_receita("PASTEL DE NATA", 1)
    assert isinstance(total, float)
    assert total >= 0