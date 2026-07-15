"""
Módulo de Análise e Filtros
Contém a lógica de aplicação de filtros e separação de pipelines (Geral e Bancos).
"""

import pandas as pd
import logging
from .config import FILTROS_GERAIS, FILTROS_BANCOS, RANKING_METRICS_GERAL, RANKING_METRICS_BANCOS, COLUNAS_FINAIS

logger = logging.getLogger(__name__)

class StockAnalyzer:
    def __init__(self, df: pd.DataFrame):
        """
        Inicializa o analisador com os dados brutos já contendo a coluna 'setor'.
        """
        self.df = df.copy()

    def processar_bancos(self, df_bancos: pd.DataFrame) -> pd.DataFrame:
        """
        Processa especificamente o dataframe de Bancos.
        """
        if df_bancos.empty:
            return df_bancos

        logger.info("Aplicando filtros em Bancos...")
        
        # Filtra colunas importantes para Bancos (conforme pedido)
        colunas_importantes = [
            'companyname', 'ticker', 'setor', 'price', 'dy', 'p_l', 'margemliquida', 
            'roe', 'liquidezmediadiaria'
        ]
        
        for col in colunas_importantes:
            if col not in df_bancos.columns:
                df_bancos[col] = 0
                
        df_filtrado = df_bancos[colunas_importantes].copy()
        
        # Filtros de Bancos
        # 1. Liquidez >= 1.000.000 (exclui nulos)
        df_filtrado = df_filtrado[df_filtrado['liquidezmediadiaria'].notnull()]
        df_filtrado = df_filtrado[df_filtrado['liquidezmediadiaria'] >= FILTROS_BANCOS['liquidezmediadiaria_min']]
        
        # 2. ROE >= 8 (Mantém nulos e 0). (no pandas, se for NaN a comparação falha. Vamos tratar NaN como 0 temporariamente ou filtrar os que não são menores que 8)
        # O pedido foi: "removeria os ativos cujo roe é menor que 8 (nesse caso não removeria os valores 0 ou null)"
        df_filtrado = df_filtrado[~((df_filtrado['roe'] < FILTROS_BANCOS['roe_min']) & (df_filtrado['roe'] != 0) & df_filtrado['roe'].notnull())]
        
        # 3. P/L <= 13
        df_filtrado = df_filtrado[df_filtrado['p_l'] <= FILTROS_BANCOS['p_l_max']]
        
        # 4. DY >= 6
        df_filtrado = df_filtrado[df_filtrado['dy'] >= FILTROS_BANCOS['dy_min']]
        
        logger.info(f"{len(df_filtrado)} Bancos passaram pelos filtros.")
        
        # Rankeamento
        # Rankeamento
        df_final = self.calcular_rankings(df_filtrado, RANKING_METRICS_BANCOS)
        return df_final

    def processar_seguradoras(self, df_seguradoras: pd.DataFrame) -> pd.DataFrame:
        """
        Processa especificamente o dataframe de Seguradoras.
        """
        if df_seguradoras.empty:
            return df_seguradoras

        logger.info("Aplicando filtros em Seguradoras...")
        
        colunas_importantes = [
            'companyname', 'ticker', 'setor', 'price', 'dy', 'p_l', 'roe', 'liquidezmediadiaria'
        ]
        
        for col in colunas_importantes:
            if col not in df_seguradoras.columns:
                df_seguradoras[col] = 0
                
        df_filtrado = df_seguradoras[colunas_importantes].copy()
        
        # Filtros de Seguradoras
        # 1. Liquidez >= 1.000.000 (exclui nulos)
        df_filtrado = df_filtrado[df_filtrado['liquidezmediadiaria'].notnull()]
        df_filtrado = df_filtrado[df_filtrado['liquidezmediadiaria'] >= 1_000_000]
        
        # 2. DY não pode ser null nem 0
        df_filtrado = df_filtrado[df_filtrado['dy'].notnull()]
        df_filtrado = df_filtrado[df_filtrado['dy'] > 0]
        
        logger.info(f"{len(df_filtrado)} Seguradoras passaram pelos filtros.")
        
        # Rankeamento
        # A configuração tem RANKING_METRICS_SEGURADORAS
        from .config import RANKING_METRICS_SEGURADORAS
        df_final = self.calcular_rankings(df_filtrado, RANKING_METRICS_SEGURADORAS)
        return df_final


    def processar_geral(self, df_geral: pd.DataFrame) -> pd.DataFrame:
        """
        Processa o dataframe geral (excluindo Bancos).
        """
        if df_geral.empty:
            return df_geral

        logger.info("Aplicando filtros Gerais...")
        
        colunas_importantes = [
            'companyname', 'ticker', 'setor', 'price', 'dy', 'p_l', 'margemliquida', 
            'dividaliquidaebit', 'roe', 'roic', 'liquidezmediadiaria'
        ]
        
        for col in colunas_importantes:
            if col not in df_geral.columns:
                df_geral[col] = 0
                
        df_filtrado = df_geral[colunas_importantes].copy()
        
        # Aplicação dos filtros Gerais
        df_filtrado = df_filtrado[df_filtrado['liquidezmediadiaria'] >= FILTROS_GERAIS['liquidezmediadiaria_min']]
        df_filtrado = df_filtrado[df_filtrado['roic'] >= FILTROS_GERAIS['roic_min']]
        df_filtrado = df_filtrado[df_filtrado['dy'] >= FILTROS_GERAIS['dy_min']]
        df_filtrado = df_filtrado[df_filtrado['p_l'] <= FILTROS_GERAIS['p_l_max']]
        df_filtrado = df_filtrado[df_filtrado['margemliquida'] >= FILTROS_GERAIS['margemliquida_min']]
        df_filtrado = df_filtrado[df_filtrado['dividaliquidaebit'] <= FILTROS_GERAIS['dividaliquidaebit_max']]
        df_filtrado = df_filtrado[df_filtrado['roe'] >= FILTROS_GERAIS['roe_min']]
        
        logger.info(f"{len(df_filtrado)} ações gerais passaram pelos filtros.")
        
        df_final = self.calcular_rankings(df_filtrado, RANKING_METRICS_GERAL)
        return df_final

    def calcular_rankings(self, df: pd.DataFrame, ranking_metrics: dict) -> pd.DataFrame:
        """
        Calcula os rankings individuais e o Score Final para o DataFrame passado.
        """
        if df.empty:
            return df

        df = df.copy()
        colunas_ranking = []
        
        for metrica, ascending in ranking_metrics.items():
            if metrica in df.columns:
                nome_rank = f"ranking_{metrica}"
                # pct=True transforma o ranking em um percentil (0.0 a 1.0)
                # method="min" garante que empates fiquem com o mesmo percentil (o melhor)
                df[nome_rank] = df[metrica].rank(ascending=ascending, method="min", pct=True)
                colunas_ranking.append(nome_rank)
        
        # A média dos percentis normaliza pontuações de pipelines com diferentes quantidades de filtros e ativos
        df["score_final"] = df[colunas_ranking].mean(axis=1)
        
        # Garante que todas as colunas finais existam para não quebrar o merge final (preenche com vazio se não aplicável ao setor)
        for col in COLUNAS_FINAIS:
            if col not in df.columns:
                df[col] = pd.NA
                
        # Mantém apenas as colunas desejadas e ordena pelo score
        df_final = df[COLUNAS_FINAIS].copy()
        df_final = df_final.sort_values("score_final", ascending=True).reset_index(drop=True)
        
        return df_final
