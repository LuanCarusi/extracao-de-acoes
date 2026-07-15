import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import math
from utils import fetch_statusinvest_data, get_selic
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Dashboard Consolidado de Valuations", layout="wide", initial_sidebar_state="collapsed")

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
            fcf_row = cf.loc['Operating Cash Flow'] + cf.loc['Capital Expenditure']
            
        if fcf_row is None:
            return None
            
        fcf_series = fcf_row.dropna().head(4)
        fcf_series = fcf_series.iloc[::-1]
        
        dates = [pd.to_datetime(d).year for d in fcf_series.index]
        values = fcf_series.values
        
        df = pd.DataFrame({'Ano': dates, 'FCF': values})
        
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
        df['VPL'] = None
        return df
    except Exception as e:
        return None

def classificar_lynch(indicador):
    if pd.isna(indicador) or indicador <= 0:
        return "Fora do Range"
    if indicador > 2.0:
        return "Muito Barata"
    elif 1.5 <= indicador <= 2.0:
        return "Barata"
    elif 1.0 <= indicador < 1.5:
        return "Justo"
    elif indicador < 1.0:
        return "Cara"
    return "Fora do Range"

# --- Header ---
st.title("🚀 Dashboard Consolidado de Valuations")
st.markdown("Compare diferentes metodologias de valuation (Damodaran, Bazin, Graham, Lynch) para uma mesma ação em tempo real.")

# --- Inputs principais ---
st.markdown('<div class="header-box">PARÂMETROS GERAIS</div>', unsafe_allow_html=True)
col_input1, col_input2, col_input3, col_input4 = st.columns([2, 1, 1, 1])
with col_input1:
    ticker_input = st.text_input("Ticker da Ação (ex: TAEE11)", value="TAEE11").strip().upper()
with col_input2:
    selic_padrao = get_taxa_selic()
    taxa_desconto = st.number_input("Taxa de Desconto (%)", value=selic_padrao, step=0.1) / 100
with col_input3:
    taxa_perpetuidade = st.number_input("Taxa de Perpetuidade (%)", value=2.0, step=0.1) / 100
with col_input4:
    crescimento_lynch = st.number_input("Crescimento (Lynch) (%)", value=3.0, step=0.1)

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
market_cap_atual = float(row.get('valormercado', 0))

if pd.isna(market_cap_atual) or market_cap_atual == 0:
    st.warning("Valor de Mercado não disponível no StatusInvest. Não é possível calcular o total de ações.")
    st.stop()

num_acoes = market_cap_atual / cotacao_atual

# Busca FCF histórico (para Damodaran)
with st.spinner("Buscando dados históricos e fundamentalistas..."):
    df_hist = get_historical_fcf(ticker_input)
    tem_dados_damodaran = df_hist is not None and not df_hist.empty

