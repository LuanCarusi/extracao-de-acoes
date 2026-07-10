"""
Módulo de Extração de Dados
Responsável por baixar os indicadores do StatusInvest e buscar os setores no Fundamentus de forma assíncrona.
"""

import requests
import pandas as pd
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
from .config import STATUS_INVEST_URL

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_statusinvest_data() -> pd.DataFrame:
    """
    Busca os indicadores fundamentalistas de todas as ações no StatusInvest.
    """
    logger.info("Iniciando requisição para o StatusInvest...")
    try:
        response = requests.get(STATUS_INVEST_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()["list"]
        df = pd.DataFrame(data)
        logger.info(f"Sucesso! {len(df)} ativos carregados do StatusInvest.")
        return df
    except Exception as e:
        logger.error(f"Erro ao buscar dados do StatusInvest: {e}")
        return pd.DataFrame()


async def fetch_setor_async(session: aiohttp.ClientSession, ticker: str, semaphore: asyncio.Semaphore) -> dict:
    """
    Função assíncrona para buscar o setor de um ticker específico no site Fundamentus.
    O semaphore limita o número de requisições concorrentes.
    """
    url = f"https://www.fundamentus.com.br/detalhes.php?papel={ticker}"
    
    async with semaphore:
        try:
            async with session.get(url, headers=HEADERS, timeout=10) as response:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                links = soup.find_all("a", href=True)
                setor = "Desconhecido"
                
                for link in links:
                    if "resultado.php?segmento=" in link["href"]:
                        setor = link.text.strip()
                        break
                        
                return {"ticker": ticker, "setor": setor}
        except Exception as e:
            logger.debug(f"Falha ao buscar setor para {ticker}: {e}")
            return {"ticker": ticker, "setor": "Desconhecido"}


async def fetch_all_sectors(tickers: list) -> pd.DataFrame:
    """
    Orquestra a busca assíncrona de setores para uma lista de tickers.
    """
    logger.info(f"Buscando setor para {len(tickers)} ativos de forma assíncrona no Fundamentus...")
    
    # Limita a 15 requisições simultâneas para não sobrecarregar o servidor
    semaphore = asyncio.Semaphore(15) 
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_setor_async(session, ticker, semaphore) for ticker in tickers]
        # tqdm ou logging simples para progresso, vamos apenas esperar tudo
        resultados = await asyncio.gather(*tasks)
        
    logger.info("Busca de setores concluída com sucesso.")
    return pd.DataFrame(resultados)
