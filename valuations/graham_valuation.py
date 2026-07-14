import math
import pandas as pd
from utils import fetch_statusinvest_data

def main():
    print("Buscando dados do StatusInvest...")
    df = fetch_statusinvest_data()
    
    if df.empty:
        print("Nenhum dado retornado. Encerrando.")
        return

    # Mantém apenas as colunas solicitadas: ticker, cotação, vpa, lpa
    # Note que a api do status invest retorna 'price', 'vpa', 'lpa'
    colunas_necessarias = ['ticker', 'price', 'vpa', 'lpa']
    
    # Verifica se as colunas existem
    for col in colunas_necessarias:
        if col not in df.columns:
            print(f"Erro: Coluna '{col}' não encontrada nos dados.")
            return
            
    df_graham = df[colunas_necessarias].copy()
    
    # Renomeia as colunas
    df_graham.rename(columns={'ticker': 'Ação', 'price': 'Cotação', 'vpa': 'VPA', 'lpa': 'LPA'}, inplace=True)
    
    # Remove valores nulos
    df_graham.dropna(subset=['Cotação', 'VPA', 'LPA'], inplace=True)
    
    # Para o método de Graham, VPA e LPA devem ser positivos para a raiz quadrada.
    # Vamos manter e tentar calcular, e os negativos vamos remover para evitar erro matemático.
    df_graham = df_graham[(df_graham['VPA'] > 0) & (df_graham['LPA'] > 0)].copy()

    if df_graham.empty:
        print("Nenhuma ação com VPA e LPA positivos encontrada.")
        return

    # Calcula Valor Intrínseco = Raiz quadrada de (22.5 * LPA * VPA)
    df_graham['Valor Intrínseco'] = df_graham.apply(lambda row: math.sqrt(22.5 * row['LPA'] * row['VPA']), axis=1)
    
    # Calcula Margem de Segurança = (Valor Intrínseco - Cotação) / Cotação
    df_graham['Margem de Segurança (%)'] = ((df_graham['Valor Intrínseco'] - df_graham['Cotação']) / df_graham['Cotação']) * 100
    
    # Elimina as ações cuja margem de segurança seja inferior a 80%
    df_graham = df_graham[df_graham['Margem de Segurança (%)'] >= 80.0].copy()
    
    if df_graham.empty:
        print("Nenhuma ação com Margem de Segurança >= 80% foi encontrada.")
        return
        
    # Arredondando os valores
    df_graham['Cotação'] = df_graham['Cotação'].round(2)
    df_graham['VPA'] = df_graham['VPA'].round(2)
    df_graham['LPA'] = df_graham['LPA'].round(2)
    df_graham['Valor Intrínseco'] = df_graham['Valor Intrínseco'].round(2)
    df_graham['Margem de Segurança (%)'] = df_graham['Margem de Segurança (%)'].round(2)
    
    # Ranqueia os ativos com Margem de Segurança (%) do maior para o menor
    df_graham = df_graham.sort_values(by='Margem de Segurança (%)', ascending=False).reset_index(drop=True)
    
    # Exibe a tabela no terminal
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    print("\n" + "="*90)
    print("RANKING DE AÇÕES - VALOR INTRÍNSECO DE GRAHAM (MARGEM DE SEGURANÇA >= 80%)")
    print("="*90)
    print(df_graham)
    print("="*90 + "\n")
    
    # Salva o resultado em CSV opcionalmente
    try:
        df_graham.to_csv("graham_ranking.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")
        print("Tabela salva localmente como 'graham_ranking.csv'.\n")
    except Exception as e:
        print(f"Não foi possível salvar o CSV: {e}")
        
    # Modo interativo (opcional e similar ao bazin para manter padrão)
    print("=== MODO INTERATIVO ===")
    print("Digite o código da ação (ex: BBAS3) para exibir o Valor Intrínseco")
    print("Digite 'sair' para encerrar o programa.")
    
    while True:
        try:
            entrada = input("\nAtivo: ").strip().upper()
            if entrada == 'SAIR':
                print("Encerrando o programa...")
                break
            if not entrada:
                continue
                
            ativo_info = df_graham[df_graham['Ação'] == entrada]
            
            if not ativo_info.empty:
                row = ativo_info.iloc[0]
                print(f"[{entrada}]")
                print(f"Cotação Atual          : R$ {row['Cotação']:.2f}")
                print(f"Valor Intrínseco       : R$ {row['Valor Intrínseco']:.2f}")
                print(f"Margem de Segurança    : {row['Margem de Segurança (%)']:.2f}%")
            else:
                # Verifica se a ação existe no dataframe original mas foi filtrada (Margem < 80% ou VPA/LPA negativos)
                existe_original = df[df['ticker'] == entrada]
                if not existe_original.empty:
                    v = existe_original.iloc[0]
                    if v['vpa'] <= 0 or v['lpa'] <= 0:
                        print(f"O ativo '{entrada}' possui VPA ou LPA negativo/zero, inviabilizando a fórmula de Graham.")
                    else:
                        vi = math.sqrt(22.5 * v['lpa'] * v['vpa'])
                        ms = ((vi - v['price']) / v['price']) * 100
                        if ms < 80:
                            print(f"O ativo '{entrada}' existe, mas sua Margem de Segurança é {ms:.2f}% (menor que 80%), por isso não está no ranking.")
                        else:
                            print(f"Ativo '{entrada}' não encontrado no ranking.")
                else:
                    print(f"Ativo '{entrada}' não encontrado na base de dados.")
                    
        except KeyboardInterrupt:
            print("\nEncerrando o programa...")
            break
        except Exception as e:
            print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()