st.markdown('<div class="header-box">VISÃO GERAL DO ATIVO</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Ticker", ticker_input)
c2.metric("Cotação Atual", f"R$ {cotacao_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
c3.metric("Número de Ações", f"{int(num_acoes):,}".replace(",", "."))
c4.metric("Market Cap", f"R$ {market_cap_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("<br>", unsafe_allow_html=True)

# Layout com Abas para cada Valuation
tab1, tab2, tab3, tab4 = st.tabs(["Fluxo de Caixa Descontado (Damodaran)", "Preço Teto (Décio Bazin)", "Valor Intrínseco (Graham)", "Fair Value (Peter Lynch)"])

# ==========================================
# ABA 1: DAMODARAN
# ==========================================
with tab1:
    if not tem_dados_damodaran:
        st.error(f"Não foi possível obter dados históricos de Fluxo de Caixa Livre (FCF) no Yahoo Finance para {ticker_input}.")
    else:
        st.markdown("### Modelo de Damodaran (DCF)")
        
        current_year = df_hist['Ano'].iloc[-1] + 1
        projetados_anos = [current_year + i for i in range(6)]

        if 'cagrs' not in st.session_state or st.session_state.get('last_ticker') != ticker_input:
            st.session_state.cagrs = {ano: 5.0 for ano in projetados_anos}
            st.session_state.last_ticker = ticker_input

        col_esq, col_dir = st.columns([1, 2], gap="large")

        with col_dir:
            st.markdown('#### Projeção de CAGR')
            st.markdown("Edite apenas o **CAGR (%)** projetado. O FCL e VPL são calculados automaticamente.")
            
            proj_data_input = {
                'Ano': projetados_anos,
                'CAGR (%)': [st.session_state.cagrs[ano] for ano in projetados_anos]
            }
            df_proj_edit = pd.DataFrame(proj_data_input)
            
            edited_df = st.data_editor(
                df_proj_edit,
                column_config={
                    "Ano": st.column_config.NumberColumn(format="%d", disabled=True),
                    "CAGR (%)": st.column_config.NumberColumn(step=1.0, format="%.1f%%")
                },
                hide_index=True,
                use_container_width=True,
                key="editor_cagr_dash"
            )
            
            for i, row_ed in edited_df.iterrows():
                ano = int(row_ed['Ano'])
                st.session_state.cagrs[ano] = float(row_ed['CAGR (%)'])
                
            last_fcf = df_hist['FCF'].iloc[-1]
            
            fcf_calculado = []
            vpl_calculado = []
            
            current_fcf = last_fcf
            for idx, ano in enumerate(projetados_anos):
                cagr = st.session_state.cagrs[ano] / 100
                current_fcf = current_fcf * (1 + cagr)
                fcf_calculado.append(current_fcf)
                
                n = idx + 1
                vpl = current_fcf / ((1 + taxa_desconto) ** n)
                vpl_calculado.append(vpl)
                
            last_proj_fcf = fcf_calculado[-1]
            last_n = len(projetados_anos)
            
            if taxa_desconto <= taxa_perpetuidade:
                tv_fcf = 0
                st.error("A Taxa de Desconto deve ser MAIOR que a Taxa de Perpetuidade.")
            else:
                tv_fcf = last_proj_fcf * (1 + taxa_perpetuidade) / (taxa_desconto - taxa_perpetuidade)
                
            vpl_perpetuo = tv_fcf / ((1 + taxa_desconto) ** last_n)
            
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
            
            df_hist_str = df_hist.copy()
            df_hist_str['Ano'] = df_hist_str['Ano'].astype(str)
            
            df_proj_str = df_proj_final.copy()
            df_proj_str['Ano'] = df_proj_str['Ano'].astype(str)
            
            df_full = pd.concat([df_hist_str, df_proj_str, df_perp], ignore_index=True)
            
            def format_money(val):
                if pd.isna(val): return "-"
                return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
            def format_perc(val):
                if pd.isna(val): return "-"
                return f"{val:.1f}%"

            df_full['FCF'] = df_full['FCF'].apply(format_money)
            df_full['VPL'] = df_full['VPL'].apply(format_money)
            df_full['CAGR (%)'] = df_full['CAGR (%)'].apply(format_perc)
            
            st.markdown("#### Tabela Consolidada (Histórico + Projeções)")
            st.dataframe(df_full, hide_index=True, use_container_width=True)

        with col_esq:
            st.markdown('#### Resultado (Damodaran)')
            
            market_cap_projetado = sum(vpl_calculado) + vpl_perpetuo
            preco_teto_damo = market_cap_projetado / num_acoes
            margem_damo = (preco_teto_damo - cotacao_atual) / cotacao_atual
            
            st.metric("Preço Justo (DCF)", f"R$ {preco_teto_damo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.metric("Market Cap Projetado", f"R$ {market_cap_projetado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            color_damo = "#00ff88" if margem_damo > 0 else "#ff3366"
            st.markdown(f"""
            <div style="background-color: #1e1e2f; border-left: 4px solid {color_damo}; padding: 10px 15px; border-radius: 4px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <p style="margin:0; font-size: 14px; color: #aaa;">Upside / Downside (Margem)</p>
                <h2 style="margin:0; color: {color_damo}; font-family: 'Orbitron', sans-serif;">{margem_damo * 100:.1f}%</h2>
            </div>
            """, unsafe_allow_html=True)


# ==========================================
# ABA 2: BAZIN
# ==========================================
with tab2:
    st.markdown("### Preço Teto de Décio Bazin")
    dy_atual = float(row.get('dy', 0))
    
    if dy_atual == 0:
        st.warning("Empresa não pagou dividendos ou dado indisponível.")
    else:
        dpa = cotacao_atual * (dy_atual / 100)
        preco_teto_bazin = dpa / 0.06
        margem_bazin = (preco_teto_bazin - cotacao_atual) / cotacao_atual
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Dividend Yield Atual", f"{dy_atual:.2f}%")
        c2.metric("Preço Teto (6% DY)", f"R$ {preco_teto_bazin:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        color_bazin = "#00ff88" if margem_bazin > 0 else "#ff3366"
        with c3:
            st.markdown(f"""
            <div style="background-color: #1e1e2f; border-left: 4px solid {color_bazin}; padding: 10px 15px; border-radius: 4px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <p style="margin:0; font-size: 14px; color: #aaa;">Margem de Segurança</p>
                <h2 style="margin:0; color: {color_bazin}; font-family: 'Orbitron', sans-serif;">{margem_bazin * 100:.1f}%</h2>
            </div>
            """, unsafe_allow_html=True)
            
        st.info("A fórmula de Bazin exige no mínimo 6% de Dividend Yield para que o investimento valha a pena. O preço teto é calculado dividindo os dividendos por ação dos últimos 12 meses por 0.06.")

# ==========================================
# ABA 3: GRAHAM
# ==========================================
with tab3:
    st.markdown("### Valor Intrínseco de Benjamin Graham")
    vpa = float(row.get('vpa', 0))
    lpa = float(row.get('lpa', 0))
    
    c1, c2 = st.columns(2)
    c1.metric("VPA (Valor Patrimonial por Ação)", f"R$ {vpa:.2f}")
    c2.metric("LPA (Lucro por Ação)", f"R$ {lpa:.2f}")
    
    if vpa <= 0 or lpa <= 0:
        st.warning("VPA e/ou LPA são negativos ou zerados. A fórmula de Graham não se aplica a empresas com prejuízo ou patrimônio líquido negativo.")
    else:
        valor_intrinseco_graham = math.sqrt(22.5 * lpa * vpa)
        margem_graham = (valor_intrinseco_graham - cotacao_atual) / cotacao_atual
        
        c3, c4 = st.columns(2)
        c3.metric("Valor Intrínseco (Graham)", f"R$ {valor_intrinseco_graham:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        color_graham = "#00ff88" if margem_graham > 0 else "#ff3366"
        with c4:
            st.markdown(f"""
            <div style="background-color: #1e1e2f; border-left: 4px solid {color_graham}; padding: 10px 15px; border-radius: 4px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <p style="margin:0; font-size: 14px; color: #aaa;">Margem de Segurança</p>
                <h2 style="margin:0; color: {color_graham}; font-family: 'Orbitron', sans-serif;">{margem_graham * 100:.1f}%</h2>
            </div>
            """, unsafe_allow_html=True)
            
        st.info("O Valor Intrínseco de Graham é calculado usando a fórmula: Raiz Quadrada de (22.5 * LPA * VPA). Graham sugere buscar margens de segurança de no mínimo 80%.")

# ==========================================
# ABA 4: PETER LYNCH
# ==========================================
with tab4:
    st.markdown("### Fair Value de Peter Lynch")
    pl = float(row.get('p_l', 0))
    roe = float(row.get('roe', 0))
    dy = float(row.get('dy', 0))
    
    c1, c2, c3 = st.columns(3)
    c1.metric("P/L", f"{pl:.2f}")
    c2.metric("ROE", f"{roe:.2f}%")
    c3.metric("Dividend Yield", f"{dy:.2f}%")
    
    if roe < selic_padrao:
        st.warning(f"Cuidado: O ROE desta empresa ({roe:.2f}%) está abaixo da Taxa Selic ({selic_padrao:.2f}%). O custo de oportunidade pode não compensar o risco.")
        
    if pl <= 0:
        st.error("P/L negativo ou zero. A empresa está apresentando prejuízo, logo o indicador de Lynch não pode ser calculado.")
    else:
        indicador_lynch = (dy + crescimento_lynch) / pl
        classificacao = classificar_lynch(indicador_lynch)
        
        c4, c5 = st.columns(2)
        c4.metric("Indicador Lynch", f"{indicador_lynch:.2f}")
        
        color_lynch = "#00ff88" if classificacao in ["Barata", "Muito Barata"] else "#ffcc00" if classificacao == "Justo" else "#ff3366"
        with c5:
            st.markdown(f"""
            <div style="background-color: #1e1e2f; border-left: 4px solid {color_lynch}; padding: 10px 15px; border-radius: 4px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <p style="margin:0; font-size: 14px; color: #aaa;">Classificação</p>
                <h2 style="margin:0; color: {color_lynch}; font-family: 'Orbitron', sans-serif;">{classificacao}</h2>
            </div>
            """, unsafe_allow_html=True)
            
        st.info("A fórmula de Lynch que utilizamos: (Dividend Yield + Crescimento Esperado) / P/L. Quanto maior o indicador, mais barata a ação.")
