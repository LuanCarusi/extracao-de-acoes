"""
Módulo de Configuração
Define os filtros globais e específicos por setor.
"""

# Filtros Gerais aplicados a todas as empresas inicialmente
FILTROS_GERAIS = {
    'liquidezmediadiaria_min': 1_000_000,
    'roic_min': 7.9,
    'dy_min': 5.0,
    'p_l_max': 15.1,
    'margemliquida_min': 4.9,
    'dividaliquidaebit_max': 5.5,
    'roe_min': 9.5
}

# Filtros Específicos por Setor (Sobrescrevem ou adicionam aos filtros gerais)
# Você pode adicionar novos setores ou alterar as métricas conforme necessário
FILTROS_POR_SETOR = {
    'Bancos': {
        'liquidezmediadiaria_min': 1_000_000,
        'dy_min': 6.0,
        'margemliquida_min': 4.9,
        'p_l_max': 12.0,          # Bancos costumam ter P/L menor
        'roe_min': 12.0,          # Exigência de rentabilidade maior para bancos

    },
    'Seguradoras': {
        'p_l_max': 12.0,
        'roe_min': 15.0,
        'dy_min': 5.5
    },
    'Corretoras de seguros': {
        'p_l_max': 15.0,
        'roe_min': 15.0
    }
}

# Indicadores que compõem o Score Final e sua direção de rankeamento
# True = Ordem crescente (menor é melhor, ex: P/L, Dívida)
# False = Ordem decrescente (maior é melhor, ex: DY, ROE, Margem Líquida)
RANKING_METRICS = {
    'dy': False,
    'p_l': True,
    'margemliquida': False,
    'dividaliquidaebit': True,
    'roe': False
}

# Colunas finais a serem exibidas no relatório
COLUNAS_FINAIS = [
    "companyname",
    "ticker",
    "setor",
    "price",
    "dy",
    "p_l",
    "margemliquida",
    "dividaliquidaebit",
    "roe",
    "roic",
    "liquidezmediadiaria",
    "score_final"
]

# URL da API não oficial do StatusInvest
STATUS_INVEST_URL = "https://statusinvest.com.br/category/advancedsearchresultpaginated?search=%7B%22Sector%22%3A%22%22%2C%22SubSector%22%3A%22%22%2C%22Segment%22%3A%22%22%2C%22my_range%22%3A%22-20%3B100%22%2C%22forecast%22%3A%7B%22upsidedownside%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22estimatesnumber%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22revisedup%22%3Atrue%2C%22reviseddown%22%3Atrue%2C%22consensus%22%3A%5B%5D%7D%2C%22dy%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_l%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22peg_ratio%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_vp%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margembruta%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margemebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margemliquida%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22ev_ebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22dividaliquidaebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22dividaliquidapatrimonioliquido%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_sr%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_capitalgiro%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ativocirculante%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roe%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roic%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22liquidezcorrente%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22pl_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22passivo_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22giroativos%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22receitas_cagr5%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22lucros_cagr5%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22liquidezmediadiaria%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22vpa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22lpa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22valormercado%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%7D&orderColumn=&isAsc=&page=0&take=1000&CategoryType=1"
