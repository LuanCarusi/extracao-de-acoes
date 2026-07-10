"""
Módulo de Análise e Filtros
Contém a lógica de aplicação de filtros (gerais e por setor) e cálculo do Score Final.
"""

import pandas as pd
import logging
from .config import FILTROS_GERAIS, FILTROS_POR_SETOR, RANKING_METRICS, COLUNAS_FINAIS

logger = logging.getLogger(__name__)

class StockAnalyzer:
    def __init__(self, df: pd.DataFrame):
        """
        Inicializa o analisador com os dados brutos.
        """
        self.df = df.copy()

    def aplicar_filtros_gerais(self) -> pd.DataFrame:
        """
        Aplica os filtros padrão para todas as ações.
        """
        logger.info("Aplicando filtros gerais...")
        
        # Filtra colunas importantes para não pesar na memória
        colunas_importantes = [
            'companyname', 'ticker', 'price', 'dy', 'p_l', 'margemliquida', 
            'dividaliquidaebit', 'roe', 'roic', 'liquidezmediadiaria'
        ]
        
        # Garante que as colunas existem
        for col in colunas_importantes:
            if col not in self.df.columns:
                self.df[col] = 0
                
        df_filtrado = self.df[colunas_importantes].copy()
        
        # Aplicação dos filtros usando a configuração
        df_filtrado = df_filtrado[df_filtrado['liquidezmediadiaria'] >= FILTROS_GERAIS['liquidezmediadiaria_min']]
        df_filtrado = df_filtrado[df_filtrado['roic'] >= FILTROS_GERAIS['roic_min']]
        df_filtrado = df_filtrado[df_filtrado['dy'] >= FILTROS_GERAIS['dy_min']]
        df_filtrado = df_filtrado[df_filtrado['p_l'] <= FILTROS_GERAIS['p_l_max']]
        df_filtrado = df_filtrado[df_filtrado['margemliquida'] >= FILTROS_GERAIS['margemliquida_min']]
        df_filtrado = df_filtrado[df_filtrado['dividaliquidaebit'] <= FILTROS_GERAIS['dividaliquidaebit_max']]
        df_filtrado = df_filtrado[df_filtrado['roe'] >= FILTROS_GERAIS['roe_min']]
        
        logger.info(f"{len(df_filtrado)} ações passaram pelos filtros gerais.")
        return df_filtrado

    def aplicar_filtros_por_setor(self, df_filtrado: pd.DataFrame) -> pd.DataFrame:
        """
        Sobrescreve a validação caso a ação pertença a um setor com regras específicas.
        Se a ação não cumprir as regras do seu setor, ela será removida.
        """
        if 'setor' not in df_filtrado.columns:
            logger.warning("Coluna 'setor' não encontrada no DataFrame. Pulando filtros por setor.")
            return df_filtrado

        logger.info("Aplicando filtros específicos por setor...")
        acoes_a_remover = []

        for idx, row in df_filtrado.iterrows():
            setor = str(row['setor'])
            if setor in FILTROS_POR_SETOR:
                regras = FILTROS_POR_SETOR[setor]
                
                # Validação condicional com base no setor
                if 'p_l_max' in regras and row['p_l'] > regras['p_l_max']:
                    acoes_a_remover.append(idx)
                    continue
                if 'dy_min' in regras and row['dy'] < regras['dy_min']:
                    acoes_a_remover.append(idx)
                    continue
                if 'roe_min' in regras and row['roe'] < regras['roe_min']:
                    acoes_a_remover.append(idx)
                    continue
                    
        df_filtrado = df_filtrado.drop(index=acoes_a_remover)
        logger.info(f"{len(df_filtrado)} ações restaram após filtros de setor.")
        return df_filtrado

    def calcular_rankings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula os rankings individuais e o Score Final.
        """
        logger.info("Calculando rankings...")
        df = df.copy()
        colunas_ranking = []
        
        for metrica, ascending in RANKING_METRICS.items():
            if metrica in df.columns:
                nome_rank = f"ranking_{metrica}"
                # method='first' quebra empates pela ordem que aparece
                df[nome_rank] = df[metrica].rank(ascending=ascending, method="first")
                colunas_ranking.append(nome_rank)
        
        # O Score Final é a soma dos rankings (menor score = melhor posição geral)
        df["score_final"] = df[colunas_ranking].sum(axis=1)
        df = df.sort_values("score_final", ascending=True)
        
        # Mantém apenas as colunas desejadas (caso existam no dataframe atual)
        colunas_exibir = [col for col in COLUNAS_FINAIS if col in df.columns]
        df_final = df[colunas_exibir].reset_index(drop=True)
        
        logger.info("Cálculo de rankings concluído.")
        return df_final
