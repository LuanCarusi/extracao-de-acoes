import yfinance as yf
t = yf.Ticker('TAEE11.SA')
print("Cash flow data:")
print(t.cash_flow.index if t.cash_flow is not None else "No data")
try:
    print(t.cash_flow.loc['Free Cash Flow'])
except:
    print("No Free Cash Flow directly available, checking cash_flow...")
