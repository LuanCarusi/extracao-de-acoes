import pandas as pd
from utils import fetch_statusinvest_data, get_selic

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

def main():
    print("Buscando a taxa Selic atual...")
    selic_atual = get_selic()
    print(f"Taxa Selic atual: {selic_atual:.2f}%\n")
    
    try:
        crescimento_input = input("Qual o crescimento projetivo esperado (%)? (Pressione Enter para usar o padrão 3%): ").strip()
        if crescimento_input == "":
            crescimento = 3.0
        else:
            crescimento = float(crescimento_input.replace(',', '.'))
    except ValueError:
        print("Valor inválido. Usando o padrão de 3.0%.")
        crescimento = 3.0
        
    print(f"\nUtilizando Crescimento Projetivo de {crescimento:.2f}%")
    print("Buscando dados do StatusInvest...")
    
    df = fetch_statusinvest_data()
    
    if df.empty:
        print("Nenhum dado retornado. Encerrando.")
        return

    # Colunas necessárias
    colunas_necessarias = ['ticker', 'price', 'p_l', 'dy', 'roe']
    
    for col in colunas_necessarias:
        if col not in df.columns:
            print(f"Erro: Coluna '{col}' não encontrada nos dados.")
            return
            
    df_lynch = df[colunas_necessarias].copy()
    
    # Renomeia as colunas
    df_lynch.rename(columns={
        'ticker': 'Ação', 
        'price': 'Cotação', 
        'p_l': 'P/L', 
        'dy': 'Dividend Yield (%)',
        'roe': 'ROE (%)'
    }, inplace=True)
    
    # Remove valores nulos essenciais
    df_lynch.dropna(subset=['Cotação', 'P/L', 'Dividend Yield (%)', 'ROE (%)'], inplace=True)
    
    # Filtro 1: Remove ações com ROE menor que a Selic atual
    df_lynch = df_lynch[df_lynch['ROE (%)'] >= selic_atual].copy()
    
    # Filtro 2: O P/L deve ser positivo para o Valuation de Lynch fazer sentido
    df_lynch = df_lynch[df_lynch['P/L'] > 0].copy()
    
    if df_lynch.empty:
        print("Nenhuma ação sobreviveu aos filtros (ROE >= Selic e P/L > 0).")
        return

    # Calcula o Indicador Lynch: (DY + Crescimento Projetivo) / PL
    # Nota: O DY do StatusInvest já é um valor em porcentagem (ex: 5.0 para 5%)
    df_lynch['Indicador Lynch'] = (df_lynch['Dividend Yield (%)'] + crescimento) / df_lynch['P/L']
    
    # Classifica os ativos com base no indicador
    df_lynch['Classificação'] = df_lynch['Indicador Lynch'].apply(classificar_lynch)
    
    # "Qualquer empresa que estiver fora desse range, remova da tabela"
    # O range abrange tudo > 0, então 'Fora do Range' são as <= 0 que já filtramos o P/L, 
    # mas garantimos aqui a limpeza.
    df_lynch = df_lynch[df_lynch['Classificação'] != 'Fora do Range'].copy()
    
    if df_lynch.empty:
        print("Nenhuma ação classificada no range especificado.")
        return
        
    # Arredondando os valores
    df_lynch['Cotação'] = df_lynch['Cotação'].round(2)
    df_lynch['P/L'] = df_lynch['P/L'].round(2)
    df_lynch['Dividend Yield (%)'] = df_lynch['Dividend Yield (%)'].round(2)
    df_lynch['ROE (%)'] = df_lynch['ROE (%)'].round(2)
    df_lynch['Indicador Lynch'] = df_lynch['Indicador Lynch'].round(2)
    
    # Ordenar pelo Indicador Lynch (do maior para o menor)
    df_lynch = df_lynch.sort_values(by='Indicador Lynch', ascending=False).reset_index(drop=True)
    
    # Exibe a tabela no terminal
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    print("\n" + "="*90)
    print(f"RANKING DE AÇÕES - VALUATION DE PETER LYNCH (Crescimento: {crescimento:.2f}% | Selic: {selic_atual:.2f}%)")
    print("="*90)
    print(df_lynch)
    print("="*90 + "\n")
    
    # Salva o resultado em CSV opcionalmente
    try:
        df_lynch.to_csv("lynch_ranking.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")
        print("Tabela salva localmente como 'lynch_ranking.csv'.\n")
    except Exception as e:
        print(f"Não foi possível salvar o CSV: {e}")
        
    # Modo interativo
    print("=== MODO INTERATIVO ===")
    print("Digite o código da ação (ex: BBAS3) para exibir o Indicador Lynch.")
    print("Digite 'sair' para encerrar o programa.")
    
    while True:
        try:
            entrada = input("\nAtivo: ").strip().upper()
            if entrada == 'SAIR':
                print("Encerrando o programa...")
                break
            if not entrada:
                continue
                
            ativo_info = df_lynch[df_lynch['Ação'] == entrada]
            
            if not ativo_info.empty:
                row = ativo_info.iloc[0]
                print(f"[{entrada}]")
                print(f"Cotação Atual          : R$ {row['Cotação']:.2f}")
                print(f"P/L                    : {row['P/L']:.2f}")
                print(f"Dividend Yield         : {row['Dividend Yield (%)']:.2f}%")
                print(f"ROE                    : {row['ROE (%)']:.2f}%")
                print(f"Indicador Lynch        : {row['Indicador Lynch']:.2f}")
                print(f"Classificação          : {row['Classificação']}")
            else:
                # Verifica se a ação existe no dataframe original
                existe_original = df[df['ticker'] == entrada]
                if not existe_original.empty:
                    v = existe_original.iloc[0]
                    roe = v.get('roe', 0)
                    pl = v.get('p_l', 0)
                    
                    motivo = []
                    if roe < selic_atual:
                        motivo.append(f"ROE ({roe:.2f}%) é menor que a Selic ({selic_atual:.2f}%)")
                    if pl <= 0:
                        motivo.append(f"P/L negativo ou zero ({pl:.2f})")
                        
                    if motivo:
                        print(f"O ativo '{entrada}' foi filtrado pelos seguintes motivos: " + " | ".join(motivo))
                    else:
                        print(f"Ativo '{entrada}' não atendeu aos critérios finais do ranking.")
                else:
                    print(f"Ativo '{entrada}' não encontrado na base de dados.")
                    
        except KeyboardInterrupt:
            print("\nEncerrando o programa...")
            break
        except Exception as e:
            print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()
