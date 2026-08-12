import sys

with open('dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the datetime bug
content = content.replace('import datetime\n            hoje = datetime.date.today()', 'hoje = datetime.now()')

# Update the column name from Data (DD/MM/YYYY) to Mês/Ano (MM/YYYY)
content = content.replace('"Data": st.column_config.TextColumn("Data (DD/MM/YYYY)")', '"Mês/Ano": st.column_config.TextColumn("Mês/Ano (MM/YYYY)")')

# Also change the default dataframe initialization
content = content.replace("pd.DataFrame(columns=['Data', 'Ticker', 'Valor'])", "pd.DataFrame(columns=['Mês/Ano', 'Ticker', 'Valor'])")

# Update the parse code for prov_mensal
old_prov_mensal = '''
            if not st.session_state.carteira_proventos.empty:
                try:
                    df_p = st.session_state.carteira_proventos.copy()
                    df_p['Data'] = pd.to_datetime(df_p['Data'], format='%d/%m/%Y', errors='coerce')
                    df_p['Valor'] = pd.to_numeric(df_p['Valor'], errors='coerce').fillna(0)
                    df_p = df_p.dropna(subset=['Data'])
                    prov_mensal = df_p[(df_p['Data'].dt.month == hoje.month) & (df_p['Data'].dt.year == hoje.year)]['Valor'].sum()
                except:
                    pass
'''

new_prov_mensal = '''
            if not st.session_state.carteira_proventos.empty:
                try:
                    df_p = st.session_state.carteira_proventos.copy()
                    df_p['Data'] = pd.to_datetime(df_p['Mês/Ano'], format='%m/%Y', errors='coerce')
                    df_p['Valor'] = pd.to_numeric(df_p['Valor'], errors='coerce').fillna(0)
                    df_p = df_p.dropna(subset=['Data'])
                    prov_mensal = df_p[(df_p['Data'].dt.month == hoje.month) & (df_p['Data'].dt.year == hoje.year)]['Valor'].sum()
                except:
                    pass
'''
content = content.replace(old_prov_mensal, new_prov_mensal)

with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
