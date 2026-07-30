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

        h1, h2, h3, h4 {
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 1rem;
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
            font-size: 0.95rem;
            color: #8b949e;
        }
        
        .metric-value {
            font-size: 1.05rem;
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

        /* Estilização para st.container(border=True) nativo do Streamlit */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 8px;
            border: 1px solid #30363d;
            background-color: #161b22;
            padding: 0.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

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

def formatar_grandeza(valor):
    if pd.isna(valor) or valor is None: 
        return "-"
    
    abs_valor = abs(valor)
    sinal = "-" if valor < 0 else ""
    
    if abs_valor >= 1_000_000_000_000:
        numero = abs_valor / 1_000_000_000_000
        sufixo = "trilhão" if numero >= 1 and numero < 2 else "trilhões"
    elif abs_valor >= 1_000_000_000:
        numero = abs_valor / 1_000_000_000
        sufixo = "bilhão" if numero >= 1 and numero < 2 else "bilhões"
    elif abs_valor >= 1_000_000:
        numero = abs_valor / 1_000_000
        sufixo = "milhão" if numero >= 1 and numero < 2 else "milhões"
    elif abs_valor >= 1_000:
        numero = abs_valor / 1_000
        sufixo = "mil"
    else:
        numero = abs_valor
        sufixo = ""

    # Formata com 2 casas decimais e troca ponto por vírgula
    num_str = f"{numero:.2f}".replace(".", ",")
    
    # Limpa zeros desnecessários (ex: de "13,00 bilhões" para "13 bilhões")
    if num_str.endswith(",00"):
        num_str = num_str[:-3]

    return f"R$ {sinal}{num_str} {sufixo}".strip()

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


# 1. RANKING (SCREENING) - Agora aberto por padrão (expanded=True)
with st.expander("🎯 Ranking de Oportunidades (Screening Automático)", expanded=True):
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
        
        dy_atual = float(row.get('dy', 0) or 0)
        vpa = float(row.get('vpa', 0) or 0)
        lpa = float(row.get('lpa', 0) or 0)
        pl = float(row.get('p_l', 0) or 0)
        roe = float(row.get('roe', 0) or 0)
        
        with st.spinner("Buscando dados históricos de balanço..."):
            df_hist_ni, payout_medio_hist = get_historical_net_income(ticker_input)
            tem_dados_damodaran = df_hist_ni is not None and not df_hist_ni.empty

        # Separa Damodaran em uma aba e o restante em outra
        tab_main, tab_damo = st.tabs(["📊 Dashboard Consolidado", "💸 Valuation Fluxo de Caixa (Damodaran)"])
        
        with tab_main:
            # ---------------------------------------------------------
            # GRID LINHA 1: BAZIN, GRAHAM, PETER LYNCH
            # ---------------------------------------------------------
            col_bazin, col_graham, col_lynch = st.columns(3)
            
            # -- CARD BAZIN --
            with col_bazin:
                with st.container(border=True):
                    st.markdown('<h4>📊 Valuation Bazin</h4>', unsafe_allow_html=True)
                    
                    dpa_atual = cotacao_atual * (dy_atual / 100)
                    render_metric_row("Dividend Yield (12m)", format_perc(dy_atual))
                    render_metric_row("DPA (12m)", format_brl(dpa_atual))
                    
                    # Key dinâmica usando o ticker para resetar quando mudar a ação
                    dy_desejado_bazin = st.number_input("Dividend Yield Desejado (%)", min_value=0.1, value=6.0, step=0.5, key=f"bazin_dy_{ticker_input}")
                    
                    preco_teto_bazin = dpa_atual / (dy_desejado_bazin / 100) if dy_desejado_bazin > 0 else 0
                    margem_bazin = (preco_teto_bazin - cotacao_atual) / cotacao_atual if cotacao_atual > 0 else 0
                    
                    st.markdown("<hr style='border-color: #30363d; margin: 15px 0;'>", unsafe_allow_html=True)
                    render_metric_row("Preço Teto do Bazin", format_brl(preco_teto_bazin), "metric-value-green")
                    render_metric_row("Margem de Segurança", format_perc(margem_bazin * 100), get_color_class(margem_bazin))

            # -- CARD GRAHAM --
            with col_graham:
                with st.container(border=True):
                    st.markdown('<h4>📈 Valuation Graham</h4>', unsafe_allow_html=True)
                    
                    render_metric_row("Lucro por Ação (LPA)", format_brl(lpa))
                    render_metric_row("Valor Patrimonial (VPA)", format_brl(vpa))
                    
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
                
            # -- CARD PETER LYNCH --
            with col_lynch:
                with st.container(border=True):
                    st.markdown('<h4>🚀 Valuation Peter Lynch</h4>', unsafe_allow_html=True)
                    
                    render_metric_row("P/L", f"{pl:.2f}")
                    render_metric_row("ROE", format_perc(roe))
                    
                    # Key dinâmica
                    crescimento_lynch = st.number_input("Crescimento Projetivo (%)", value=3.0, step=0.5, key=f"lynch_cresc_{ticker_input}")
                    
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

            st.markdown("<br>", unsafe_allow_html=True)

            # ---------------------------------------------------------
            # GRID LINHA 2: PREÇO TETO PROJETIVO
            # ---------------------------------------------------------
            col_proj_in, col_proj_out = st.columns([1, 1])
            
            if df_hist_ni is not None and not df_hist_ni.empty:
                ultimo_ll_proj_base = float(df_hist_ni['Lucro Líquido'].iloc[-1])
            else:
                ultimo_ll_proj_base = 0.0
                
            payout_padrao_proj = payout_medio_hist if payout_medio_hist is not None else 50.0

            # -- CARD PREÇO TETO (INPUTS) --
            with col_proj_in:
                with st.container(border=True):
                    st.markdown('<h4>⚙️ Preço Teto Projetivo (Inputs)</h4>', unsafe_allow_html=True)
                    
                    # Keys dinâmicas para resetarem com o ticker
                    dy_proj = st.number_input("Dividend Yield Desejado (%)", value=6.0, step=0.5, key=f"proj_dy_{ticker_input}")
                    payout_proj = st.number_input("Payout da Empresa (%)", value=round(payout_padrao_proj, 2), step=1.0, key=f"proj_payout_{ticker_input}")
                    lucro_proj = st.number_input("Lucro Líquido Projetado (R$)", value=round(ultimo_ll_proj_base, 0), step=10_000_000.0, format="%.0f", key=f"proj_lucro_{ticker_input}")
                    st.caption(f"**Valor interpretado:** {formatar_grandeza(lucro_proj)}")

                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Salvar Cenário Atual"):
                        lpa_p = lucro_proj / num_acoes if num_acoes > 0 else 0
                        dpa_p = lpa_p * (payout_proj / 100)
                        teto_p = dpa_p / (dy_proj / 100) if dy_proj > 0 else 0
                        margem_p = (teto_p - cotacao_atual) / cotacao_atual if cotacao_atual > 0 else 0
                        yield_p = (dpa_p / cotacao_atual) * 100 if cotacao_atual > 0 else 0
                        
                        cenario = {
                            "Ativo": ticker_input,
                            "Preço Teto": teto_p,
                            "Margem (%)": margem_p * 100,
                            "Yield Proj (%)": yield_p,
                            "Lucro Proj": lucro_proj,
                            "Payout": payout_proj,
                            "Cotação": cotacao_atual
                        }
                        st.session_state.cenarios_salvos.append(cenario)
                        st.toast("Cenário salvo!")

            # -- CARD PREÇO TETO (OUTPUTS) --
            with col_proj_out:
                with st.container(border=True):
                    st.markdown('<h4>📊 Resultados Projetivos</h4>', unsafe_allow_html=True)
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

            st.markdown("<br>", unsafe_allow_html=True)
            
            # ---------------------------------------------------------
            # CENÁRIOS SALVOS (Expandido e com melhor visualização)
            # ---------------------------------------------------------
            if len(st.session_state.cenarios_salvos) > 0:
                with st.container(border=True):
                    st.markdown('<h4>📋 Histórico de Cenários Salvos</h4>', unsafe_allow_html=True)
                    df_cenarios = pd.DataFrame(st.session_state.cenarios_salvos)
                    
                    # Formatando para visualização
                    df_view = df_cenarios.copy()
                    cols_moeda = ["Preço Teto", "Lucro Proj", "Cotação"]
                    cols_perc = ["Margem (%)", "Yield Proj (%)", "Payout"]
                    
                    for col in cols_moeda:
                        if col in df_view.columns:
                            df_view[col] = df_view[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    for col in cols_perc:
                        if col in df_view.columns:
                            df_view[col] = df_view[col].apply(lambda x: f"{x:.2f}%")
                            
                    # Função para colorir a célula baseada no valor
                    def colorir_margem(valor):
                        try:
                            # Remove o '%' para transformar de volta em número e checar o sinal
                            val_num = float(valor.replace('%', ''))
                            if val_num > 0:
                                return 'color: #3fb950; font-weight: 600;' # Verde (metric-value-green)
                            elif val_num < 0:
                                return 'color: #f85149; font-weight: 600;' # Vermelho (metric-value-red)
                            return ''
                        except:
                            return ''

                    # Aplica o estilo na coluna específica (usa try/except para garantir compatibilidade com qualquer versão do Pandas)
                    try:
                        df_estilizado = df_view.style.map(colorir_margem, subset=["Margem (%)"])
                    except AttributeError:
                        # Fallback para versões do Pandas anteriores à 2.1.0
                        df_estilizado = df_view.style.applymap(colorir_margem, subset=["Margem (%)"])

                    # Renderiza o dataframe já com as regras de cores aplicadas
                    st.dataframe(df_estilizado, hide_index=True, use_container_width=True)
                    
                    if st.button("🗑️ Limpar Histórico"):
                        st.session_state.cenarios_salvos = []
                        st.rerun()

        # ---------------------------------------------------------
        # ABA DAMODARAN
        # ---------------------------------------------------------
        with tab_damo:
            st.markdown('<h3>💸 Valuation Fluxo de Caixa (Damodaran)</h3>', unsafe_allow_html=True)
            
            if not tem_dados_damodaran:
                st.warning("Sem dados históricos (Yahoo Finance) para projetar o Fluxo de Caixa.")
            else:
                st.markdown("""
                Este modelo projeta o Lucro Líquido descontado a valor presente, estimando o **Preço Justo** (Damodaran).
                """)
                
                ano_atual = datetime.now().year
                anos_projetados = [ano_atual + i for i in range(1, 4)]
                
                col_d1, col_d2 = st.columns([1, 2])
                
                with col_d1:
                    with st.container(border=True):
                        st.markdown("**Parâmetros Globais**")
                        taxa_desc = st.number_input("Taxa de Desconto (%)", value=selic_padrao, step=0.1, key=f"damo_desc_{ticker_input}") / 100
                        taxa_perp = st.number_input("Taxa Perpetuidade (%)", value=2.0, step=0.1, key=f"damo_perp_{ticker_input}") / 100
                        
                        payout_damo = st.number_input("Payout (%)", value=round(payout_padrao_proj, 2), key=f"damo_payout_{ticker_input}")
                        ll_atual = st.number_input("Lucro Ano Atual", value=round(ultimo_ll_proj_base, 0), step=1_000_000.0, key=f"damo_ll_{ticker_input}")
                        st.caption(f"**Valor interpretado:** {format_brl(ll_atual)}")

                        payout_dec = payout_damo / 100
                        g_calc = (1 - payout_dec) * roe
                        st.caption(f"**Taxa Cresc.(g) Calculada:** {g_calc:.2f}% (usado para projetar os CAGRs)")
                        
                with col_d2:
                    with st.container(border=True):
                        st.markdown("**Projeções de CAGR Anuais (%)**")
                        state_key_cagr = f"cagrs_{ticker_input}"
                        if state_key_cagr not in st.session_state:
                            st.session_state[state_key_cagr] = {ano: round(g_calc, 2) for ano in anos_projetados}
                            
                        df_ed = pd.DataFrame({'Ano': anos_projetados, 'CAGR (%)': [st.session_state[state_key_cagr][a] for a in anos_projetados]})
                        df_ed = st.data_editor(df_ed, hide_index=True, use_container_width=True, key=f"damo_editor_{ticker_input}")
                        
                        for _, r in df_ed.iterrows():
                            st.session_state[state_key_cagr][int(r['Ano'])] = float(r['CAGR (%)'])
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                with st.container(border=True):
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
                        st.error("A Taxa de Desconto deve ser maior que a Perpetuidade.")
                    else:
                        tv = ll_proj[-1] * (1 + taxa_perp) / (taxa_desc - taxa_perp)
                        vpl_perp = tv / ((1 + taxa_desc) ** len(anos_projetados))
                        
                        mkt_cap_damo = sum(vpls) + vpl_perp
                        preco_justo_damo = mkt_cap_damo / num_acoes if num_acoes > 0 else 0
                        margem_damo = (preco_justo_damo - cotacao_atual) / cotacao_atual if cotacao_atual > 0 else 0
                        
                        c_r1, c_r2, c_r3 = st.columns(3)
                        
                        with c_r1:
                            render_metric_row("Cotação Atual", format_brl(cotacao_atual))
                        with c_r2:
                            render_metric_row("Preço Justo (DCF)", format_brl(preco_justo_damo), "metric-value-green")
                        with c_r3:
                            render_metric_row("Upside / Downside", format_perc(margem_damo * 100), get_color_class(margem_damo))
                            
                    st.markdown("<hr style='border-color: #30363d; margin: 20px 0;'>", unsafe_allow_html=True)
                    st.markdown("#### Tabela Consolidada (Histórico + Projeções)")
                    
                    # -- Histórico: calcula CAGR YoY entre os anos reais --
                    hist_anos  = df_hist_ni['Ano'].tolist()
                    hist_lls   = df_hist_ni['Lucro Líquido'].tolist()
                    hist_cagrs = []
                    for i, v in enumerate(hist_lls):
                        if i == 0:
                            hist_cagrs.append(None)
                        else:
                            prev = hist_lls[i - 1]
                            hist_cagrs.append(((v / prev) - 1) * 100 if prev > 0 else None)

                    rows_hist = []
                    for i in range(len(hist_anos)):
                        rows_hist.append({
                            'Ano':           str(hist_anos[i]),
                            'Tipo':          'Histórico',
                            'Lucro Líquido': hist_lls[i],
                            'CAGR (%)':      hist_cagrs[i],
                            'VPL':           None
                        })

                    # -- Ano Atual (input): CAGR vs último histórico --
                    cagr_atual = ((ll_atual / ultimo_ll_proj_base) - 1) * 100 if ultimo_ll_proj_base > 0 else None
                    rows_atual = [{
                        'Ano':           str(ano_atual),
                        'Tipo':          'Atual (Input)',
                        'Lucro Líquido': ll_atual,
                        'CAGR (%)':      cagr_atual,
                        'VPL':           None
                    }]

                    # -- Anos Projetados --
                    rows_proj = []
                    for idx, ano in enumerate(anos_projetados):
                        rows_proj.append({
                            'Ano':           str(ano),
                            'Tipo':          'Projetado',
                            'Lucro Líquido': ll_proj[idx],
                            'CAGR (%)':      st.session_state[state_key_cagr][ano],
                            'VPL':           vpls[idx]
                        })

                    # -- Perpétuo (última linha) --
                    row_perp = [{
                        'Ano':           'Perpétuo',
                        'Tipo':          'Perpetuidade',
                        'Lucro Líquido': tv,
                        'CAGR (%)':      taxa_perp * 100,
                        'VPL':           vpl_perp
                    }]

                    df_full = pd.DataFrame(rows_hist + rows_atual + rows_proj + row_perp)

                    # Formatação para exibição
                    df_disp = df_full.copy()
                    df_disp['Lucro Líquido'] = df_disp['Lucro Líquido'].apply(format_brl)
                    df_disp['VPL']           = df_disp['VPL'].apply(format_brl)
                    df_disp['CAGR (%)']      = df_disp['CAGR (%)'].apply(format_perc)

                    st.dataframe(
                        df_disp[['Ano', 'Tipo', 'Lucro Líquido', 'CAGR (%)', 'VPL']],
                        hide_index=True,
                        use_container_width=True
                    )
