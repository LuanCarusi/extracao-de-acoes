import sys

code_to_inject = """
    st.markdown("### 💼 Minha Carteira de Proventos")
    
    if 'carteira_posicao' not in st.session_state:
        st.session_state.carteira_posicao = pd.DataFrame(columns=['Ticker', 'Tipo', 'Quantidade', 'Preço Médio'])
    if 'carteira_proventos' not in st.session_state:
        st.session_state.carteira_proventos = pd.DataFrame(columns=['Data', 'Ticker', 'Valor'])

    with st.expander("📝 Inserir Dados da Carteira", expanded=True):
        st.markdown("Preencha as tabelas abaixo. **Dica:** Insira as datas dos proventos no formato `DD/MM/YYYY`. Em breve adicionaremos upload de planilha via template.")
        c_pos, c_prov = st.columns(2)
        
        with c_pos:
            st.markdown("#### Posição Atual")
            df_pos_edited = st.data_editor(
                st.session_state.carteira_posicao, 
                num_rows="dynamic", 
                key="editor_pos", 
                use_container_width=True,
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
                column_config={
                    "Data": st.column_config.TextColumn("Data (DD/MM/YYYY)"),
                    "Valor": st.column_config.NumberColumn("Valor (R$)")
                }
            )
            
        if st.button("💾 Salvar e Calcular Carteira"):
            st.session_state.carteira_posicao = df_pos_edited
            st.session_state.carteira_proventos = df_prov_edited
            st.rerun()

    metricas = calcular_metricas_carteira(st.session_state.carteira_posicao)
    df_pivot_prov, total_prov = gerar_tabela_proventos(st.session_state.carteira_proventos)
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        with st.container(border=True):
            render_metric_row("Valor aplicado", format_brl(metricas['valor_aplicado']))
            render_metric_row("Saldo bruto", format_brl(metricas['saldo_bruto']))
            render_metric_row("Ganho de capital", format_brl(metricas['ganho_capital_rs']), get_color_class(metricas['ganho_capital_rs']))
            render_metric_row("Em percentual", format_perc(metricas['ganho_capital_perc']), get_color_class(metricas['ganho_capital_perc']))
            
    with col_m2:
        with st.container(border=True):
            yoc = (total_prov / metricas['valor_aplicado']) * 100 if metricas['valor_aplicado'] > 0 else 0
            
            fiis_tickers = st.session_state.carteira_posicao[st.session_state.carteira_posicao['Tipo'] == 'FII']['Ticker'].tolist()
            total_prov_fiis = 0.0
            if not st.session_state.carteira_proventos.empty:
                df_temp_prov = st.session_state.carteira_proventos.copy()
                df_temp_prov['Valor'] = pd.to_numeric(df_temp_prov['Valor'], errors='coerce').fillna(0)
                total_prov_fiis = df_temp_prov[df_temp_prov['Ticker'].isin(fiis_tickers)]['Valor'].sum()
            
            yield_fiis = (total_prov_fiis / metricas['aplicado_fii']) * 100 if metricas['aplicado_fii'] > 0 else 0
            
            render_metric_row("YoC consolidado", format_perc(yoc))
            render_metric_row("Yield FIIs", format_perc(yield_fiis))
            render_metric_row("Aplicado em FII", format_brl(metricas['aplicado_fii']))
            
            import datetime
            hoje = datetime.date.today()
            prov_mensal = 0.0
            if not st.session_state.carteira_proventos.empty:
                try:
                    df_p = st.session_state.carteira_proventos.copy()
                    df_p['Data'] = pd.to_datetime(df_p['Data'], format='%d/%m/%Y', errors='coerce')
                    df_p['Valor'] = pd.to_numeric(df_p['Valor'], errors='coerce').fillna(0)
                    df_p = df_p.dropna(subset=['Data'])
                    prov_mensal = df_p[(df_p['Data'].dt.month == hoje.month) & (df_p['Data'].dt.year == hoje.year)]['Valor'].sum()
                except:
                    pass
            
            render_metric_row("Provento mensal", format_brl(prov_mensal))

    st.markdown("### Proventos Pagos")
    if not df_pivot_prov.empty:
        df_display = df_pivot_prov.copy()
        for col in df_display.columns:
            df_display[col] = df_display[col].apply(format_brl)
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("Adicione proventos para visualizar a tabela mensal.")
        
    st.markdown("---")
    with st.container(border=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.markdown(f"**Total de Proventos:** {format_brl(total_prov)}")
        with col_f2:
            rent_total = ((metricas['ganho_capital_rs'] + total_prov) / metricas['valor_aplicado']) * 100 if metricas['valor_aplicado'] > 0 else 0
            st.markdown(f"<h3 style='margin-top:0;'>PERFORMANCE: <span class='{get_color_class(rent_total)}'>{format_perc(rent_total)}</span></h3>", unsafe_allow_html=True)
"""

with open('dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Substituir o placeholder, ajustando a indentação corretamente
lines = code_to_inject.split('\\n')
indented_lines = ['    ' + line if line.strip() else '' for line in lines]
indented_code = '\\n'.join(indented_lines)

content = content.replace('    # __INSERIR_CARTEIRA_AQUI__', indented_code)

with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
