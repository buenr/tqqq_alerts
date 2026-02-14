import yfinance as yf
import pandas as pd
import numpy as np

def run_optimization():
    ticker = "TQQQ"
    initial_investment = 10000
    ret_window = 63
    
    print(f"Fetching max history for {ticker}...")
    data = yf.download(ticker, period="max", interval="1d", progress=False)
    
    if data.empty:
        print("No data found.")
        return

    # Extract Close prices
    if isinstance(data.columns, pd.MultiIndex):
        close = data['Close'][ticker]
    else:
        close = data['Close']
        
    df = pd.DataFrame(index=data.index)
    df['Price'] = close
    df['ret_63'] = df['Price'].pct_change(periods=ret_window) * 100
    df = df.dropna(subset=['ret_63'])
    
    # Define thresholds
    buy_thresholds = np.arange(-25, 6, 5) # -25, -20, ..., 0, 5
    sell_thresholds = np.arange(35, 70, 5) # 35, 40, ..., 60, 65
    
    results = []

    for buy_th in buy_thresholds:
        for sell_th in sell_thresholds:
            # Simulation
            cash = initial_investment
            shares = 0
            in_position = False
            
            for _, row in df.iterrows():
                price = row['Price']
                ind = row['ret_63']
                
                if not in_position and ind < buy_th:
                    shares = cash / price
                    cash = 0
                    in_position = True
                elif in_position and ind > sell_th:
                    cash = shares * price
                    shares = 0
                    in_position = False
            
            final_value = (shares * df['Price'].iloc[-1]) if in_position else cash
            results.append({
                'Buy_Thresh': buy_th,
                'Sell_Thresh': sell_th,
                'Final_Value': final_value
            })

    # Convert to DataFrame to find the best
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(by='Final_Value', ascending=False)
    
    best = results_df.iloc[0]
    print("\nBEST STRATEGY FOUND:")
    print(f"Buy Threshold: {best['Buy_Thresh']}%")
    print(f"Sell Threshold: {best['Sell_Thresh']}%")
    print(f"Final Value:   ${best['Final_Value']:,.2f}")
    
    print("\nTop 5 Results:")
    print(results_df.head(5).to_string(index=False))

if __name__ == "__main__":
    run_optimization()
