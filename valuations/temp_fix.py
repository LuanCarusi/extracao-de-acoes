import sys

with open('dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Change DataFrame initialization
content = content.replace("pd.DataFrame(columns=['Mês/Ano', 'Ticker', 'Valor'])", "pd.DataFrame(columns=['Mês/Ano', 'Tipo', 'Valor'])")

# Update data_editor column config
content = content.replace(
'''                column_config={
                    "Mês/Ano": st.column_config.TextColumn("Mês/Ano (MM/YYYY)"),
                    "Valor": st.column_config.NumberColumn("Valor (R$)")
                }''',
'''                column_config={
                    "Mês/Ano": st.column_config.TextColumn("Mês/Ano (MM/YYYY)"),
                    "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Ação", "FII"], required=True),
                    "Valor": st.column_config.NumberColumn("Valor (R$)")
                }'''
)

# Update the FII dividend calculation
old_fii_calc = '''            fiis_tickers = st.session_state.carteira_posicao[st.session_state.carteira_posicao['Tipo'] == 'FII']['Ticker'].tolist()
            total_prov_fiis = 0.0
            if not st.session_state.carteira_proventos.empty:
                df_temp_prov = st.session_state.carteira_proventos.copy()
                df_temp_prov['Valor'] = pd.to_numeric(df_temp_prov['Valor'], errors='coerce').fillna(0)
                total_prov_fiis = df_temp_prov[df_temp_prov['Ticker'].isin(fiis_tickers)]['Valor'].sum()'''

new_fii_calc = '''            total_prov_fiis = 0.0
            if not st.session_state.carteira_proventos.empty:
                df_temp_prov = st.session_state.carteira_proventos.copy()
                df_temp_prov['Valor'] = pd.to_numeric(df_temp_prov['Valor'], errors='coerce').fillna(0)
                if 'Tipo' in df_temp_prov.columns:
                    total_prov_fiis = df_temp_prov[df_temp_prov['Tipo'] == 'FII']['Valor'].sum()'''

content = content.replace(old_fii_calc, new_fii_calc)

with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
