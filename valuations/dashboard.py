import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import math
import os
import sys
import subprocess
import json
import altair as alt
from datetime import datetime
from utils import fetch_statusinvest_data, get_selic, calcular_metricas_carteira, gerar_tabela_proventos

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO E CSS (SEM CORTAR ABAS OU COMPONENTES)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Dashboard de Valuations", layout="wide", initial_sidebar_state="collapsed")

def apply_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
        }

        .block-container {
            padding-top: 2.5rem;
            padding-bottom: 2rem;
            max-width: 98%;
            overflow: visible !important;
        }

        /* Top KPI Cards */
        .kpi-card {
            background-color: #161b22;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 10px;
        }
        .kpi-title {
            font-size: 0.75rem;
            font-weight: 700;
            color: #38bdf8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        .kpi-value {
            font-size: 1.2rem;
            font-weight: 700;
            color: #ffffff;
        }

        /* Panels / Boxes */
        .panel-box {
            background-color: #161b22;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 18px;
            margin-bottom: 15px;
        }
        
        .panel-header {
            font-size: 1.1rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 15px;
        }

        /* Metric Rows */
        .metric-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #21262d;
        }
        .metric-row:last-child {
            border-bottom: none;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #8b949e;
        }
        .metric-val {
            font-size: 0.95rem;
            font-weight: 600;
            color: #ffffff;
        }
        .metric-val-blue { color: #38bdf8; font-weight: 700; font-size: 1.05rem; }
        .metric-val-green { color: #3fb950; font-weight: 700; font-size: 1.05rem; }
        .metric-val-red { color: #f85149; font-weight: 700; font-size: 1.05rem; }

        /* Estilização limpa das abas para evitar cortes */
        .stTabs {
            overflow: visible !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            border-bottom: 1px solid #21262d;
            gap: 10px;
            overflow: visible !important;
            flex-wrap: wrap;
            padding-top: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            color: #8b949e;
            font-weight: 600;
            padding-top: 8px;
            padding-bottom: 8px;
            white-space: nowrap;
        }
        .stTabs [aria-selected="true"] {
            color: #ffffff !important;
            border-bottom-color: #38bdf8 !important;
        }

        /* Contêineres padrão Streamlit */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 8px;
            border: 1px solid #21262d;
            background-color: #161b22;
            padding: 0.8rem;
        }

        hr { border-color: #21262d; }
    </style>
    """, unsafe_allow_html=True)

apply_custom_css()

# -----------------------------------------------------------------------------
# 2. CACHE E FUNÇÕES AUXILIARES
# -----------------------------------------------------------------------------
CENARIOS_FILE = "cenarios_salvos.json"

def load_cenarios():
    if os.path.exists(CENARIOS_FILE):
        try:
            with open(CENARIOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_cenarios(cenarios):
    with open(CENARIOS_FILE, "w", encoding="utf-8") as f:
        json.dump(cenarios, f, indent=4, ensure_ascii=False)

if 'cenarios_salvos' not in st.session_state:
    st.session_state.cenarios_salvos = load_cenarios()

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

        ni_series = inc.loc['Net Income'].dropna().head(5).iloc[::-1]
        dates  = [pd.to_datetime(d).year for d in ni_series.index]
        values = ni_series.values.tolist()

        df_hist = pd.DataFrame({'Ano': dates, 'Lucro Líquido': values})

        payout_medio = None
        if cf is not None and not cf.empty and 'Cash Dividends Paid' in cf.index:
            div_series = cf.loc['Cash Dividends Paid'].dropna().head(5).iloc[::-1]
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

def format_brl(val):
    if pd.isna(val) or val is None: return "-"
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_perc(val):
    if pd.isna(val) or val is None: return "-"
    return f"{val:.2f}%"

def formatar_grandeza(valor):
    if pd.isna(valor) or valor is None: return "-"
    abs_valor = abs(valor)
    sinal = "-" if valor < 0 else ""
    if abs_valor >= 1_000_000_000_000:
        return f"R$ {sinal}{abs_valor/1_000_000_000_000:.2f} trilhões".replace(".", ",")
    elif abs_valor >= 1_000_000_000:
        return f"R$ {sinal}{abs_valor/1_000_000_000:.2f} bilhões".replace(".", ",")
    elif abs_valor >= 1_000_000:
        return f"R$ {sinal}{abs_valor/1_000_000:.2f} milhões".replace(".", ",")
    return f"R$ {sinal}{abs_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_color_class(value):
    if pd.isna(value): return ""
    return "metric-val-green" if value >= 0 else "metric-val-red"

def render_kpi(title, value):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def render_metric_row(label, value, color_class=""):
    st.markdown(f"""
    <div class="metric-row">
        <span class="metric-label">{label}</span>
        <span class="metric-val {color_class}">{value}</span>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. ABAS DA APLICAÇÃO
# -----------------------------------------------------------------------------

tab_val, tab_ranking, tab_carteira = st.tabs([
    "📊 Valuation Consolidado", 
    "🎯 Ranking de Oportunidades", 
    "💼 Carteira de Proventos"
])

# =============================================================================
# ABA 1: VALUATION CONSOLIDADO
# =============================================================================
with tab_val:
    col_busca, _ = st.columns([3, 7])
    with col_busca:
        ticker_input = st.text_input("🔍 Buscar Ativo para Valuation (ex: BBSE3)", value="BBSE3").strip().upper()
    
    st.markdown(
        """
        <div style='margin-top: -10px; margin-bottom: 15px; font-size: 0.85rem;'>
            <a href='https://www.oceans14.com.br/acoes/agenda-resultados' target='_blank' style='color: #8b949e; text-decoration: none;'>
                📅 Consultar Agenda de Resultados
            </a>
        </div>
        """, unsafe_allow_html=True
    )

    if ticker_input:
        df_si = get_statusinvest_db()
        ticker_data = df_si[df_si['ticker'] == ticker_input]
        selic_padrao = get_taxa_selic()

        if ticker_data.empty:
            st.error(f"Ticker '{ticker_input}' não encontrado na base de dados (StatusInvest).")
        else:
            row = ticker_data.iloc[0]
            cotacao_atual = float(row.get('price', 0) or 0)
            market_cap_atual = float(row.get('valormercado', 0) or 0)
            num_acoes = market_cap_atual / cotacao_atual if cotacao_atual > 0 and market_cap_atual > 0 else 0
            
            dy_atual = float(row.get('dy', 0) or 0)
            vpa = float(row.get('vpa', 0) or 0)
            lpa = float(row.get('lpa', 0) or 0)
            pl = float(row.get('p_l', 0) or 0)
            roe = float(row.get('roe', 0) or 0)

            df_hist_ni, payout_medio_hist = get_historical_net_income(ticker_input)
            payout_padrao_proj = payout_medio_hist if payout_medio_hist is not None else 75.59
            
            ultimo_ll_base = float(df_hist_ni['Lucro Líquido'].iloc[-1]) if (df_hist_ni is not None and not df_hist_ni.empty) else (lpa * num_acoes)

            # TOP STRIP - BANNER SUPERIOR DE KPIS
            k1, k2, k3, k4, k5 = st.columns(5)
            with k1: render_kpi("PREÇO ATUAL", format_brl(cotacao_atual))
            with k2: render_kpi("Nº TOTAL DE AÇÕES", f"{int(num_acoes):,}".replace(",", "."))
            with k3: render_kpi("MARKET CAP", formatar_grandeza(market_cap_atual))
            with k4: render_kpi("PAYOUT MÉDIO", format_perc(payout_padrao_proj))
            with k5: render_kpi("ROE", format_perc(roe))

            st.markdown("<br>", unsafe_allow_html=True)

            # GRID PRINCIPAL (COLUNA ESQUERDA: PREMISSAS | COLUNA DIREITA: DCF)
            col_left, col_right = st.columns([4, 8])

            with col_left:
                st.markdown('<div class="panel-box">', unsafe_allow_html=True)
                st.markdown('<div class="panel-header">Premissas</div>', unsafe_allow_html=True)
                
                # Inputs de Premissas com Reatividade Instantânea
                payout_proj = st.number_input("Payout médio (%)", value=round(payout_padrao_proj, 2), step=1.0, key=f"payout_{ticker_input}")
                roe_proj = st.number_input("ROE (%)", value=round(roe, 2), step=0.5, key=f"roe_{ticker_input}")
                
                # Crescimento Retido Calculado g = ROE * (1 - Payout)
                # Recalcula g sempre que ROE ou Payout mudarem; preserva edição manual nos demais casos
                cresc_key      = f"cresc_{ticker_input}"
                prev_roe_key   = f"_prev_roe_{ticker_input}"
                prev_payout_key = f"_prev_payout_{ticker_input}"

                g_calc = round(roe_proj * (1 - (payout_proj / 100)), 2)

                roe_changed    = st.session_state.get(prev_roe_key)   != roe_proj
                payout_changed = st.session_state.get(prev_payout_key) != payout_proj

                if cresc_key not in st.session_state or roe_changed or payout_changed:
                    st.session_state[cresc_key]      = float(g_calc)
                    st.session_state[prev_roe_key]   = roe_proj
                    st.session_state[prev_payout_key] = payout_proj

                cresc_proj = st.number_input("Taxa Esperada de Crescimento (%)", step=0.5, key=cresc_key)
                
                taxa_desc_proj = st.number_input("Taxa de Desconto (%)", value=14.0, step=0.5, key=f"desc_{ticker_input}")
                
                st.caption(f"ℹ️ Média histórica da Selic é {selic_padrao:.2f}%")
                st.markdown('</div>', unsafe_allow_html=True)

                # EXPANDER COM VALUATIONS CLASSICOS (MANTIDOS NA MESMA ABA)
                with st.expander("🏛️ Valuations Tradicionais (Bazin, Graham, Lynch)", expanded=False):
                    v_tabs = st.tabs(["Bazin", "Graham", "Peter Lynch"])
                    
                    with v_tabs[0]:
                        dpa_atual = cotacao_atual * (dy_atual / 100)
                        dy_bazin = st.number_input("DY Desejado (%)", value=6.0, step=0.5, key=f"baz_{ticker_input}")
                        teto_bazin = dpa_atual / (dy_bazin / 100) if dy_bazin > 0 else 0
                        margem_bazin = ((teto_bazin - cotacao_atual) / cotacao_atual) * 100 if cotacao_atual > 0 else 0
                        
                        render_metric_row("DPA (12m)", format_brl(dpa_atual))
                        render_metric_row("Preço Teto Bazin", format_brl(teto_bazin), "metric-val-green")
                        render_metric_row("Margem", format_perc(margem_bazin), get_color_class(margem_bazin))

                    with v_tabs[1]:
                        if vpa > 0 and lpa > 0:
                            vi_graham = math.sqrt(22.5 * lpa * vpa)
                            margem_graham = ((vi_graham - cotacao_atual) / cotacao_atual) * 100
                            render_metric_row("Preço Teto Graham", format_brl(vi_graham), "metric-val-green")
                            render_metric_row("Margem", format_perc(margem_graham), get_color_class(margem_graham))
                        else:
                            st.warning("VPA ou LPA negativos impedem o cálculo de Graham.")

                    with v_tabs[2]:
                        if pl > 0:
                            ind_lynch = (dy_atual + cresc_proj) / pl
                            render_metric_row("Indicador Lynch", f"{ind_lynch:.2f}")
                            status_lynch = "Muito Barata" if ind_lynch > 2.0 else ("Barata" if ind_lynch >= 1.5 else "Cara")
                            render_metric_row("Classificação", status_lynch, "metric-val-green" if ind_lynch >= 1.5 else "metric-val-red")
                        else:
                            st.warning("P/L negativo impede o cálculo.")

            # COLUNA DIREITA: FLUXO DE CAIXA DESCONTADO (DCF) E PERPETUIDADE EDITÁVEL
            with col_right:
                st.markdown('<div class="panel-box">', unsafe_allow_html=True)
                
                head_col, horiz_col = st.columns([6, 4])
                with head_col:
                    st.markdown('<div class="panel-header" style="margin:0;">Fluxo de Caixa Descontado</div>', unsafe_allow_html=True)
                with horiz_col:
                    horizonte = st.radio("Horizonte", options=["3 anos", "5 anos"], horizontal=True, label_visibility="collapsed")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Inputs de Lucro Base e Perpetuidade
                c_ll_base, c_perp = st.columns(2)
                with c_ll_base:
                    lucro_atual_input = st.number_input(
                        "Lucro Líquido Base (R$)", 
                        value=round(ultimo_ll_base, 0), 
                        step=10_000_000.0, 
                        format="%.0f",
                        key=f"ll_base_{ticker_input}"
                    )
                    st.caption(f"**Interpretação:** {formatar_grandeza(lucro_atual_input)}")
                with c_perp:
                    taxa_perp_input = st.number_input(
                        "Taxa de Perpetuidade (%)", 
                        value=3.0, 
                        step=0.1, 
                        key=f"perp_{ticker_input}"
                    )
                
                st.markdown("<br>", unsafe_allow_html=True)

                # Cálculo Dinâmico da Tabela do DCF
                n_anos = 3 if horizonte == "3 anos" else 5
                ano_atual = datetime.now().year
                
                rows = []
                
                # Anos Históricos — calcula crescimento real ano a ano
                if df_hist_ni is not None and not df_hist_ni.empty:
                    ll_vals = df_hist_ni['Lucro Líquido'].tolist()
                    for idx, h_row in df_hist_ni.iterrows():
                        if idx == 0 or ll_vals[idx - 1] == 0:
                            cresc_hist = "-"
                        else:
                            cresc_pct = ((ll_vals[idx] - ll_vals[idx - 1]) / abs(ll_vals[idx - 1])) * 100
                            cresc_hist = f"{cresc_pct:+.2f}%"
                        rows.append({
                            "ANO": str(int(h_row['Ano'])),
                            "LUCRO LÍQUIDO": float(h_row['Lucro Líquido']),
                            "CRESCIMENTO": cresc_hist,
                            "VPL": "-"
                        })
                
                # Anos Projetados
                curr_ll = lucro_atual_input
                taxa_desc_dec = taxa_desc_proj / 100.0
                cresc_dec = cresc_proj / 100.0
                taxa_perp_dec = taxa_perp_input / 100.0
                
                vpls_projetados = []
                for i in range(1, n_anos + 1):
                    ano_p = ano_atual + i - 1
                    curr_ll = curr_ll * (1 + cresc_dec)
                    vpl = curr_ll / ((1 + taxa_desc_dec) ** i)
                    vpls_projetados.append(vpl)
                    
                    rows.append({
                        "ANO": str(ano_p),
                        "LUCRO LÍQUIDO": curr_ll,
                        "CRESCIMENTO": format_perc(cresc_proj),
                        "VPL": format_brl(vpl)
                    })

                # Perpetuidade
                if taxa_desc_dec > taxa_perp_dec:
                    tv = (curr_ll * (1 + taxa_perp_dec)) / (taxa_desc_dec - taxa_perp_dec)
                    vpl_perp = tv / ((1 + taxa_desc_dec) ** n_anos)
                else:
                    tv, vpl_perp = 0.0, 0.0

                # Dataframe para exibição com cores na coluna CRESCIMENTO
                df_dcf = pd.DataFrame(rows)
                df_dcf['LUCRO LÍQUIDO'] = df_dcf['LUCRO LÍQUIDO'].apply(format_brl)

                n_hist = len(df_hist_ni) if df_hist_ni is not None and not df_hist_ni.empty else 0

                def style_dcf(df):
                    styles = pd.DataFrame("", index=df.index, columns=df.columns)
                    for i, val in enumerate(df['CRESCIMENTO']):
                        if val == "-":
                            pass  # sem cor
                        elif i < n_hist:
                            # Anos históricos: verde se positivo, vermelho se negativo
                            try:
                                num = float(str(val).replace("+", "").replace("%", ""))
                                cor = "#3fb950" if num >= 0 else "#f85149"
                            except ValueError:
                                cor = "#8b949e"
                            styles.loc[i, 'CRESCIMENTO'] = f"color: {cor}; font-weight: 700"
                        else:
                            # Anos projetados: ciano (mesmo padrão do benchmark)
                            styles.loc[i, 'CRESCIMENTO'] = "color: #38bdf8; font-weight: 600"
                    return styles

                styled_dcf = df_dcf.style.apply(style_dcf, axis=None)
                st.dataframe(styled_dcf, use_container_width=True, hide_index=True)

                # Linha do Perpétuo
                st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                p_c1, p_c2, p_c3, p_c4 = st.columns([2, 4, 3, 3])
                with p_c1: st.markdown("**Perpétuo**")
                with p_c2: st.markdown(f"**{format_brl(tv)}**")
                with p_c3: st.markdown(f"**{taxa_perp_input:.1f}%**")
                with p_c4: st.markdown(f"<span class='metric-val-blue'>{format_brl(vpl_perp)}</span>", unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

                # Atualizando resultados projetados finais
                mkt_cap_dcf = sum(vpls_projetados) + vpl_perp
                preco_justo_dcf = mkt_cap_dcf / num_acoes if num_acoes > 0 else 0
                upside_dcf = ((preco_justo_dcf - cotacao_atual) / cotacao_atual) * 100 if cotacao_atual > 0 else 0

            # Atualização do card de Realidade Projetada na coluna da esquerda
            with col_left:
                st.markdown('<div class="panel-box">', unsafe_allow_html=True)
                st.markdown('<div class="panel-header">Realidade Projetada</div>', unsafe_allow_html=True)
                
                render_metric_row("Market cap", formatar_grandeza(mkt_cap_dcf))
                render_metric_row("Nº total de ações", f"{int(num_acoes):,}".replace(",", "."))
                render_metric_row("Nº ações ex-tesouraria", f"{int(num_acoes):,}".replace(",", "."))
                render_metric_row("Preço por ação", format_brl(preco_justo_dcf), "metric-val-blue")
                render_metric_row("Upside / Downside", format_perc(upside_dcf), get_color_class(upside_dcf))

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Salvar Preço Teto", use_container_width=True):
                    cenario = {
                        "Ativo": ticker_input,
                        "Preço Teto": preco_justo_dcf,
                        "Margem (%)": upside_dcf,
                        "Yield Proj (%)": ( ( (lucro_atual_input * (payout_proj/100)) / num_acoes ) / cotacao_atual ) * 100 if cotacao_atual > 0 else 0,
                        "Lucro Proj": lucro_atual_input,
                        "Payout": payout_proj,
                        "Cotação": cotacao_atual
                    }
                    st.session_state.cenarios_salvos.append(cenario)
                    save_cenarios(st.session_state.cenarios_salvos)
                    st.toast("Cenário salvo com sucesso!")
                    st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

            # HISTÓRICO DE CENÁRIOS SALVOS (PONTO 2 CORRIGIDO)
            st.markdown("<br>", unsafe_allow_html=True)
            if len(st.session_state.cenarios_salvos) > 0:
                with st.container(border=True):
                    st.markdown('<h4>📋 Histórico de Cenários Salvos</h4>', unsafe_allow_html=True)
                    df_cenarios = pd.DataFrame(st.session_state.cenarios_salvos)
                    
                    df_view = df_cenarios.copy()
                    
                    # Guarda os valores numéricos de Margem antes de formatar
                    margem_nums = df_cenarios['Margem (%)'].tolist()

                    # Formatação visual para a tabela
                    df_view['Preço Teto'] = df_view['Preço Teto'].apply(format_brl)
                    df_view['Lucro Proj'] = df_view['Lucro Proj'].apply(formatar_grandeza)
                    df_view['Cotação'] = df_view['Cotação'].apply(format_brl)
                    df_view['Margem (%)'] = df_view['Margem (%)'].apply(format_perc)
                    df_view['Yield Proj (%)'] = df_view['Yield Proj (%)'].apply(format_perc)
                    df_view['Payout'] = df_view['Payout'].apply(format_perc)

                    # Aplica cor na coluna Margem via Styler
                    def color_margem(row_idx):
                        val = margem_nums[row_idx]
                        return "#3fb950" if val >= 0 else "#f85149"

                    def style_margem(df):
                        styles = pd.DataFrame("", index=df.index, columns=df.columns)
                        for i in range(len(df)):
                            cor = color_margem(i)
                            styles.loc[i, 'Margem (%)'] = f"color: {cor}; font-weight: 700"
                        return styles

                    styled = df_view.style.apply(style_margem, axis=None)
                    st.dataframe(styled, hide_index=True, use_container_width=True)
                    
                    c_b1, c_b2, _ = st.columns([3, 3, 4])
                    with c_b1:
                        if st.button("🗑️ Limpar Histórico", use_container_width=True):
                            st.session_state.cenarios_salvos = []
                            save_cenarios([])
                            st.rerun()
                    with c_b2:
                        csv_export = df_cenarios.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig")
                        st.download_button(
                            label="📥 Exportar CSV",
                            data=csv_export,
                            file_name="cenarios_salvos.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

# =============================================================================
# ABA 2: RANKING DE OPORTUNIDADES (RESTAURADO COMPLETO)
# =============================================================================
with tab_ranking:
    st.markdown("### 🎯 Ranking de Oportunidades (Screening Automático)")
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

    col_btn_rank, _ = st.columns([3, 7])
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
        st.dataframe(df_ranking, hide_index=True, use_container_width=True, height=450)
    else:
        st.info("Nenhum ranking gerado ainda. Clique no botão acima para iniciar.")

# =============================================================================
# ABA 3: CARTEIRA DE PROVENTOS (RESTAURADO COMPLETO)
# =============================================================================
with tab_carteira:
    st.markdown("### 💼 Minha Carteira de Proventos")
    
    if 'carteira_posicao' not in st.session_state:
        st.session_state.carteira_posicao = pd.DataFrame(columns=['Ticker', 'Tipo', 'Quantidade', 'Preço Médio'])
    if 'carteira_proventos' not in st.session_state:
        st.session_state.carteira_proventos = pd.DataFrame(columns=['Mês/Ano', 'Tipo', 'Valor'])

    with st.expander("📝 Inserir Dados da Carteira", expanded=True):
        st.markdown("Preencha as tabelas abaixo ou faça o upload dos CSVs de template.")
        c_up1, c_up2 = st.columns(2)
        with c_up1:
            upload_pos = st.file_uploader("Upload Posição (CSV)", type=["csv"], key="up_pos")
            if upload_pos is not None:
                try:
                    df_up_pos = pd.read_csv(upload_pos, sep=';', decimal=',')
                    colunas_esperadas = ['Ticker', 'Tipo', 'Quantidade', 'Preço Médio']
                    if all(c in df_up_pos.columns for c in colunas_esperadas):
                        st.session_state.carteira_posicao = df_up_pos[colunas_esperadas]
                    else:
                        st.error("Colunas inválidas no CSV de Posição.")
                except Exception as e:
                    st.error(f"Erro ao ler arquivo: {e}")
        with c_up2:
            upload_prov = st.file_uploader("Upload Proventos (CSV)", type=["csv"], key="up_prov")
            if upload_prov is not None:
                try:
                    df_up_prov = pd.read_csv(upload_prov, sep=';', decimal=',')
                    colunas_esperadas = ['Mês/Ano', 'Tipo', 'Valor']
                    if all(c in df_up_prov.columns for c in colunas_esperadas):
                        st.session_state.carteira_proventos = df_up_prov[colunas_esperadas]
                    else:
                        st.error("Colunas inválidas no CSV de Proventos.")
                except Exception as e:
                    st.error(f"Erro ao ler arquivo: {e}")
        
        c_pos, c_prov = st.columns(2)
        
        with c_pos:
            st.markdown("#### Posição Atual")
            df_pos_edited = st.data_editor(
                st.session_state.carteira_posicao, 
                num_rows="dynamic", 
                key="editor_pos", 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Ação", "FII"], required=True)
                }
            )
            
        with c_prov:
            st.markdown("#### Histórico de Proventos (Recebidos)")
            df_prov_edited = st.data_editor(
                st.session_state.carteira_proventos, 
                num_rows="dynamic", 
                key="editor_prov", 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Mês/Ano": st.column_config.TextColumn("Mês/Ano (MM/YYYY)"),
                    "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Ação", "FII"], required=True),
                    "Valor": st.column_config.NumberColumn("Valor (R$)")
                }
            )
            
        if st.button("💾 Salvar e Calcular Carteira"):
            st.session_state.carteira_posicao = df_pos_edited.reset_index(drop=True)
            st.session_state.carteira_proventos = df_prov_edited.reset_index(drop=True)
            st.rerun()

    metricas = calcular_metricas_carteira(st.session_state.carteira_posicao)
    df_pivot_prov, total_prov = gerar_tabela_proventos(st.session_state.carteira_proventos)
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        with st.container(border=True):
            render_metric_row("Valor aplicado", format_brl(metricas['valor_aplicado']))
            render_metric_row("Saldo bruto", format_brl(metricas['saldo_bruto']))
            render_metric_row("Ganho de capital", format_brl(metricas['ganho_capital_rs']), get_color_class(metricas['ganho_capital_rs']))
            render_metric_row("Em percentual", format_perc(metricas['ganho_capital_perc']), get_color_class(metricas['ganho_capital_perc']))
            
    with col_m2:
        with st.container(border=True):
            yoc = (total_prov / metricas['valor_aplicado']) * 100 if metricas['valor_aplicado'] > 0 else 0
            render_metric_row("YoC consolidado", format_perc(yoc))
            render_metric_row("Total de Proventos", format_brl(total_prov))
            render_metric_row("Aplicado em FII", format_brl(metricas['aplicado_fii']))

    st.markdown("### 📅 Proventos Pagos Por Mês")
    if not df_pivot_prov.empty:
        df_display = df_pivot_prov.copy()
        for col in df_display.columns:
            df_display[col] = df_display[col].apply(format_brl)
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("Adicione proventos para visualizar a tabela mensal.")

    # Gráfico de YoC Mensal
    if not st.session_state.carteira_proventos.empty and metricas['valor_aplicado'] > 0:
        st.markdown("### 📈 Rentabilidade Mensal (YoC)")
        try:
            df_yoc = st.session_state.carteira_proventos.copy()
            df_yoc['Data'] = pd.to_datetime(df_yoc['Mês/Ano'], format='%m/%Y', errors='coerce')
            df_yoc['Valor'] = pd.to_numeric(df_yoc['Valor'], errors='coerce').fillna(0.0)
            df_yoc = df_yoc.dropna(subset=['Data'])

            df_mensal = df_yoc.groupby(df_yoc['Data'].dt.to_period('M'))['Valor'].sum().reset_index()
            df_mensal.columns = ['Período', 'Proventos']
            df_mensal['Período'] = df_mensal['Período'].astype(str)
            df_mensal['YoC (%)'] = (df_mensal['Proventos'] / metricas['valor_aplicado']) * 100

            chart = alt.Chart(df_mensal).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                x=alt.X('Período:O', axis=alt.Axis(labelAngle=-45, title=None)),
                y=alt.Y('YoC (%):Q', axis=alt.Axis(title='Rentabilidade mensal (%)')),
                color=alt.value('#3fb950')
            ).properties(height=260)
            st.altair_chart(chart, use_container_width=True)
        except Exception as e:
            st.warning(f"Erro ao gerar gráfico: {e}")