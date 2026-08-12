import sys

with open('dashboard.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if i == 9: # from utils import ...
        new_lines.append('from utils import fetch_statusinvest_data, get_selic, calcular_metricas_carteira, gerar_tabela_proventos\n')
    elif i == 291: # # 2. BUSCADOR PRINCIPAL
        new_lines.append('tab_val, tab_carteira = st.tabs(["📊 Análise de Ativos", "💼 Carteira de Proventos"])\n\n')
        new_lines.append('with tab_carteira:\n')
        new_lines.append('    # __INSERIR_CARTEIRA_AQUI__\n')
        new_lines.append('    pass\n\n')
        new_lines.append('with tab_val:\n')
        new_lines.append('    ' + line)
    elif i > 291:
        new_lines.append('    ' + line)
    else:
        new_lines.append(line)

with open('dashboard_tmp.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
