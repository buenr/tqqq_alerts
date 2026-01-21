import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def generate_strategy_comparison():
    ticker = "TQQQ"
    initial_investment = 10000
    ret_window = 63
    buy_thresh = -5.0
    sell_thresh = 45.0
    
    print(f"Fetching data for {ticker}...")
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
    
    # 1. Calculate Buy & Hold Value
    first_price = df['Price'].iloc[0]
    initial_shares = initial_investment / first_price
    df['Buy_and_Hold'] = df['Price'] * initial_shares
    
    # 2. Simulation for Optimal Strategy
    cash = initial_investment
    shares = 0
    in_position = False
    
    portfolio_values = []
    trades = []
    
    for date, row in df.iterrows():
        price = row['Price']
        ind = row['ret_63']
        
        # BUY SIGNAL
        if not in_position and ind < buy_thresh:
            shares = cash / price
            cash = 0
            in_position = True
            trades.append({
                'Date': date,
                'Type': 'BUY',
                'Price': price,
                'Shares': shares,
                'Indicator': ind,
                'Portfolio_Value': shares * price
            })
            
        # SELL SIGNAL
        elif in_position and ind > sell_thresh:
            val_at_sell = shares * price
            trades.append({
                'Date': date,
                'Type': 'SELL',
                'Price': price,
                'Shares': shares,
                'Indicator': ind,
                'Portfolio_Value': val_at_sell
            })
            cash = val_at_sell
            shares = 0
            in_position = False
            
        # Track daily portfolio value
        current_val = (shares * price) if in_position else cash
        portfolio_values.append(current_val)
        
    df['Optimal_Strategy'] = portfolio_values
    trades_df = pd.DataFrame(trades)
    
    # Create the Interactive Comparison Chart
    fig = go.Figure()
    
    # Trace 1: Buy & Hold
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['Buy_and_Hold'], 
            name="Buy & Hold TQQQ", 
            line=dict(color='#6c757d', width=1.5, dash='dot'),
            opacity=0.6
        )
    )
    
    # Trace 2: Optimal Strategy
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['Optimal_Strategy'], 
            name="Optimal Strategy (-5% / 45%)", 
            line=dict(color='#28a745', width=3)
        )
    )
    
    # 3. Add Buy Markers on Strategy Curve
    buy_trades = trades_df[trades_df['Type'] == 'BUY']
    fig.add_trace(
        go.Scatter(
            x=buy_trades['Date'], y=buy_trades['Portfolio_Value'], mode='markers',
            name='BUY Signal', marker=dict(symbol='triangle-up', size=14, color='white', line=dict(width=2, color='darkgreen')),
            customdata=np.stack((buy_trades['Price'], buy_trades['Shares'], buy_trades['Indicator']), axis=-1),
            hovertemplate="<b>BUY EVENT</b><br>" +
                          "Date: %{x}<br>" +
                          "Portfolio Value: $%{y:,.2f}<br>" +
                          "TQQQ Price: $%{customdata[0]:.2f}<br>" +
                          "Shares Bought: %{customdata[1]:.2f}<br>" +
                          "ret_63: %{customdata[2]:.2f}%<extra></extra>"
        )
    )
    
    # 4. Add Sell Markers on Strategy Curve
    sell_trades = trades_df[trades_df['Type'] == 'SELL']
    fig.add_trace(
        go.Scatter(
            x=sell_trades['Date'], y=sell_trades['Portfolio_Value'], mode='markers',
            name='SELL Signal', marker=dict(symbol='triangle-down', size=14, color='white', line=dict(width=2, color='darkred')),
            customdata=np.stack((sell_trades['Price'], sell_trades['Shares'], sell_trades['Indicator']), axis=-1),
            hovertemplate="<b>SELL EVENT</b><br>" +
                          "Date: %{x}<br>" +
                          "Portfolio Value: $%{y:,.2f}<br>" +
                          "TQQQ Price: $%{customdata[0]:.2f}<br>" +
                          "Shares Sold: %{customdata[1]:.2f}<br>" +
                          "ret_63: %{customdata[2]:.2f}%<extra></extra>"
        )
    )
    
    # Styling
    fig.update_layout(
        title=dict(
            text="Strategy Performance vs. Buy & Hold (TQQQ)",
            font=dict(size=24, color='#1e3a5f'),
            x=0.5
        ),
        template='plotly_white',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        yaxis=dict(
            title="Portfolio Value ($)",
            type="log",
            gridcolor='lightgrey',
            tickformat="$,.0f"
        ),
        xaxis=dict(
            title="Year",
            rangeslider_visible=True
        ),
        margin=dict(l=50, r=50, t=100, b=50)
    )
    
    # Add summary boxes
    final_strat = df['Optimal_Strategy'].iloc[-1]
    final_bnh = df['Buy_and_Hold'].iloc[-1]
    
    fig.add_annotation(
        xref="paper", yref="paper", x=0.02, y=0.98,
        text=f"<b>OPTIMAL STRATEGY</b><br>Final: ${final_strat:,.2f}<br>Total Return: {(final_strat/initial_investment - 1)*100:,.0f}%",
        showarrow=False, align="left", bgcolor="rgba(40,167,69,0.1)", bordercolor="#28a745", borderwidth=2, borderpad=10
    )
    
    fig.add_annotation(
        xref="paper", yref="paper", x=0.02, y=0.82,
        text=f"<b>BUY AND HOLD</b><br>Final: ${final_bnh:,.2f}<br>Total Return: {(final_bnh/initial_investment - 1)*100:,.0f}%",
        showarrow=False, align="left", bgcolor="rgba(108,117,125,0.1)", bordercolor="#6c757d", borderwidth=1, borderpad=10
    )

    output_file = "strategy_comparison.html"
    fig.write_html(output_file)
    print(f"Comparison visualization saved to: {output_file}")

if __name__ == "__main__":
    generate_strategy_comparison()
