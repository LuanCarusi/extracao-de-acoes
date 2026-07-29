import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import math
import os
from utils import fetch_statusinvest_data, get_selic
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Dashboard Consolidado de Valuations", layout="wide", initial_sidebar_state="collapsed")

def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700&family=Roboto:wght@300;400;700&display=swap');
        
        html, body, [class*="css"]  { font-family: 'Roboto', sans-serif; }
        h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #00d2ff; }
        
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
        .stDataFrame { border: 1px solid #333; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# ============================================================
# VARIÁVEIS DE SESSÃO E CACHE
# ============================================================

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
    """
    Busca o Lucro Líquido (Net Income) dos últimos 3 anos e calcula
    o Payout médio histórico via Dividendos Pagos / Lucro Líquido.
    """
    try:
        t = yf.Ticker(f"{ticker}.SA")
        inc = t.income_stmt
        cf  = t.cash_flow

        if inc is None or inc.empty or 'Net Income' not in inc.index:
            return None, None

        ni_series = inc.loc['Net Income'].dropna().head(3).iloc[::-1]  # 3 anos, cronológico
        dates  = [pd.to_datetime(d).year for d in ni_series.index]
        values = ni_series.values.tolist()

        df_hist = pd.DataFrame({'Ano': dates, 'Lucro Líquido': values})

        # Payout histórico médio: |Dividendos Pagos| / Lucro Líquido
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
    if pd.isna(indicador) or indicador <= 0:
        return "Fora do Range"
    if indicador > 2.0:
        return "Muito Barata"
    elif 1.5 <= indicador <= 2.0:
        return "Barata"
    elif 1.0 <= indicador < 1.5:
        return "Justo"
    return "Cara"

def format_brl(val):
    if pd.isna(val) or val is None:
        return "-"
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_perc(val):
    if pd.isna(val) or val is None:
        return "-"
    return f"{val:.1f}%"

# ============================================================
# HEADER E PARÂMETROS GERAIS
# ============================================================

st.title("🚀 Consolidação de Valuations")
st.markdown("Compare diferentes metodologias de valuation (Damodaran, Bazin, Graham, Lynch).")

selic_padrao = get_taxa_selic()

st.markdown('<div class="header-box">PARÂMETROS GERAIS</div>', unsafe_allow_html=True)
ticker_input = st.text_input("Ticker da Ação (ex: BBSE3)", value="").strip().upper()

# Resolve dados do ticker (se preenchido)
ticker_ok    = False
row          = None
cotacao_atual = 0.0
market_cap_atual = 0.0
num_acoes    = 0.0
df_hist_ni   = None
payout_medio_hist = None
tem_dados_damodaran = False

if ticker_input:
    df_si = get_statusinvest_db()
    ticker_data = df_si[df_si['ticker'] == ticker_input]

    if ticker_data.empty:
        st.error(f"Ticker '{ticker_input}' não encontrado no StatusInvest.")
    else:
        row = ticker_data.iloc[0]
        cotacao_atual    = float(row.get('price', 0) or 0)
        market_cap_atual = float(row.get('valormercado', 0) or 0)

        if pd.isna(market_cap_atual) or market_cap_atual == 0:
            st.warning("Valor de Mercado não disponível. Não é possível calcular o total de ações.")
        else:
            num_acoes = market_cap_atual / cotacao_atual
            ticker_ok = True

            with st.spinner("Buscando dados históricos no Yahoo Finance..."):
                df_hist_ni, payout_medio_hist = get_historical_net_income(ticker_input)
                tem_dados_damodaran = df_hist_ni is not None and not df_hist_ni.empty

            st.markdown('<div class="header-box">VISÃO GERAL DO ATIVO</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ticker", ticker_input)
            c2.metric("Cotação Atual", format_brl(cotacao_atual))
            c3.metric("Número de Ações", f"{int(num_acoes):,}".replace(",", "."))
            c4.metric("Market Cap", format_brl(market_cap_atual))
            st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# TABS
# ============================================================

tab_screening, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Ranking (Oportunidades)",
    "Lucro Líquido Descontado (Damodaran)",
    "Preço Teto (Décio Bazin)",
    "Valor Intrínseco (Graham)",
    "Fair Value (Peter Lynch)",
    "Preço Teto Projetivo"
])

