"""
Script Principal (Entry Point)
Orquestra o processo de extração, limpeza, enriquecimento assíncrono e rankeamento.
"""

import asyncio
import logging
import time
import pandas as pd
from src.data_extractor import fetch_statusinvest_data, fetch_all_sectors
from src.analyzer import StockAnalyzer

# Configuração profissional de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ScreeningApp")

def main():
    start_time = time.time()
    logger.info("Iniciando o processo de Screening de Ações...")
    
    # 1. Extração Inicial (Síncrono pois é uma única requisição com todos os dados)
    df_raw = fetch_statusinvest_data()
    if df_raw.empty:
        logger.error("Nenhum dado retornado do StatusInvest. Encerrando processo.")
        return
        
    # 2. Inicializa o Analisador
    analyzer = StockAnalyzer(df_raw)
    
    # 3. Aplica Filtros Gerais (Reduz a base para buscar setor apenas do que importa)
    df_filtrado = analyzer.aplicar_filtros_gerais()
    
    if df_filtrado.empty:
        logger.warning("Nenhuma ação passou pelos filtros gerais.")
        return
        
    # 4. Busca os Setores de forma Assíncrona (Apenas para as ações filtradas, otimizando muito)
    tickers = df_filtrado['ticker'].tolist()
    # O asyncio.run orquestra as chamadas assíncronas
    df_setores = asyncio.run(fetch_all_sectors(tickers))
    
    # Faz o merge para adicionar a coluna de setor
    df_filtrado = df_filtrado.merge(df_setores, on="ticker", how="left")
    
    # 5. Aplica Filtros Específicos por Setor (Ex: Bancos, Seguradoras)
    df_filtrado = analyzer.aplicar_filtros_por_setor(df_filtrado)
    
    # 6. Calcula Rankings e Score Final
    df_final = analyzer.calcular_rankings(df_filtrado)
    
    # Formata a exibição do pandas para ver todas as colunas no console
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_rows', 100)
    
    # 7. Resultado Final
    logger.info(f"Processo finalizado com sucesso! Tempo total: {time.time() - start_time:.2f} segundos.")
    print("\n================== RANKING FINAL DE AÇÕES ==================")
    print(df_final)
    print("============================================================\n")
    
    # Opcional: Exportar para CSV com formatação brasileira (evita que o Excel converta números em datas)
    try:
        df_final.to_csv("ranking_acoes_resultado.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")
        logger.info("Resultado salvo com sucesso no arquivo 'ranking_acoes_resultado.csv'.")
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo CSV: {e}")
        
if __name__ == "__main__":
    main()
