# Screening de Ações Brasileiras

Projeto em Python que extrai, analisa e ranqueia as melhores ações da bolsa brasileira com base em indicadores fundamentalistas e critérios de oportunidades definidos pelo usuário. O código é altamente performático, assíncrono e modular.

## 🚀 Como Funciona

1. **Extração de Dados**: Utiliza a API pública (não-oficial) do [StatusInvest](https://statusinvest.com.br) para coletar as métricas de centenas de ativos instantaneamente.
2. **Filtragem Geral**: Aplica um funil (definido em `config.py`) para retirar empresas sem liquidez, não rentáveis ou muito caras.
3. **Mapeamento de Setores**: De forma 100% assíncrona, faz scrap no [Fundamentus](https://www.fundamentus.com.br) de todas as empresas restantes ao mesmo tempo, reduzindo o tempo de consulta que seria de minutos para poucos segundos.
4. **Filtros Específicos por Setor**: Permite regras mais exigentes/específicas para determinados setores, como *Bancos* ou *Seguradoras*.
5. **Cálculo de Score e Ranking**: As empresas que sobrevivem aos filtros são ordenadas criando um *Score Final* que consolida sua posição nos indicadores: *Dividend Yield, P/L, Margem Líquida, Dívida/Ebit e ROE*.
6. **Exportação**: Gera um arquivo `ranking_acoes_resultado.csv` formatado especialmente para o Excel brasileiro, sem distorcer números em datas.

---

## 💻 Estrutura do Projeto

O código está estruturado em módulos para facilitar a escalabilidade:

- **`main.py`**: O script principal que orquestra todo o funcionamento. É este arquivo que você deve executar.
- **`src/config.py`**: Arquivo de configurações onde ficam todos os filtros e métricas. Aqui você pode alterar as regras do jogo.
- **`src/data_extractor.py`**: Lógica de conexão com o StatusInvest e extração assíncrona dos setores via Fundamentus.
- **`src/analyzer.py`**: A inteligência da aplicação. Processa os dados usando o poder computacional da biblioteca `pandas`.
- **`requirements.txt`**: A lista de dependências externas do Python necessárias.

---

## 🛠️ Como Instalar e Rodar

### 1. Pré-Requisitos

Ter o **Python** (versão 3.8+) instalado no computador.

### 2. Preparando o Ambiente Virtual

Abra o seu terminal (Powershell ou CMD) na raiz desta pasta e execute os comandos:

```powershell
# Criação do Ambiente Virtual (só precisa rodar uma vez)
python -m venv venv

# Ativação do Ambiente Virtual (você roda sempre que abrir o terminal)
.\venv\Scripts\Activate.ps1

# Instalação das bibliotecas
pip install -r requirements.txt openpyxl
```

### 3. Rodando o Script

Com o ambiente ativado (você verá um `(venv)` no console), basta executar:

```powershell
python main.py
```

O resultado aparecerá formatado no seu terminal e um arquivo `ranking_acoes_resultado.csv` será gerado. Você pode dar dois cliques nele para abrir direto no Excel sem bugs.

---

## ⚙️ Como alterar as Métricas e Regras?

Toda vez que você quiser mudar a estratégia de análise, não precisa mexer na lógica, **basta editar o arquivo `src/config.py`**.

Exemplo do `config.py`:
```python
# Mude os valores mínimos ou máximos conforme seu apetite de risco
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

*Desenvolvido por Luan Carusi (e otimizado por IA).*
