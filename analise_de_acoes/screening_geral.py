import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

URL = "https://statusinvest.com.br/category/advancedsearchresultpaginated?search=%7B%22Sector%22%3A%22%22%2C%22SubSector%22%3A%22%22%2C%22Segment%22%3A%22%22%2C%22my_range%22%3A%22-20%3B100%22%2C%22forecast%22%3A%7B%22upsidedownside%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22estimatesnumber%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22revisedup%22%3Atrue%2C%22reviseddown%22%3Atrue%2C%22consensus%22%3A%5B%5D%7D%2C%22dy%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_l%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22peg_ratio%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_vp%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margembruta%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margemebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margemliquida%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22ev_ebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22dividaliquidaebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22dividaliquidapatrimonioliquido%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_sr%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_capitalgiro%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ativocirculante%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roe%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roic%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22liquidezcorrente%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22pl_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22passivo_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22giroativos%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22receitas_cagr5%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22lucros_cagr5%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22liquidezmediadiaria%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22vpa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22lpa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22valormercado%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%7D&orderColumn=&isAsc=&page=0&take=617&CategoryType=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def buscando_dados():
    response = requests.get(URL, headers=HEADERS)
    response.raise_for_status()
    return pd.DataFrame(response.json()["list"])

def filtros(df):
    df = df[['companyname', 'ticker', 'price','dy', 'p_l', 'margemliquida', 'dividaliquidaebit','roe', 'roic','liquidezmediadiaria']] #Indicadores que interessam
    df = df[df['liquidezmediadiaria'] >=1_000_000]
    df = df[df['roic'] >=7.9 ]
    df = df[df['dy'] >=5]
    df = df[df['p_l'] <=15.1] 
    df = df[df['margemliquida'] >=4.9]
    df = df[df['dividaliquidaebit'] <=5.5]
    df = df[df['roe'] >=9.5]   

    return df

def rankings(df):
    df["ranking_dy"] = df["dy"].rank(ascending=False, method="first")
    df["ranking_p_l"] = df["p_l"].rank(ascending=True, method="first")
    df["ranking_marg_liq"] = df["margemliquida"].rank(ascending=False, method="first")
    df["ranking_divida"] = df["dividaliquidaebit"].rank(ascending=True, method="first")
    df["ranking_roe"] = df["roe"].rank(ascending=False, method="first")

    df["score_final"] = df[
        ["ranking_dy", "ranking_p_l", "ranking_marg_liq",
         "ranking_divida", "ranking_roe"]
    ].sum(axis=1)

    # Ordena pelo score
    df = df.sort_values("score_final")

    # Seleciona colunas finais
    colunas_finais = [
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
        "liquidezmediadiaria"
    ]

    df_final = df[colunas_finais]

    return df_final

def get_setor(ticker):
    url = f"https://www.fundamentus.com.br/detalhes.php?papel={ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    links = soup.find_all("a", href=True)

    setor = None

    for link in links:
        href = link["href"]

        if "resultado.php?segmento=" in href:
            setor = link.text.strip()
            break

    return {
        "ticker": ticker,
        "setor": setor
    }

def buscar_setores(df):
    tickers = df["ticker"].tolist()

    resultados = []

    for ticker in tickers:
        print(f"Buscando setor de {ticker}...")
        try:
            resultados.append(get_setor(ticker))
            time.sleep(0.25)
        except Exception as e:
            print(f"Erro em {ticker}: {e}")
            resultados.append({"ticker": ticker, "setor": None})

    return pd.DataFrame(resultados)

def adicionar_setor(df, df_setores):
    df = df.merge(df_setores, on="ticker", how="left")

    coluna_setor = df.pop("setor")
    posicao = df.columns.get_loc("ticker") + 1

    df.insert(posicao, "setor", coluna_setor)

    return df


def main():
    df = buscando_dados()
    df = filtros(df)

    # 🔹 busca setores antes do ranking (melhor prática)
    df_setores = buscar_setores(df)
    df = adicionar_setor(df, df_setores)

    df = rankings(df)

    print(df)
    #df.to_csv("ranking_acoes.csv", index=False)

main()
