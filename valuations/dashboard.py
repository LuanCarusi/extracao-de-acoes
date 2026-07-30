import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import math
import os
import sys
import subprocess
from utils import fetch_statusinvest_data, get_selic
from datetime import datetime

st.set_page_config(page_title="Dashboard de Valuations", layout="wide", initial_sidebar_state="collapsed")

def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #0e1117;
            color: #c9d1d9;
        }
        
        /* Ajuste do container principal para usar melhor o espaço lateral */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 95%;
        }

        h1, h2, h3 {
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 1rem;
        }
        
        /* Cards style */
        .valuation-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 1.5rem;
            height: 100%;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .card-header {
            font-size: 1.1rem;
            font-weight: 600;
            color: #ffffff;
            border-bottom: 1px solid #30363d;
            padding-bottom: 0.8rem;
            margin-bottom: 1.2rem;
            display: flex;
            align-items: center;
        }
        
        .metric-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #21262d;
        }
        
        .metric-row:last-child {
            border-bottom: none;
        }
        
        .metric-label {
            font-size: 0.9rem;
            color: #8b949e;
        }
        
        .metric-value {
            font-size: 1rem;
            font-weight: 500;
            color: #ffffff;
        }
        
        .metric-value-green {
            color: #3fb950;
            font-weight: 600;
        }
        
        .metric-value-red {
            color: #f85149;
            font-weight: 600;
        }
        
        .metric-value-yellow {
            color: #d29922;
            font-weight: 600;
        }

        /* Inputs customizados mais discretos */
        .stNumberInput > div > div > input {
            background-color: #0d1117;
            color: #ffffff;
            border: 1px solid #30363d;
            padding: 0.4rem;
        }
        
        /* Botões customizados */
        .stButton>button {
            background-color: #238636;
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 500;
            padding: 0.5rem 1rem;
            transition: 0.2s;
        }
        .stButton>button:hover {
            background-color: #2ea043;
            border: none;
        }

        /* Expander style */
        .streamlit-expanderHeader {
            background-color: #161b22;
            border-radius: 6px;
            border: 1px solid #30363d;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# Funções de Cache e Utilidades

if 'cenarios_salvos' not in st.session_state:
    st.session_state.cenarios_salvos = []

@st.cache_data(ttl=3600)
def get_statusinvest_db():
    return fetch_statusinvest_data()

@st.cache_data(ttl=3600)
def get_taxa_selic():
    return get_selic()

@st.cache_data(ttl=3600)
def get_historical_net_income(ticker):
    try:
        t = yf.Ticker(f"{ticker}.SA")
        inc = t.income_stmt
        cf  = t.cash_flow

        if inc is None or inc.empty or 'Net Income' not in inc.index:
            return None, None

        ni_series = inc.loc['Net Income'].dropna().head(3).iloc[::-1]
        dates  = [pd.to_datetime(d).year for d in ni_series.index]
        values = ni_series.values.tolist()

        df_hist = pd.DataFrame({'Ano': dates, 'Lucro Líquido': values})

        payout_medio = None
        if cf is not None and not cf.empty and 'Cash Dividends Paid' in cf.index:
            div_series = cf.loc['Cash Dividends Paid'].dropna().head(3).iloc[::-1]
            payouts = []
            for d in div_series.index:
                ano = pd.to_datetime(d).year
                if ano in df_hist['Ano'].values:
                    ni_val = df_hist.loc[df_hist['Ano'] == ano, 'Lucro Líquido'].values[0]
                    div_val = abs(div_series[d])
                    if ni_val > 0:
                        payouts.append(div_val / ni_val * 100)
            if payouts:
                payout_medio = round(float(np.mean(payouts)), 2)

        return df_hist, payout_medio
    except Exception:
        return None, None

def classificar_lynch(indicador):
    if pd.isna(indicador) or indicador <= 0: return "Fora do Range", "red"
    if indicador > 2.0: return "Muito Barata", "green"
    if 1.5 <= indicador <= 2.0: return "Barata", "green"
    if 1.0 <= indicador < 1.5: return "Justo", "yellow"
    return "Cara", "red"

def format_brl(val):
    if pd.isna(val) or val is None: return "-"
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_perc(val):
    if pd.isna(val) or val is None: return "-"
    return f"{val:.2f}%"

def get_color_class(value, invert=False):
    if pd.isna(value): return ""
    if value > 0: return "metric-value-red" if invert else "metric-value-green"
    if value < 0: return "metric-value-green" if invert else "metric-value-red"
    return ""

def render_metric_row(label, value, color_class="", tooltip=None):
    st.markdown(f"""
    <div class="metric-row" title="{tooltip or ''}">
        <span class="metric-label">{label}</span>
        <span class="metric-value {color_class}">{value}</span>
    </div>
    """, unsafe_allow_html=True)

# 1. EXPANDER DE RANKING (SCREENING)
with st.expander("🎯 Ranking de Oportunidades (Screening Automático)", expanded=False):
    st.markdown("Extraia e filtre os melhores ativos do mercado baseados nas suas regras de negócio.")
    
    def rodar_main():
        caminhos_main = [("../analise_de_acoes/main.py", "../analise_de_acoes"), ("analise_de_acoes/main.py", "analise_de_acoes")]
        for arq, cwd in caminhos_main:
            if os.path.exists(arq):
                try:
                    result = subprocess.run([sys.executable, "main.py"], cwd=cwd, check=True, capture_output=True, text=True)
                    return True, ""
                except subprocess.CalledProcessError as e:
                    return False, f"Erro (código {e.returncode}):\n{e.stderr}"
                except Exception as e:
                    return False, str(e)
        return False, "Arquivo main.py não encontrado."

    caminhos_csv = ["../analise_de_acoes/ranking_acoes_resultado.csv", "../ranking_acoes_resultado.csv", "ranking_acoes_resultado.csv"]
    df_ranking = None
    for path in caminhos_csv:
        if os.path.exists(path):
            try:
                df_ranking = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
                break
            except Exception: pass

    col_btn_rank, _ = st.columns([2, 8])
    with col_btn_rank:
        if st.button("🔄 Executar Crawler e Gerar Ranking"):
            with st.spinner("Extraindo e rankeando mercado..."):
                sucesso, msg = rodar_main()
                if sucesso:
                    st.success("Ranking atualizado com sucesso!")
                    st.rerun()
                else:
                    st.error(msg)
                    
    if df_ranking is not None and not df_ranking.empty:
        if 'Setor' in df_ranking.columns:
            setores = sorted(df_ranking['Setor'].dropna().unique().tolist())
            filtro_setor = st.multiselect("Filtrar por Setor:", options=setores, default=[])
            if filtro_setor:
                df_ranking = df_ranking[df_ranking['Setor'].isin(filtro_setor)]
        st.dataframe(df_ranking, hide_index=True, use_container_width=True, height=250)
    else:
        st.info("Nenhum ranking gerado ainda. Clique no botão acima para iniciar.")

st.markdown("---")

# 2. BUSCADOR PRINCIPAL
col_busca, _ = st.columns([3, 7])
with col_busca:
    ticker_input = st.text_input("🔍 Buscar Ativo para Valuation (ex: BBSE3)", value="").strip().upper()

selic_padrao = get_taxa_selic()

if ticker_input:
    df_si = get_statusinvest_db()
    ticker_data = df_si[df_si['ticker'] == ticker_input]

    if ticker_data.empty:
        st.error(f"Ticker '{ticker_input}' não encontrado na base de dados (StatusInvest).")
    else:
        row = ticker_data.iloc[0]
        cotacao_atual = float(row.get('price', 0) or 0)
        market_cap_atual = float(row.get('valormercado', 0) or 0)
        num_acoes = market_cap_atual / cotacao_atual if cotacao_atual > 0 and market_cap_atual > 0 else 0
        
        # Variáveis globais para os modelos
        dy_atual = float(row.get('dy', 0) or 0)
        vpa = float(row.get('vpa', 0) or 0)
        lpa = float(row.get('lpa', 0) or 0)
        pl = float(row.get('p_l', 0) or 0)
        roe = float(row.get('roe', 0) or 0)
        
        with st.spinner("Buscando dados históricos de balanço..."):
            df_hist_ni, payout_medio_hist = get_historical_net_income(ticker_input)
            tem_dados_damodaran = df_hist_ni is not None and not df_hist_ni.empty

        # ---------------------------------------------------------
        # GRID LINHA 1: BAZIN, GRAHAM, PETER LYNCH
        # ---------------------------------------------------------
        col_bazin, col_graham, col_lynch = st.columns(3)
        
        # -- CARD BAZIN --
        with col_bazin:
            st.markdown('<div class="valuation-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">📊 Valuation Bazin</div>', unsafe_allow_html=True)
            
            dpa_atual = cotacao_atual * (dy_atual / 100)
            render_metric_row("Dividend Yield (12m)", format_perc(dy_atual))
            render_metric_row("DPA (12m)", format_brl(dpa_atual))
            
            dy_desejado_bazin = st.number_input("Dividend Yield Desejado (%)", min_value=0.1, value=6.0, step=0.5, key="bazin_dy")
            
            preco_teto_bazin = dpa_atual / (dy_desejado_bazin / 100) if dy_desejado_bazin > 0 else 0
            margem_bazin = (preco_teto_bazin - cotacao_atual) / cotacao_atual if cotacao_atual > 0 else 0
            
            st.markdown("<hr style='border-color: #30363d; margin: 15px 0;'>", unsafe_allow_html=True)
            render_metric_row("Preço Teto do Bazin", format_brl(preco_teto_bazin), "metric-value-green")
            render_metric_row("Margem de Segurança", format_perc(margem_bazin * 100), get_color_class(margem_bazin))
            
            st.markdown('</div>', unsafe_allow_html=True)

        # -- CARD GRAHAM --
        with col_graham:
            st.markdown('<div class="valuation-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">📈 Valuation Graham</div>', unsafe_allow_html=True)
            
            render_metric_row("Lucro por Ação (LPA)", format_brl(lpa))
            render_metric_row("Valor Patrimonial (VPA)", format_brl(vpa))
            
            # Espaçador para manter altura simétrica com os inputs das outras colunas
            st.write("")
            st.write("")
            st.write("")
            st.write("")
            
            if vpa > 0 and lpa > 0:
                vi_graham = math.sqrt(22.5 * lpa * vpa)
                margem_graham = (vi_graham - cotacao_atual) / cotacao_atual if cotacao_atual > 0 else 0
            else:
                vi_graham = 0
                margem_graham = 0
                
            st.markdown("<hr style='border-color: #30363d; margin: 15px 0;'>", unsafe_allow_html=True)
            if vpa > 0 and lpa > 0:
                render_metric_row("Preço Teto do Graham", format_brl(vi_graham), "metric-value-green")
                render_metric_row("Margem de Segurança", format_perc(margem_graham * 100), get_color_class(margem_graham))
            else:
                st.warning("VPA ou LPA negativos impedem o cálculo.")
                
            st.markdown('</div>', unsafe_allow_html=True)
            
        # -- CARD PETER LYNCH --
        with col_lynch:
            st.markdown('<div class="valuation-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">🚀 Valuation Peter Lynch</div>', unsafe_allow_html=True)
            
            render_metric_row("P/L", f"{pl:.2f}")
            render_metric_row("ROE", format_perc(roe))
            
            crescimento_lynch = st.number_input("Crescimento Projetivo (%)", value=3.0, step=0.5, key="lynch_crescimento")
            
            if pl > 0:
                ind_lynch = (dy_atual + crescimento_lynch) / pl
                classif_lynch, cor_lynch = classificar_lynch(ind_lynch)
            else:
                ind_lynch = 0
                classif_lynch, cor_lynch = "Inaplicável", "red"
                
            st.markdown("<hr style='border-color: #30363d; margin: 15px 0;'>", unsafe_allow_html=True)
            if pl > 0:
                render_metric_row("Indicador Peter Lynch", f"{ind_lynch:.2f}")
                render_metric_row("Classificação", classif_lynch, f"metric-value-{cor_lynch}")
            else:
                st.warning("P/L negativo ou zero impede o cálculo.")
                
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ---------------------------------------------------------
        # GRID LINHA 2: PREÇO TETO PROJETIVO E DAMODARAN
        # ---------------------------------------------------------
        col_proj_in, col_proj_out, col_damo = st.columns([1, 1, 1])
        
        # Pega lucro histórico se houver
        if df_hist_ni is not None and not df_hist_ni.empty:
            ultimo_ll_proj_base = float(df_hist_ni['Lucro Líquido'].iloc[-1])
        else:
            ultimo_ll_proj_base = 0.0
            
        payout_padrao_proj = payout_medio_hist if payout_medio_hist is not None else 50.0

        # -- CARD PREÇO TETO (INPUTS) --
        with col_proj_in:
            st.markdown('<div class="valuation-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">⚙️ Preço Teto Projetivo</div>', unsafe_allow_html=True)
            
            dy_proj = st.number_input("Dividend Yield Desejado (%)", value=6.0, step=0.5, key="proj_dy")
            payout_proj = st.number_input("Payout da Empresa (%)", value=round(payout_padrao_proj, 2), step=1.0, key="proj_payout")
            lucro_proj = st.number_input("Lucro Líquido Projetado (R$)", value=round(ultimo_ll_proj_base, 0), step=10_000_000.0, format="%.0f", key="proj_lucro")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Salvar Cenário Atual"):
                # Cálculo rápido para salvar
                lpa_p = lucro_proj / num_acoes if num_acoes > 0 else 0
                dpa_p = lpa_p * (payout_proj / 100)
                teto_p = dpa_p / (dy_proj / 100) if dy_proj > 0 else 0
                margem_p = (teto_p - cotacao_atual) / cotacao_atual if cotacao_atual > 0 else 0
                yield_p = (dpa_p / cotacao_atual) * 100 if cotacao_atual > 0 else 0
                
                cenario = {
                    "Ativo": ticker_input,
                    "Preço Teto": teto_p,
                    "Margem": margem_p * 100,
                    "Yield Proj": yield_p
                }
                st.session_state.cenarios_salvos.append(cenario)
                
            if len(st.session_state.cenarios_salvos) > 0:
                with st.expander("Ver cenários salvos"):
                    st.dataframe(pd.DataFrame(st.session_state.cenarios_salvos))
                    if st.button("Limpar Histórico"):
                        st.session_state.cenarios_salvos = []
                        st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        # -- CARD PREÇO TETO (OUTPUTS) --
        with col_proj_out:
            st.markdown('<div class="valuation-card" style="display:flex; flex-direction:column; justify-content:center;">', unsafe_allow_html=True)
            
            if num_acoes > 0:
                lpa_proj_out = lucro_proj / num_acoes
                dpa_proj_out = lpa_proj_out * (payout_proj / 100)
                preco_teto_proj_out = dpa_proj_out / (dy_proj / 100) if dy_proj > 0 else 0
                margem_teto_proj_out = (preco_teto_proj_out - cotacao_atual) / cotacao_atual if cotacao_atual > 0 else 0
                yield_proj_cotacao_out = (dpa_proj_out / cotacao_atual) * 100 if cotacao_atual > 0 else 0
                
                render_metric_row("Cotação Atual", format_brl(cotacao_atual))
                render_metric_row("Número de Papéis", f"{int(num_acoes):,}".replace(",", "."))
                st.markdown("<hr style='border-color: #30363d; margin: 10px 0;'>", unsafe_allow_html=True)
                
                render_metric_row("DPA Projetivo", format_brl(dpa_proj_out))
                render_metric_row("Preço Teto", format_brl(preco_teto_proj_out), "metric-value-green")
                render_metric_row("Yield (Projetivo)", format_perc(yield_proj_cotacao_out), get_color_class(yield_proj_cotacao_out - dy_proj))
                render_metric_row("Margem Segurança", format_perc(margem_teto_proj_out * 100), get_color_class(margem_teto_proj_out))
            else:
                st.error("Número de ações inválido ou não disponível no StatusInvest.")
                
            st.markdown('</div>', unsafe_allow_html=True)

        # -- CARD DAMODARAN (FLUXO DE CAIXA / LUCRO DESCONTADO) --
        with col_damo:
            st.markdown('<div class="valuation-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">💸 Valuation Fluxo de Caixa</div>', unsafe_allow_html=True)
            
            if not tem_dados_damodaran:
                st.warning("Sem dados históricos (Yahoo Finance) para projetar o Fluxo.")
            else:
                st.markdown("""
                Este modelo projeta o Lucro Líquido descontado a valor presente, estimando o **Preço Justo** (Damodaran).
                """)
                
                with st.expander("Abrir Calculadora Damodaran", expanded=False):
                    ano_atual = datetime.now().year
                    anos_projetados = [ano_atual + i for i in range(1, 4)]
                    
                    st.markdown("**Parâmetros Globais**")
                    taxa_desc = st.number_input("Taxa de Desconto (%)", value=selic_padrao, step=0.1, key="damo_desc") / 100
                    taxa_perp = st.number_input("Taxa Perpetuidade (%)", value=2.0, step=0.1, key="damo_perp") / 100
                    
                    payout_damo = st.number_input("Payout (%)", value=round(payout_padrao_proj, 2), key="damo_payout")
                    ll_atual = st.number_input("Lucro Ano Atual", value=round(ultimo_ll_proj_base, 0), step=1_000_000.0, key="damo_ll")
                    
                    payout_dec = payout_damo / 100
                    g_calc = (1 - payout_dec) * roe
                    st.caption(f"**Taxa Cresc.(g) Calculada:** {g_calc:.2f}% (usado para projetar os CAGRs abaixo)")
                    
                    state_key_cagr = f"cagrs_{ticker_input}"
                    if state_key_cagr not in st.session_state:
                        st.session_state[state_key_cagr] = {ano: round(g_calc, 2) for ano in anos_projetados}
                        
                    df_ed = pd.DataFrame({'Ano': anos_projetados, 'CAGR (%)': [st.session_state[state_key_cagr][a] for a in anos_projetados]})
                    df_ed = st.data_editor(df_ed, hide_index=True, use_container_width=True, key="damo_editor")
                    
                    for _, r in df_ed.iterrows():
                        st.session_state[state_key_cagr][int(r['Ano'])] = float(r['CAGR (%)'])
                        
                    # Cálculos
                    ll_proj = []
                    vpls = []
                    curr_ll = ll_atual
                    for idx, a in enumerate(anos_projetados):
                        c = st.session_state[state_key_cagr][a] / 100
                        curr_ll *= (1 + c)
                        ll_proj.append(curr_ll)
                        vpls.append(curr_ll / ((1 + taxa_desc) ** (idx + 1)))
                        
                    if taxa_desc <= taxa_perp:
                        st.error("Desconto deve ser > Perpetuidade.")
                    else:
                        tv = ll_proj[-1] * (1 + taxa_perp) / (taxa_desc - taxa_perp)
                        vpl_perp = tv / ((1 + taxa_desc) ** len(anos_projetados))
                        
                        mkt_cap_damo = sum(vpls) + vpl_perp
                        preco_justo_damo = mkt_cap_damo / num_acoes if num_acoes > 0 else 0
                        margem_damo = (preco_justo_damo - cotacao_atual) / cotacao_atual if cotacao_atual > 0 else 0
                        
                        st.markdown("<hr style='border-color: #30363d; margin: 10px 0;'>", unsafe_allow_html=True)
                        render_metric_row("Preço Justo (DCF)", format_brl(preco_justo_damo), "metric-value-green")
                        render_metric_row("Upside / Downside", format_perc(margem_damo * 100), get_color_class(margem_damo))
            
            st.markdown('</div>', unsafe_allow_html=True)
