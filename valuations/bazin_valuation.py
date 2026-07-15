import pandas as pd
from utils import fetch_statusinvest_data

def main():
    print("Buscando dados do StatusInvest...")
    df = fetch_statusinvest_data()
    
    if df.empty:
        print("Nenhum dado retornado. Encerrando.")
        return

    # Filtra ações com Dividend Yield > 6%
    df_filtrado = df[df['dy'] > 6.0].copy()
    
    if df_filtrado.empty:
        print("Nenhuma ação com Dividend Yield > 6% encontrada.")
        return
        
    # Mantém apenas as 3 colunas solicitadas
    df_bazin = df_filtrado[['ticker', 'price', 'dy']].copy()
    
    # Renomeia as colunas
    df_bazin.rename(columns={'ticker': 'Ação', 'price': 'Cotação', 'dy': 'Dividend Yield (%)'}, inplace=True)
    
    # Calcula DPA (12m) = Cotação * (Dividend Yield / 100)
    df_bazin['DPA (12m)'] = df_bazin['Cotação'] * (df_bazin['Dividend Yield (%)'] / 100)
    
    # Calcula Preço Teto = DPA / 0.06
    df_bazin['Preço Teto'] = df_bazin['DPA (12m)'] / 0.06
    
    # Calcula Margem de Segurança = (Preço Teto - Cotação) / Cotação
    df_bazin['Margem Segurança (%)'] = ((df_bazin['Preço Teto'] - df_bazin['Cotação']) / df_bazin['Cotação']) * 100
    
    # Arredondando os valores para ficar mais limpo
    df_bazin['Cotação'] = df_bazin['Cotação'].round(2)
    df_bazin['Dividend Yield (%)'] = df_bazin['Dividend Yield (%)'].round(2)
    df_bazin['DPA (12m)'] = df_bazin['DPA (12m)'].round(2)
    df_bazin['Preço Teto'] = df_bazin['Preço Teto'].round(2)
    df_bazin['Margem Segurança (%)'] = df_bazin['Margem Segurança (%)'].round(2)
    
    # Ranqueia os ativos com Margem de Segurança (%) do maior para o menor
    df_bazin = df_bazin.sort_values(by='Margem Segurança (%)', ascending=False).reset_index(drop=True)
    
    # Exibe a tabela no terminal
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    print("\n" + "="*80)
    print("RANKING DE AÇÕES - PREÇO TETO DO BAZIN (DY > 6%)")
    print("="*80)
    print(df_bazin)
    print("="*80 + "\n")
    
    # Salva o resultado em CSV opcionalmente
    try:
        df_bazin.to_csv("bazin_ranking.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")
        print("Tabela salva localmente como 'bazin_ranking.csv'.\n")
    except Exception as e:
        print(f"Não foi possível salvar o CSV: {e}")
        
    # Modo interativo
    print("=== MODO INTERATIVO ===")
    print("Digite o código da ação (ex: BBAS3) para exibir o Preço Teto e Margem de Segurança.")
    print("Digite 'sair' para encerrar o programa.")
    
    while True:
        try:
            entrada = input("\nAtivo: ").strip().upper()
            if entrada == 'SAIR':
                print("Encerrando o programa...")
                break
            if not entrada:
                continue
                
            ativo_info = df_bazin[df_bazin['Ação'] == entrada]
            
            if not ativo_info.empty:
                row = ativo_info.iloc[0]
                print(f"[{entrada}]")
                print(f"Cotação Atual        : R$ {row['Cotação']:.2f}")
                print(f"Preço Teto (Bazin)   : R$ {row['Preço Teto']:.2f}")
                print(f"Margem de Segurança  : {row['Margem Segurança (%)']:.2f}%")
            else:
                # Verifica se a ação existe no dataframe original mas foi filtrada (DY < 6)
                existe_original = df[df['ticker'] == entrada]
                if not existe_original.empty:
                    dy_original = existe_original.iloc[0]['dy']
                    print(f"O ativo '{entrada}' existe, mas seu Dividend Yield é de {dy_original:.2f}% (menor que 6%), por isso não está no ranking.")
                else:
                    print(f"Ativo '{entrada}' não encontrado na base de dados.")
                    
        except KeyboardInterrupt:
            print("\nEncerrando o programa...")
            break
        except Exception as e:
            print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()