# ============================================================
# ABA 0: SCREENING
# ============================================================
with tab_screening:
    st.markdown("### Ranking de Oportunidades (Screening Geral)")
    st.markdown("Esta tabela exibe o resultado do processo de extração e filtragem do `main.py`.")

    def rodar_main():
        import subprocess
        import sys
        caminhos_main = [
            ("../analise_de_acoes/main.py", "../analise_de_acoes"),
            ("analise_de_acoes/main.py",    "analise_de_acoes"),
        ]
        for arq, cwd in caminhos_main:
            if os.path.exists(arq):
                try:
                    result = subprocess.run([sys.executable, "main.py"], cwd=cwd, check=True, capture_output=True, text=True)
                    return True, ""
                except subprocess.CalledProcessError as e:
                    return False, f"Erro ao executar main.py (código {e.returncode}):\n{e.stderr}"
                except Exception as e:
                    return False, f"Erro inesperado: {str(e)}"
        return False, "Arquivo main.py não encontrado."

    caminhos_csv = [
        "../analise_de_acoes/ranking_acoes_resultado.csv",
        "../ranking_acoes_resultado.csv",
        "ranking_acoes_resultado.csv",
    ]
    df_ranking = None
    for path in caminhos_csv:
        if os.path.exists(path):
            try:
                df_ranking = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
                break
            except Exception:
                pass

    col_btn1, _ = st.columns([2, 8])
    with col_btn1:
        if st.button("🔄 Atualizar / Gerar Ranking"):
            with st.spinner("Analisando o mercado... Isso pode levar alguns segundos."):
                sucesso, msg_erro = rodar_main()
                if sucesso:
                    st.success("Ranking atualizado!")
                    st.rerun()
                else:
                    st.error(msg_erro)

    if df_ranking is not None and not df_ranking.empty:
        # Filtro de Setor
        if 'Setor' in df_ranking.columns:
            setores = sorted(df_ranking['Setor'].dropna().unique().tolist())
            filtro_setor = st.multiselect(
                "Filtrar por Setor (Opcional):",
                options=setores,
                default=[]
            )
            if filtro_setor:
                df_ranking = df_ranking[df_ranking['Setor'].isin(filtro_setor)]
                
        st.success(f"Ranking carregado! ({len(df_ranking)} empresas encontradas)")
        st.dataframe(df_ranking, hide_index=True, use_container_width=True)
        st.info("💡 **Dica:** Copie o Ticker acima e cole no campo de busca para calcular o Valuation.")
    else:
        st.warning("⚠️ Arquivo de ranking não encontrado.")
        st.info("Clique em **Atualizar / Gerar Ranking** para extrair os dados agora.")

