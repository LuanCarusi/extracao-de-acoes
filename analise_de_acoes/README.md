# Screening de Ações Brasileiras

Projeto em Python que extrai, analisa e ranqueia as melhores ações da bolsa brasileira com base em indicadores fundamentalistas e critérios de oportunidades definidos pelo usuário.

## 🚀 Como Funciona

1. **Extração de Dados**: Utiliza a API pública (não-oficial) do [StatusInvest](https://statusinvest.com.br) para coletar as métricas de centenas de ativos.
2. **Filtragem Geral**: Aplica um funil (definido em `config.py`) para retirar empresas sem liquidez, não rentáveis ou muito caras.
3. **Mapeamento de Setores**: Scrapping no [Fundamentus](https://www.fundamentus.com.br) de todas as empresas restantes.
4. **Filtros Específicos por Setor**: 3 tipos de filtros: geral, *Bancos* e *Seguradoras*, utilizando métricas diferentes para cada uma.
5. **Cálculo de Score e Ranking**: As empresas remanescentes são ordenadas criando um *Score Final* que consolida sua posição nos indicadores: *Dividend Yield, P/L, Margem Líquida, Dívida/Ebit e ROE*.
6. **Exportação**: Gera um arquivo `ranking_acoes_resultado.csv` formatado especialmente para o Excel brasileiro.

---

## 💻 Estrutura do Projeto

O código está estruturado em módulos:

- **`main.py`**: Script principal que orquestra todo o funcionamento. Arquivo a ser executado.
- **`src/config.py`**: Arquivo de configurações onde ficam todos os filtros e métricas. Possibilidade de alteração das métricas.
- **`src/data_extractor.py`**: Lógica de conexão com o StatusInvest e extração dos setores via Fundamentus.
- **`src/analyzer.py`**: Processa os dados usando o poder computacional da biblioteca `pandas`.
- **`requirements.txt`**: A lista de dependências externas do Python necessárias.

---

## 🛠️ Como Instalar e Rodar

### 1. Pré-Requisitos

Ter o **Python** (versão 3.8+) instalado no computador.

### 2. Preparando o Ambiente Virtual

Abra o seu terminal (Powershell ou CMD) na raiz desta pasta e execute os comandos:

```powershell
# Criação do Ambiente Virtual
python -m venv venv

# Ativação do Ambiente Virtual
.\venv\Scripts\Activate.ps1

# Instalação das bibliotecas
pip install -r requirements.txt openpyxl
```

### 3. Rodando o Script

Com o ambiente ativado, execute:

```powershell
python main.py
```

O resultado aparecerá no seu terminal e um arquivo `ranking_acoes_resultado.csv` será gerado.

---

## Como alterar as Métricas e Regras?

Toda vez que você quiser mudar a estratégia de análise, basta editar o arquivo `src/config.py`.

Exemplo do `config.py`:
```python
# Mude os valores mínimos ou máximos conforme seu perfil de risco
FILTROS_GERAIS = {
    'liquidezmediadiaria_min': 1_000_000,
    'roic_min': 7.9,
    'dy_min': 5.0, # Ex: aumentar para 8.0 se quiser focar apenas em grandes dividendos
    'p_l_max': 15.1,
    'margemliquida_min': 4.9,
    'dividaliquidaebit_max': 5.5,
    'roe_min': 9.5
}
```

Se desejar criar uma regra rígida apenas para Empresas de **Energia Elétrica**:

```python
FILTROS_POR_SETOR = {
    'Energia Elétrica': {
        'dy_min': 8.0, # Exige dividendos maiores desse setor
    }
}
```
Salvar o `config.py` e rodar o `main.py` de novo aplicará imediatamente sua nova estratégia.

---

*Desenvolvido por Luan Carusi.*
