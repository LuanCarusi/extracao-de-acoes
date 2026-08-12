import sys

with open('utils.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Just a safety check since I might have deleted too much. I will just rewrite the whole file to be safe.
# It is short enough.

code = """import requests
import pandas as pd
import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def get_selic():
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return float(response.json()[0]['valor'])
    except Exception as e:
        logger.warning(f"Não foi possível buscar a Selic, usando 10.5% como padrão. Erro: {e}")
        return 10.5

def fetch_statusinvest_data():
    url = "https://statusinvest.com.br/category/advancedsearchresultpaginated?search=%7B%22Sector%22%3A%22%22%2C%22SubSector%22%3A%22%22%2C%22Segment%22%3A%22%22%2C%22my_range%22%3A%22-20%3B100%22%2C%22forecast%22%3A%7B%22upsidedownside%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22estimatesnumber%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22revisedup%22%3Atrue%2C%22reviseddown%22%3Atrue%2C%22consensus%22%3A%5B%5D%7D%2C%22dy%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_l%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22peg_ratio%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_vp%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margembruta%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margemebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margemliquida%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22ev_ebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22dividaliquidaebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22dividaliquidapatrimonioliquido%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_sr%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_capitalgiro%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ativocirculante%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roe%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roic%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22liquidezcorrente%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22pl_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22passivo_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22giroativos%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22receitas_cagr5%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22lucros_cagr5%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22liquidezmediadiaria%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22vpa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22lpa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22valormercado%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%7D&orderColumn=&isAsc=&page=0&take=1000&CategoryType=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    logger.info("Iniciando requisição para o StatusInvest...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()["list"]
        df = pd.DataFrame(data)
        
        if 'price' in df.columns:
            df = df[df['price'] > 0].copy()
            
        logger.info(f"Sucesso! {len(df)} ativos carregados do StatusInvest.")
        return df
    except Exception as e:
        logger.error(f"Erro ao buscar dados do StatusInvest: {e}")
        return pd.DataFrame()

def get_current_price(ticker):
    try:
        t_name = f"{ticker}.SA" if not ticker.endswith(".SA") else ticker
        t = yf.Ticker(t_name)
        
        hist = t.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        
        info = t.info
        if 'currentPrice' in info:
            return info['currentPrice']
        elif 'regularMarketPrice' in info:
            return info['regularMarketPrice']
            
        return 0.0
    except Exception as e:
        logger.error(f"Erro ao buscar preço para {ticker}: {e}")
        return 0.0

def calcular_metricas_carteira(df_carteira):
    if df_carteira.empty:
        return {
            'valor_aplicado': 0.0,
            'saldo_bruto': 0.0,
            'ganho_capital_rs': 0.0,
            'ganho_capital_perc': 0.0,
            'aplicado_fii': 0.0
        }

    valor_aplicado_total = 0.0
    saldo_bruto_total = 0.0
    aplicado_fii = 0.0

    for _, row in df_carteira.iterrows():
        ticker = str(row.get('Ticker', '')).strip().upper()
        if not ticker: continue
            
        tipo = str(row.get('Tipo', 'Ação')).strip().upper()
        qtde = pd.to_numeric(row.get('Quantidade', 0), errors='coerce')
        pm = pd.to_numeric(row.get('Preço Médio', 0), errors='coerce')
        
        if pd.isna(qtde) or pd.isna(pm): continue

        valor_aplicado = qtde * pm
        valor_aplicado_total += valor_aplicado
        
        if tipo == 'FII':
            aplicado_fii += valor_aplicado

        preco_atual = get_current_price(ticker)
        saldo_bruto = qtde * preco_atual if preco_atual > 0 else valor_aplicado
        saldo_bruto_total += saldo_bruto

    ganho_rs = saldo_bruto_total - valor_aplicado_total
    ganho_perc = (ganho_rs / valor_aplicado_total) * 100 if valor_aplicado_total > 0 else 0.0

    return {
        'valor_aplicado': valor_aplicado_total,
        'saldo_bruto': saldo_bruto_total,
        'ganho_capital_rs': ganho_rs,
        'ganho_capital_perc': ganho_perc,
        'aplicado_fii': aplicado_fii
    }

def gerar_tabela_proventos(df_proventos):
    if df_proventos.empty:
        return pd.DataFrame(), 0.0

    try:
        df = df_proventos.copy()
        df['Data'] = pd.to_datetime(df['Mês/Ano'], format='%m/%Y', errors='coerce')
        df = df.dropna(subset=['Data'])
        if df.empty:
            return pd.DataFrame(), 0.0
            
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0.0)
            
        df['Ano'] = df['Data'].dt.year
        df['Mês'] = df['Data'].dt.month
        
        meses_map = {
            1: 'jan', 2: 'fev', 3: 'mar', 4: 'abr', 5: 'mai', 6: 'jun',
            7: 'jul', 8: 'ago', 9: 'set', 10: 'out', 11: 'nov', 12: 'dez'
        }
        
        pivot = pd.pivot_table(
            df, 
            values='Valor', 
            index='Ano', 
            columns='Mês', 
            aggfunc='sum', 
            fill_value=0.0
        )
        
        pivot.columns = [meses_map.get(c, str(c)) for c in pivot.columns]
        
        for i in range(1, 13):
            m_str = meses_map[i]
            if m_str not in pivot.columns:
                pivot[m_str] = 0.0
                
        cols_ordered = [meses_map[i] for i in range(1, 13)]
        pivot = pivot[cols_ordered]
        
        total = df['Valor'].sum()
        
        return pivot, total
    except Exception as e:
        logger.error(f"Erro ao gerar tabela de proventos: {e}")
        return pd.DataFrame(), 0.0
"""

with open('utils.py', 'w', encoding='utf-8') as f:
    f.write(code)