# ============================================================
# ABA 1: DAMODARAN (LUCRO LÍQUIDO DESCONTADO)
# ============================================================
with tab1:
    if not ticker_ok:
        st.info("👆 Digite o Ticker da ação no campo acima para carregar a análise.")
    elif not tem_dados_damodaran:
        st.error(f"Não foi possível obter dados históricos de Lucro Líquido no Yahoo Finance para '{ticker_input}'.")
    else:
        st.markdown("### Modelo de Damodaran — Lucro Líquido Descontado")

        ano_atual       = datetime.now().year
        anos_projetados = [ano_atual + i for i in range(1, 4)]  # 3 anos futuros

        # ROE do StatusInvest
        roe_si = float(row.get('roe', 0) or 0)

        # --- Parâmetros de Desconto (exclusivos do Damodaran) ---
        col_damo_p1, col_damo_p2 = st.columns(2)
        with col_damo_p1:
            taxa_desconto = st.number_input(
                "Taxa de Desconto (%)",
                value=selic_padrao,
                step=0.1,
                help="Taxa utilizada para descontar os Lucros futuros a Valor Presente. Sugestão: Selic atual."
            ) / 100
        with col_damo_p2:
            taxa_perpetuidade = st.number_input(
                "Taxa de Perpetuidade (%)",
                value=2.0,
                step=0.1,
                help="Taxa de crescimento perpétuo da empresa após o período de projeção."
            ) / 100

        st.markdown("---")

        # --- Painel de Indicadores Base ---
        st.markdown("#### Indicadores Base")
        st.markdown(
            "Ajuste o **Payout** e o **Lucro Líquido do ano atual** conforme sua expectativa. "
            "A **Taxa de Crescimento (g)** é calculada automaticamente, mas você pode editar "
            "o CAGR de cada ano projetado individualmente na tabela abaixo."
        )

        col_ind1, col_ind2, col_ind3, col_ind4 = st.columns(4)

        # Lucro Líquido do ano atual (input)
        ultimo_ll_hist = float(df_hist_ni['Lucro Líquido'].iloc[-1])
        with col_ind1:
            ll_atual = st.number_input(
                f"Lucro Líquido {ano_atual} (R$)",
                value=round(ultimo_ll_hist, 0),
                step=1_000_000.0,
                format="%.0f",
                help="Insira o Lucro Líquido esperado para o ano atual."
            )

        # Payout médio histórico (editável)
        payout_default = payout_medio_hist if payout_medio_hist is not None else 50.0
        with col_ind2:
            payout_input = st.number_input(
                "Payout (%)",
                value=round(payout_default, 2),
                step=1.0,
                min_value=0.0,
                help=f"Média histórica calculada: {payout_default:.1f}%. Ajuste manualmente se desejar."
            )

        # ROE (referência, read-only)
        with col_ind3:
            st.metric("ROE (%)", f"{roe_si:.2f}%")

        # Taxa de crescimento g = (1 - Payout) * ROE
        payout_dec  = payout_input / 100
        g_calculado = (1 - payout_dec) * roe_si
        with col_ind4:
            st.metric(
                "Taxa de Crescimento g",
                f"{g_calculado:.2f}%",
                help="Calculada como: (1 − Payout) × ROE"
            )

        st.markdown("---")

        # -------------------------------------------------------
        # Session state: inicializa CAGRs projetados pré-preenchidos
        # com g_calculado sempre que o ticker ou g mudar
        # -------------------------------------------------------
        state_key_cagr   = f"cagrs_damo_{ticker_input}"
        state_key_g_prev = f"g_prev_{ticker_input}"

        g_anterior = st.session_state.get(state_key_g_prev, None)
        if state_key_cagr not in st.session_state or g_anterior != round(g_calculado, 4):
            st.session_state[state_key_cagr]   = {ano: round(g_calculado, 2) for ano in anos_projetados}
            st.session_state[state_key_g_prev] = round(g_calculado, 4)

        # -------------------------------------------------------
        # Layout: Resultado (esq) | Tabela + Editor (dir)
        # -------------------------------------------------------
        col_esq, col_dir = st.columns([1, 2], gap="large")

        with col_dir:
            st.markdown("#### Projeção de Crescimento (CAGR por Ano)")
            st.markdown(
                "Edite o **CAGR (%)** de cada ano projetado. "
                "Valores pré-preenchidos com a Taxa de Crescimento **(1 − Payout) × ROE**."
            )

            # Editor interativo com apenas Ano e CAGR para os projetados
            df_editor_input = pd.DataFrame({
                'Ano':      anos_projetados,
                'CAGR (%)': [st.session_state[state_key_cagr][a] for a in anos_projetados]
            })

            edited_df = st.data_editor(
                df_editor_input,
                column_config={
                    "Ano":      st.column_config.NumberColumn(format="%d", disabled=True),
                    "CAGR (%)": st.column_config.NumberColumn(step=0.1, format="%.2f%%"),
                },
                hide_index=True,
                use_container_width=True,
                key=f"editor_damo_{ticker_input}"
            )

            # Persiste os CAGRs editados
            for _, r_ed in edited_df.iterrows():
                st.session_state[state_key_cagr][int(r_ed['Ano'])] = float(r_ed['CAGR (%)'])

            # -------------------------------------------------------
            # Cálculo: Lucros e VPLs projetados
            # -------------------------------------------------------
            ll_projetado  = []
            vpl_projetado = []
            current_ll    = ll_atual
            for idx, ano in enumerate(anos_projetados):
                cagr_ano   = st.session_state[state_key_cagr][ano] / 100
                current_ll = current_ll * (1 + cagr_ano)
                ll_projetado.append(current_ll)
                n   = idx + 1
                vpl = current_ll / ((1 + taxa_desconto) ** n)
                vpl_projetado.append(vpl)

            # Perpetuidade (sobre o último LL projetado)
            ultimo_ll_proj = ll_projetado[-1]
            last_n         = len(anos_projetados)

            if taxa_desconto <= taxa_perpetuidade:
                tv = 0.0
                st.error("⚠️ A Taxa de Desconto deve ser maior que a Taxa de Perpetuidade.")
            else:
                tv = ultimo_ll_proj * (1 + taxa_perpetuidade) / (taxa_desconto - taxa_perpetuidade)

            vpl_perpetuo = tv / ((1 + taxa_desconto) ** last_n)

            # -------------------------------------------------------
            # Tabela Consolidada: Histórico + Atual + Projetado + Perpétuo
            # -------------------------------------------------------
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
            cagr_atual = ((ll_atual / ultimo_ll_hist) - 1) * 100 if ultimo_ll_hist > 0 else None
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
                    'Lucro Líquido': ll_projetado[idx],
                    'CAGR (%)':      st.session_state[state_key_cagr][ano],
                    'VPL':           vpl_projetado[idx]
                })

            # -- Perpétuo (última linha) --
            row_perp = [{
                'Ano':           'Perpétuo',
                'Tipo':          'Perpetuidade',
                'Lucro Líquido': tv,
                'CAGR (%)':      taxa_perpetuidade * 100,
                'VPL':           vpl_perpetuo
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

        with col_esq:
            st.markdown("#### Resultado")

            market_cap_proj = sum(vpl_projetado) + vpl_perpetuo
            preco_justo     = market_cap_proj / num_acoes if num_acoes > 0 else 0
            margem          = (preco_justo - cotacao_atual) / cotacao_atual if cotacao_atual > 0 else 0

            st.metric("Preço Justo (Damodaran)", format_brl(preco_justo))
            st.metric("Market Cap Projetado",    format_brl(market_cap_proj))

            color = "#00ff88" if margem > 0 else "#ff3366"
            st.markdown(f"""
            <div style="background-color:#1e1e2f; border-left:4px solid {color};
                        padding:10px 15px; border-radius:4px; box-shadow:0 4px 6px rgba(0,0,0,0.3);">
                <p style="margin:0; font-size:14px; color:#aaa;">Upside / Downside</p>
                <h2 style="margin:0; color:{color}; font-family:'Orbitron',sans-serif;">{margem*100:.1f}%</h2>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Premissas utilizadas:**")
            st.markdown(f"- Payout médio histórico: **{payout_default:.1f}%**")
            st.markdown(f"- Payout utilizado: **{payout_input:.1f}%**")
            st.markdown(f"- ROE: **{roe_si:.2f}%**")
            st.markdown(f"- g calculado: **{g_calculado:.2f}%**")
            st.markdown(f"- Taxa de Desconto: **{taxa_desconto*100:.1f}%**")
            st.markdown(f"- Taxa de Perpetuidade: **{taxa_perpetuidade*100:.1f}%**")

# ============================================================
# ABA 2: BAZIN
# ============================================================
with tab2:
    if not ticker_ok:
        st.info("👆 Digite o Ticker da ação no campo acima para carregar a análise.")
    else:
        st.markdown("### Preço Teto de Décio Bazin")
        dy_atual = float(row.get('dy', 0) or 0)

        if dy_atual == 0:
            st.warning("Empresa não pagou dividendos ou dado indisponível.")
        else:
            dpa              = cotacao_atual * (dy_atual / 100)
            preco_teto_bazin = dpa / 0.06
            margem_bazin     = (preco_teto_bazin - cotacao_atual) / cotacao_atual

            c1, c2, c3 = st.columns(3)
            c1.metric("Dividend Yield Atual", f"{dy_atual:.2f}%")
            c2.metric("Preço Teto (6% DY)", format_brl(preco_teto_bazin))

            color_bazin = "#00ff88" if margem_bazin > 0 else "#ff3366"
            with c3:
                st.markdown(f"""
                <div style="background-color:#1e1e2f; border-left:4px solid {color_bazin};
                            padding:10px 15px; border-radius:4px; box-shadow:0 4px 6px rgba(0,0,0,0.3);">
                    <p style="margin:0; font-size:14px; color:#aaa;">Margem de Segurança</p>
                    <h2 style="margin:0; color:{color_bazin}; font-family:'Orbitron',sans-serif;">{margem_bazin*100:.1f}%</h2>
                </div>
                """, unsafe_allow_html=True)

            st.info("Bazin exige no mínimo 6% de DY. Preço Teto = DPA (12m) / 0,06.")

# ============================================================
# ABA 3: GRAHAM
# ============================================================
with tab3:
    if not ticker_ok:
        st.info("👆 Digite o Ticker da ação no campo acima para carregar a análise.")
    else:
        st.markdown("### Valor Intrínseco de Benjamin Graham")
        vpa = float(row.get('vpa', 0) or 0)
        lpa = float(row.get('lpa', 0) or 0)

        c1, c2 = st.columns(2)
        c1.metric("VPA", f"R$ {vpa:.2f}")
        c2.metric("LPA", f"R$ {lpa:.2f}")

        if vpa <= 0 or lpa <= 0:
            st.warning("VPA e/ou LPA negativos ou zerados. Fórmula de Graham inaplicável.")
        else:
            vi = math.sqrt(22.5 * lpa * vpa)
            margem_graham = (vi - cotacao_atual) / cotacao_atual

            c3, c4 = st.columns(2)
            c3.metric("Valor Intrínseco (Graham)", format_brl(vi))

            color_g = "#00ff88" if margem_graham > 0 else "#ff3366"
            with c4:
                st.markdown(f"""
                <div style="background-color:#1e1e2f; border-left:4px solid {color_g};
                            padding:10px 15px; border-radius:4px; box-shadow:0 4px 6px rgba(0,0,0,0.3);">
                    <p style="margin:0; font-size:14px; color:#aaa;">Margem de Segurança</p>
                    <h2 style="margin:0; color:{color_g}; font-family:'Orbitron',sans-serif;">{margem_graham*100:.1f}%</h2>
                </div>
                """, unsafe_allow_html=True)

            st.info("Fórmula: √(22,5 × LPA × VPA). Graham sugere margem ≥ 80%.")

# ============================================================
# ABA 4: PETER LYNCH
# ============================================================
with tab4:
    if not ticker_ok:
        st.info("👆 Digite o Ticker da ação no campo acima para carregar a análise.")
    else:
        st.markdown("### Fair Value de Peter Lynch")
        pl  = float(row.get('p_l', 0) or 0)
        roe = float(row.get('roe', 0) or 0)
        dy  = float(row.get('dy',  0) or 0)

        c1, c2, c3 = st.columns(3)
        c1.metric("P/L", f"{pl:.2f}")
        c2.metric("ROE", f"{roe:.2f}%")
        c3.metric("Dividend Yield", f"{dy:.2f}%")

        if roe < selic_padrao:
            st.warning(f"ROE ({roe:.2f}%) abaixo da Selic ({selic_padrao:.2f}%). Custo de oportunidade desfavorável.")

        crescimento_lynch = st.number_input(
            "Crescimento projetado (%)",
            value=3.0,
            step=0.1,
            help="Crescimento anual esperado dos lucros da empresa. Padrão conservador: 3%."
        )

        if pl <= 0:
            st.error("P/L negativo ou zero — empresa com prejuízo. Indicador de Lynch inaplicável.")
        else:
            indicador = (dy + crescimento_lynch) / pl
            classif   = classificar_lynch(indicador)

            c4, c5 = st.columns(2)
            c4.metric("Indicador Lynch", f"{indicador:.2f}")

            color_l = "#00ff88" if classif in ["Barata", "Muito Barata"] else "#ffcc00" if classif == "Justo" else "#ff3366"
            with c5:
                st.markdown(f"""
                <div style="background-color:#1e1e2f; border-left:4px solid {color_l};
                            padding:10px 15px; border-radius:4px; box-shadow:0 4px 6px rgba(0,0,0,0.3);">
                    <p style="margin:0; font-size:14px; color:#aaa;">Classificação</p>
                    <h2 style="margin:0; color:{color_l}; font-family:'Orbitron',sans-serif;">{classif}</h2>
                </div>
                """, unsafe_allow_html=True)

            st.info("Fórmula de Lynch: (Dividend Yield + Crescimento Esperado) / P/L. Quanto maior, mais barata a ação.")

# ============================================================
# ABA 5: PREÇO TETO PROJETIVO
# ============================================================
with tab5:
    if not ticker_ok:
        st.info("👆 Digite o Ticker da ação no campo acima para carregar a análise.")
    else:
        st.markdown("### Preço Teto Projetivo (Foco em Dividendos)")
        st.markdown("Calcule o Preço Teto ideal que você deve pagar com base no **Yield on Cost** futuro esperado.")
        
        col_proj1, col_proj2, col_proj3 = st.columns(3)
        
        # Pega lucro histórico se houver
        if df_hist_ni is not None and not df_hist_ni.empty:
            ultimo_ll_proj_base = float(df_hist_ni['Lucro Líquido'].iloc[-1])
        else:
            ultimo_ll_proj_base = 0.0
            
        payout_padrao_proj = payout_medio_hist if payout_medio_hist is not None else 50.0

        with col_proj1:
            lucro_proj_input = st.number_input(
                "Lucro Líquido Projetivo (R$)",
                value=round(ultimo_ll_proj_base, 0),
                step=1_000_000.0,
                format="%.0f",
                help="Lucro Líquido total que você estima que a empresa gerará no futuro."
            )
            
        with col_proj2:
            payout_proj_input = st.number_input(
                "Payout Projetivo (%)",
                value=round(payout_padrao_proj, 2),
                step=1.0,
                min_value=0.0,
                help="A porcentagem desse lucro que será distribuída em dividendos."
            )
            
        with col_proj3:
            yield_min_input = st.number_input(
                "Yield Mínimo Desejado (%)",
                value=6.0,
                step=0.5,
                help="Seu custo de oportunidade (ex: Método Bazin recomenda no mínimo 6%)."
            )
            
        st.markdown("---")
        
        if num_acoes <= 0:
            st.error("Número de ações não pôde ser calculado. Verifique os dados no StatusInvest.")
        else:
            lpa_proj = lucro_proj_input / num_acoes
            dpa_proj = lpa_proj * (payout_proj_input / 100)
            
            preco_teto_proj = dpa_proj / (yield_min_input / 100) if yield_min_input > 0 else 0
            
            yield_proj_cotacao = (dpa_proj / cotacao_atual) * 100 if cotacao_atual > 0 else 0
            margem_teto_proj = (preco_teto_proj - cotacao_atual) / cotacao_atual if cotacao_atual > 0 else 0
            
            c_res1, c_res2, c_res3 = st.columns(3)
            c_res1.metric("Preço Teto Projetivo", format_brl(preco_teto_proj))
            
            color_margem = "#00ff88" if margem_teto_proj > 0 else "#ff3366"
            with c_res2:
                st.markdown(f"""
                <div style="background-color:#1e1e2f; border-left:4px solid {color_margem};
                            padding:10px 15px; border-radius:4px; box-shadow:0 4px 6px rgba(0,0,0,0.3);">
                    <p style="margin:0; font-size:14px; color:#aaa;">Margem de Segurança</p>
                    <h2 style="margin:0; color:{color_margem}; font-family:'Orbitron',sans-serif;">{margem_teto_proj*100:.1f}%</h2>
                </div>
                """, unsafe_allow_html=True)
                
            color_yield = "#00ff88" if yield_proj_cotacao >= yield_min_input else "#ffcc00" if yield_proj_cotacao >= (yield_min_input * 0.8) else "#ff3366"
            with c_res3:
                st.markdown(f"""
                <div style="background-color:#1e1e2f; border-left:4px solid {color_yield};
                            padding:10px 15px; border-radius:4px; box-shadow:0 4px 6px rgba(0,0,0,0.3);">
                    <p style="margin:0; font-size:14px; color:#aaa;">Yield Projetivo (na Cotação Atual)</p>
                    <h2 style="margin:0; color:{color_yield}; font-family:'Orbitron',sans-serif;">{yield_proj_cotacao:.2f}%</h2>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- Salvamento de Cenários ---
            col_save1, col_save2 = st.columns([2, 8])
            with col_save1:
                if st.button("💾 Salvar Cenário", use_container_width=True):
                    novo_cenario = {
                        "Ticker": ticker_input,
                        "Cotação (R$)": cotacao_atual,
                        "Lucro Proj. (R$)": lucro_proj_input,
                        "LPA Proj. (R$)": lpa_proj,
                        "Payout (%)": payout_proj_input,
                        "Yield Desejado (%)": yield_min_input,
                        "Preço Teto (R$)": preco_teto_proj,
                        "Margem (%)": margem_teto_proj * 100,
                        "Yield Proj. (%)": yield_proj_cotacao
                    }
                    st.session_state.cenarios_salvos.append(novo_cenario)
                    st.success("Cenário salvo!")
                    
            if st.session_state.cenarios_salvos:
                st.markdown("#### 📋 Histórico de Simulações")
                df_cenarios = pd.DataFrame(st.session_state.cenarios_salvos)
                
                # Formatando para visualização
                df_view = df_cenarios.copy()
                cols_moeda = ["Cotação (R$)", "Lucro Proj. (R$)", "LPA Proj. (R$)", "Preço Teto (R$)"]
                cols_perc = ["Payout (%)", "Yield Desejado (%)", "Margem (%)", "Yield Proj. (%)"]
                
                for col in cols_moeda:
                    df_view[col] = df_view[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                for col in cols_perc:
                    df_view[col] = df_view[col].apply(lambda x: f"{x:.2f}%")
                    
                st.dataframe(df_view, hide_index=True, use_container_width=True)
                
                col_down1, col_down2 = st.columns(2)
                with col_down1:
                    csv = df_cenarios.to_csv(index=False, sep=";", decimal=",").encode('utf-8-sig')
                    st.download_button(
                        label="📥 Exportar Histórico (CSV)",
                        data=csv,
                        file_name="cenarios_preco_teto.csv",
                        mime="text/csv",
                    )
                with col_down2:
                    if st.button("🗑️ Limpar Histórico"):
                        st.session_state.cenarios_salvos = []
                        st.rerun()
