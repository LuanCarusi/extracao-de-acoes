import sys

with open('dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

upload_code = """        st.markdown("Preencha as tabelas abaixo ou faça o upload dos CSVs de template.")
        c_up1, c_up2 = st.columns(2)
        with c_up1:
            upload_pos = st.file_uploader("Upload Posição (CSV)", type=["csv"], key="up_pos")
            if upload_pos is not None:
                try:
                    df_up_pos = pd.read_csv(upload_pos, sep=';', decimal=',')
                    # Validar colunas
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
        
        c_pos, c_prov = st.columns(2)"""

# Substituir o placeholder antigo (ou texto atual se já substituí)
target_text = '        st.markdown("Preencha as tabelas abaixo. **Dica:** Insira as datas dos proventos no formato `DD/MM/YYYY`. Em breve adicionaremos upload de planilha via template.")\n        c_pos, c_prov = st.columns(2)'
if target_text not in content:
    # Se o texto já foi alterado para outra coisa na rodada anterior:
    target_text = '        st.markdown("Preencha as tabelas abaixo. **Dica:** Insira as datas dos proventos no formato `DD/MM/YYYY`. Em breve adicionaremos upload de planilha via template.")\n        c_pos, c_prov = st.columns(2)'

# O texto atual não tem "DD/MM/YYYY" porque eu mudei para "Mês/Ano (MM/YYYY)" mas não no markdown! Wait, I didn't change the markdown in the last replace. So it still says DD/MM/YYYY or I can just use a regex/find.
# Let's just find the `c_pos, c_prov = st.columns(2)` line.

import re
content = re.sub(r'        st\.markdown\("Preencha as tabelas abaixo.*"\)\n        c_pos, c_prov = st\.columns\(2\)', upload_code, content)

# Add hide_index=True to data_editors
content = content.replace('use_container_width=True,', 'use_container_width=True,\n                hide_index=True,')

# Reset index when saving
reset_index_code = """        if st.button("💾 Salvar e Calcular Carteira"):
            df_pos_edited = df_pos_edited.reset_index(drop=True)
            df_prov_edited = df_prov_edited.reset_index(drop=True)
            st.session_state.carteira_posicao = df_pos_edited
            st.session_state.carteira_proventos = df_prov_edited
            st.rerun()"""

content = content.replace("""        if st.button("💾 Salvar e Calcular Carteira"):
            st.session_state.carteira_posicao = df_pos_edited
            st.session_state.carteira_proventos = df_prov_edited
            st.rerun()""", reset_index_code)

with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
