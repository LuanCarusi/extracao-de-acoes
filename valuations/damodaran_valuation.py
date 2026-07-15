import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from utils import fetch_statusinvest_data, get_selic
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Valuation DCF - Damodaran", layout="wide", initial_sidebar_state="collapsed")

# Estilos CSS Futuristas e Simplistas
def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700&family=Roboto:wght@300;400;700&display=swap');
        
        html, body, [class*="css"]  {
            font-family: 'Roboto', sans-serif;
        }
        
        h1, h2, h3 {
            font-family: 'Orbitron', sans-serif;
            color: #00d2ff;
        }
        
        div[data-testid="metric-container"] {
            background-color: #1e1e2f;
            border-left: 4px solid #00d2ff;
            padding: 10px 15px;
            border-radius: 4px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            margin-bottom: 10px;
        }
        
        .header-box {
            background-color: #11111b;
            padding: 10px;
            text-align: center;
            border-bottom: 2px solid #00d2ff;
            margin-bottom: 20px;
            font-weight: bold;
            font-size: 1.2rem;
            color: #ffffff;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border-radius: 5px 5px 0 0;
        }
        
        .stDataFrame {
            border: 1px solid #333;
            border-radius: 5px;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- Funções de Cache de Dados ---

@st.cache_data(ttl=3600)
def get_statusinvest_db():
    return fetch_statusinvest_data()

@st.cache_data(ttl=3600)
def get_taxa_selic():
    return get_selic()

@st.cache_data(ttl=3600)
def get_historical_fcf(ticker):
    try:
        t = yf.Ticker(f"{ticker}.SA")
        cf = t.cash_flow
        
        if cf.empty:
            return None
            
        fcf_row = None
        if 'Free Cash Flow' in cf.index:
            fcf_row = cf.loc['Free Cash Flow']
        elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
            # Capital Expenditure geralmente vem negativo no yfinance
            fcf_row = cf.loc['Operating Cash Flow'] + cf.loc['Capital Expenditure']
            
        if fcf_row is None:
            return None
            
        # Pega os últimos 4 anos disponíveis
        fcf_series = fcf_row.dropna().head(4)
        
        # Inverte para ordem cronológica (mais antigo pro mais recente)
        fcf_series = fcf_series.iloc[::-1]
        
        dates = [pd.to_datetime(d).year for d in fcf_series.index]
        values = fcf_series.values
        
        # Constrói o dataframe histórico
        df = pd.DataFrame({'Ano': dates, 'FCF': values})
        
        # Calcula YoY Growth (CAGR histórico)
        cagrs = [None]
        for i in range(1, len(values)):
            prev = values[i-1]
            curr = values[i]
            if prev != 0 and prev > 0:
                growth = ((curr / prev) - 1) * 100
                cagrs.append(growth)
            else:
                cagrs.append(None)
                
        df['CAGR (%)'] = cagrs
        df['VPL'] = None # Histórico não tem VPL projetado
        return df
    except Exception as e:
        return None

# --- Header ---
st.title("Valuation de Fluxo de Caixa Livre (DCF)")
st.markdown("Modelo baseado em Aswath Damodaran - Projeção de Crescimento e Desconto a Valor Presente.")

# --- Inputs principais ---
col_input1, col_input2, col_input3 = st.columns([2, 1, 1])
with col_input1:
    ticker_input = st.text_input("Ticker da Ação (ex: TAEE11)", value="TAEE11").strip().upper()
with col_input2:
    selic_padrao = get_taxa_selic()
    taxa_desconto = st.number_input("Taxa de Desconto (%)", value=selic_padrao, step=0.1) / 100
with col_input3:
    taxa_perpetuidade = st.number_input("Taxa de Perpetuidade (%)", value=2.0, step=0.1) / 100

if not ticker_input:
    st.stop()

# Busca dados atuais
df_si = get_statusinvest_db()
ticker_data = df_si[df_si['ticker'] == ticker_input]

if ticker_data.empty:
    st.error(f"Ticker {ticker_input} não encontrado no StatusInvest.")
    st.stop()

row = ticker_data.iloc[0]
cotacao_atual = float(row.get('price', 0))
# Market Cap e Número de ações (se valor de mercado não estiver disponível, tenta calcular)
market_cap_atual = float(row.get('valormercado', 0))

# Fallback caso 'valormercado' venha nulo
if pd.isna(market_cap_atual) or market_cap_atual == 0:
    st.warning("Valor de Mercado não disponível no StatusInvest. Não é possível calcular o total de ações.")
    st.stop()

num_acoes = market_cap_atual / cotacao_atual

# Busca FCF histórico
df_hist = get_historical_fcf(ticker_input)
if df_hist is None or df_hist.empty:
    st.error(f"Não foi possível obter dados históricos de Fluxo de Caixa Livre (FCF) no Yahoo Finance para {ticker_input}.")
    st.stop()

# --- Lógica de Projeção Interativa ---
# O usuário precisa definir o CAGR para os próximos 6 anos
current_year = df_hist['Ano'].iloc[-1] + 1
projetados_anos = [current_year + i for i in range(6)]

# Inicializa o estado para os CAGRs projetados, default 5% para simplificar
if 'cagrs' not in st.session_state or st.session_state.get('last_ticker') != ticker_input:
    # Reseta se mudar de ticker
    st.session_state.cagrs = {ano: 5.0 for ano in projetados_anos}
    st.session_state.last_ticker = ticker_input

# Cria o layout principal em duas colunas (Esquerda: Resumo, Direita: Tabela Interativa)
col_esq, col_dir = st.columns([1, 2], gap="large")

with col_dir:
    st.markdown('<div class="header-box">PROJEÇÃO DE FLUXO DE CAIXA (FCF)</div>', unsafe_allow_html=True)
    
    # Prepara a tabela editável apenas na coluna CAGR para os anos projetados
    proj_data = {
        'Ano': projetados_anos,
        'FCF': [0.0] * 6,
        'CAGR (%)': [st.session_state.cagrs[ano] for ano in projetados_anos],
        'VPL': [0.0] * 6
    }
    df_proj_edit = pd.DataFrame(proj_data)
    
    st.markdown("Edite a coluna **CAGR (%)** abaixo para projetar o crescimento do Fluxo de Caixa Livre nos próximos anos:")
    
    # Data Editor
    edited_df = st.data_editor(
        df_proj_edit,
        column_config={
            "Ano": st.column_config.NumberColumn(format="%d", disabled=True),
            "FCF": st.column_config.NumberColumn(format="R$ %.2f", disabled=True),
            "VPL": st.column_config.NumberColumn(format="R$ %.2f", disabled=True),
            "CAGR (%)": st.column_config.NumberColumn(step=1.0, format="%.1f%%")
        },
        hide_index=True,
        use_container_width=True,
        key="editor_cagr"
    )
    
    # Atualiza o estado
    for i, row_ed in edited_df.iterrows():
        ano = int(row_ed['Ano'])
        st.session_state.cagrs[ano] = float(row_ed['CAGR (%)'])
        
    # Recalcula a tabela projetada com os novos CAGRs
    last_fcf = df_hist['FCF'].iloc[-1]
    
    fcf_calculado = []
    vpl_calculado = []
    
    current_fcf = last_fcf
    for idx, ano in enumerate(projetados_anos):
        cagr = st.session_state.cagrs[ano] / 100
        current_fcf = current_fcf * (1 + cagr)
        fcf_calculado.append(current_fcf)
        
        # VPL = FCF / (1 + taxa_desconto)^n
        n = idx + 1 # Ano 1, Ano 2, etc.
        vpl = current_fcf / ((1 + taxa_desconto) ** n)
        vpl_calculado.append(vpl)
        
    # Calcula o Perpétuo
    last_proj_fcf = fcf_calculado[-1]
    last_n = len(projetados_anos)
    
    # TV = FCF_n * (1 + g) / (r - g)
    if taxa_desconto <= taxa_perpetuidade:
        tv_fcf = 0 # Evita divisão por zero ou negativa
        st.error("A Taxa de Desconto deve ser MAIOR que a Taxa de Perpetuidade.")
    else:
        tv_fcf = last_proj_fcf * (1 + taxa_perpetuidade) / (taxa_desconto - taxa_perpetuidade)
        
    # VPL do Perpétuo = TV / (1 + taxa_desconto)^last_n
    vpl_perpetuo = tv_fcf / ((1 + taxa_desconto) ** last_n)
    
    # Constrói o Dataframe final para exibição unindo Histórico, Projetado e Perpétuo
    df_proj_final = pd.DataFrame({
        'Ano': projetados_anos,
        'FCF': fcf_calculado,
        'CAGR (%)': [st.session_state.cagrs[a] for a in projetados_anos],
        'VPL': vpl_calculado
    })
    
    df_perp = pd.DataFrame({
        'Ano': ['Perpétuo'],
        'FCF': [tv_fcf],
        'CAGR (%)': [taxa_perpetuidade * 100],
        'VPL': [vpl_perpetuo]
    })
    
    # Formatação para exibição da tabela consolidada em Markdown/HTML
    df_hist_str = df_hist.copy()
    df_hist_str['Ano'] = df_hist_str['Ano'].astype(str)
    
    df_proj_str = df_proj_final.copy()
    df_proj_str['Ano'] = df_proj_str['Ano'].astype(str)
    
    df_full = pd.concat([df_hist_str, df_proj_str, df_perp], ignore_index=True)
    
    # Aplica formatação de moeda para exibir
    def format_money(val):
        if pd.isna(val): return "-"
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
    def format_perc(val):
        if pd.isna(val): return "-"
        return f"{val:.1f}%"

    df_full['FCF'] = df_full['FCF'].apply(format_money)
    df_full['VPL'] = df_full['VPL'].apply(format_money)
    df_full['CAGR (%)'] = df_full['CAGR (%)'].apply(format_perc)
    
    st.markdown("### Tabela Consolidada (Histórico + Projeções)")
    st.dataframe(df_full, hide_index=True, use_container_width=True)

with col_esq:
    # --- REALIDADE ATUAL ---
    st.markdown('<div class="header-box">REALIDADE ATUAL</div>', unsafe_allow_html=True)
    st.metric("Ticker", ticker_input)
    st.metric("Preço por Ação", f"R$ {cotacao_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.metric("Número Total de Ações", f"{int(num_acoes):,}".replace(",", "."))
    st.metric("Market Cap", f"R$ {market_cap_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- REALIDADE PROJETADA ---
    st.markdown('<div class="header-box">REALIDADE PROJETADA</div>', unsafe_allow_html=True)
    
    # Market Cap Projetado = Soma de todos os VPLs projetados + VPL do Perpétuo
    market_cap_projetado = sum(vpl_calculado) + vpl_perpetuo
    
    # Preço Teto Projetado
    preco_teto = market_cap_projetado / num_acoes
    
    # Upside / Downside
    margem = (preco_teto - cotacao_atual) / cotacao_atual
    
    st.metric("Preço Justo (Teto) por Ação", f"R$ {preco_teto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.metric("Market Cap Projetado", f"R$ {market_cap_projetado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # Cor da margem (Verde para upside, vermelho para downside)
    color = "#00ff88" if margem > 0 else "#ff3366"
    st.markdown(f"""
    <div style="background-color: #1e1e2f; border-left: 4px solid {color}; padding: 10px 15px; border-radius: 4px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <p style="margin:0; font-size: 14px; color: #aaa;">Upside / Downside (Margem)</p>
        <h2 style="margin:0; color: {color}; font-family: 'Orbitron', sans-serif;">{margem * 100:.1f}%</h2>
    </div>
    """, unsafe_allow_html=True)
