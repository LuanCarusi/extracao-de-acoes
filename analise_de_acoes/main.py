"""
Script Principal (Entry Point)
Orquestra o processo de extração, limpeza, enriquecimento assíncrono e rankeamento.
"""

import asyncio
import logging
import sys
import time
import pandas as pd
from src.data_extractor import fetch_statusinvest_data, fetch_all_sectors
from src.analyzer import StockAnalyzer

# Correção para evitar RuntimeError (Event loop is closed) no Windows com asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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
    
    # 1. Extração Inicial 
    df_raw = fetch_statusinvest_data()
    if df_raw.empty:
        logger.error("Nenhum dado retornado do StatusInvest. Encerrando processo.")
        return
        
    # 2. Busca os Setores de forma Assíncrona para TODOS os ativos logo no início
    # Isso garante que não excluímos Bancos/Seguradoras indevidamente
    tickers = df_raw['ticker'].tolist()
    
    # O asyncio.run orquestra as chamadas assíncronas
    df_setores = asyncio.run(fetch_all_sectors(tickers))
    
    # Faz o merge para adicionar a coluna de setor na base crua
    df_raw = df_raw.merge(df_setores, on="ticker", how="left")
    
    # 3. Separa os DataFrames por Setor
    # Aqui separamos Bancos e Seguradoras do resto.
    is_banco = df_raw['setor'] == 'Bancos'
    is_seguradora = df_raw['setor'].isin(['Seguradoras', 'Corretoras de Seguros', 'Previdência e Seguros'])
    
    df_bancos = df_raw[is_banco].copy()
    df_seguradoras = df_raw[is_seguradora].copy()
    df_geral = df_raw[~(is_banco | is_seguradora)].copy()
    
    logger.info(f"Separação concluída: {len(df_bancos)} Bancos, {len(df_seguradoras)} Seguradoras, {len(df_geral)} Outros Setores.")
    
    # 4. Inicializa o Analisador
    analyzer = StockAnalyzer(df_raw) # O dataframe interno dele não será usado diretamente agora
    
    # 5. Processamento Independente (Pipelines)
    df_bancos_processado = analyzer.processar_bancos(df_bancos)
    df_seguradoras_processado = analyzer.processar_seguradoras(df_seguradoras)
    df_geral_processado = analyzer.processar_geral(df_geral)
    
    # 6. Combinação Final
    dfs_to_concat = []
    if not df_bancos_processado.empty:
        dfs_to_concat.append(df_bancos_processado)
    if not df_seguradoras_processado.empty:
        dfs_to_concat.append(df_seguradoras_processado)
    if not df_geral_processado.empty:
        dfs_to_concat.append(df_geral_processado)
        
    if not dfs_to_concat:
        logger.warning("Nenhuma ação sobrou após os filtros!")
        return
        
    df_final = pd.concat(dfs_to_concat, ignore_index=True)
    
    # Ordena o DataFrame final pelo Score Final de forma crescente (menor percentil é o melhor)
    df_final = df_final.sort_values(by="score_final", ascending=True).reset_index(drop=True)
    
    # Transforma a média dos percentis na posição final do ranking (1º, 2º, etc)
    df_final["score_final"] = df_final.index + 1
    
    # Renomeia as colunas para um formato de apresentação elegante
    mapa_colunas = {
        "companyname": "Empresa",
        "ticker": "Ticker",
        "setor": "Setor",
        "price": "Cotação",
        "dy": "Dividend Yield",
        "p_l": "P/L",
        "margemliquida": "Margem Líquida",
        "dividaliquidaebit": "Divida Líquida/EBIT",
        "roe": "ROE",
        "roic": "ROIC",
        "liquidezmediadiaria": "Liquidez Média Diária",
        "score_final": "Posição"
    }
    df_final = df_final.rename(columns=mapa_colunas)
    
    # Formata a exibição do pandas para ver todas as colunas no console
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_rows', 200)
    
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
