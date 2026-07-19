# Valuations de Ações

Este diretório contém scripts para realizar cálculos de *valuation* (decisão do preço justo de uma empresa) utilizando dados extraídos em tempo real do site StatusInvest. 

A extração de dados é centralizada no arquivo `utils.py`, garantindo que os scripts desta pasta sejam independentes do resto do projeto de Screening Geral.

## Requisitos e Ambiente Virtual (VENV)

Para garantir o bom funcionamento do código, recomendo fortemente o uso de um Ambiente Virtual.

Abra o seu terminal dentro da pasta `valuations` e execute os comandos abaixo para criar o ambiente e instalar as bibliotecas:

```bash
# 1. Cria o ambiente virtual
python -m venv venv

# 2. Ativa o ambiente virtual (no Windows)
.\venv\Scripts\activate

# 3. Instala todas as dependências isoladamente
pip install -r requirements.txt
```

> **Atenção:** Sempre que você abrir um terminal novo para rodar os códigos ou o Streamlit, lembre-se de rodar `.\venv\Scripts\activate` antes.

## Como Usar os Códigos

Para executar qualquer um dos códigos de valuation pelo terminal, navegue até esta pasta e execute o script desejado usando o Python.

### 1. Preço-teto do Bazin (`bazin_valuation.py`)
Baseado no método de Décio Bazin, foca em empresas que pagam bons dividendos.
- Filtra ações com **Dividend Yield > 6%**.
- Calcula o DPA (Dividendo Por Ação) projetado.
- Calcula o Preço-teto exigindo no mínimo 6% de retorno em dividendos.
- Ranqueia as ações pela maior Margem de Segurança.

**Para executar:**
```bash
python bazin_valuation.py
```

### 2. Valor Intrínseco de Graham (`graham_valuation.py`)
Baseado no método de Benjamin Graham, foca no valor em ativos da empresa e seu lucro, ignorando dividendos. A fórmula busca empresas que estejam sendo negociadas abaixo do que realmente valem contábilmente.
- Fórmula utilizada: `Raiz Quadrada de (22.5 * LPA * VPA)`
- Filtra apenas as ações onde a **Margem de Segurança seja superior a 80%**.
- Ações com VPA ou LPA negativos são desconsideradas, visto que o método exige lucros e patrimônio positivos.

**Para executar:**
```bash
python graham_valuation.py
```

### 3. Valuation de Peter Lynch (`lynch_valuation.py`)
Baseado na métrica de Fair Value de Peter Lynch, que avalia o quão "barata" ou "cara" uma empresa está comparando seu P/L com seu crescimento e dividendos.
- Busca a **Taxa Selic atualizada via API do Banco Central** automaticamente.
- Filtra ações com **ROE menor que a Selic atual**.
- Calcula o **Indicador Lynch**: `(Dividend Yield + Crescimento Projetivo) / P/L`.
- Permite que você digite qual Crescimento Projetivo você deseja utilizar em runtime (o padrão é 3%).
- Ações são classificadas em:
  - `> 2`: Muito Barata
  - `1.5 a 2`: Barata
  - `1 a 1.5`: Justo
  - `< 1`: Cara

**Para executar:**
```bash
python lynch_valuation.py
```

### 4. Valuation DCF - Fluxo de Caixa Livre de Damodaran (`damodaran_valuation.py`)
Baseado na metodologia acadêmica e profunda de Aswath Damodaran. Este valuation projeta o crescimento do caixa de uma empresa nos próximos 6 anos e o desconta a valor presente (VPL).

**Para executar (Interface Web):**
```bash
streamlit run damodaran_valuation.py
```

### 5. Dashboard Consolidado de Valuations (`dashboard.py`)
Este é o aplicativo definitivo que unifica as 4 metodologias acima (Damodaran, Bazin, Graham e Lynch).

**Como Usar o Dashboard:**
1. No seu terminal, digite o comando abaixo:
   ```bash
   streamlit run dashboard.py
   ```
2. Uma nova aba se abrirá automaticamente no seu navegador.
3. No painel superior ("Parâmetros Gerais"), digite o **Ticker da Ação** (ex: `TAEE11`, `bbas3`).
4. Ajuste os parâmetros se desejar (Taxa de Desconto, Perpetuidade, Crescimento para o modelo de Lynch).
5. O sistema buscará instantaneamente a cotação e os dados fundamentalistas no StatusInvest, e o histórico de Fluxo de Caixa no Yahoo Finance.
6. Navegue pelas **Abas** para comparar a mesma ação sob a ótica de diferentes grandes investidores:
   - **Damodaran**: Edite o CAGR (%) na tabela para projetar o futuro da empresa. FCL e VPL são calculados automaticamente.
   - **Décio Bazin**: Veja o Preço Teto baseado em dividendos projetados.
   - **Benjamin Graham**: Descubra o Valor Intrínseco baseado em Lucros e Patrimônio.
   - **Peter Lynch**: Analise o Fair Value relacionando Dividendos, Crescimento e P/L.

## Modo Interativo (Scripts de Terminal)

Todos os scripts de terminal (Bazin, Graham e Lynch) possuem um modo interativo no final de sua execução. Após exibirem o ranking no terminal e salvarem um arquivo `.csv` correspondente, eles apresentarão um prompt:
`Ativo: `

Nele, você pode digitar o código da ação (ex: `BBAS3`, `VALE3`) para ver os indicadores e as margens de segurança específicos daquele ativo, mesmo que não estejam no topo do ranking.

Para encerrar o programa, basta digitar `sair`.
