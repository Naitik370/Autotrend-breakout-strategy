import numpy as np
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from trendline_automation import fit_trendlines_single, fit_upper_trendline
import mplfinance as mpf
import yfinance as yf

def trendline_breakout_dataset(ohlcv: pd.DataFrame, lookback:int=60, hold_period:int=60, sl_percent: float=0.025, tp_percent: float=0.10):
    # Prepare data
    close = ohlcv['close'].to_numpy()

    trades = pd.DataFrame()
    trade_i = 0
    in_trade = False

    # Loop through data
    for i in range(lookback, len(ohlcv)):
        window = close[i - lookback: i]
        s_coefs, r_coefs = fit_trendlines_single(window)
        r_val = r_coefs[1] + lookback * r_coefs[0]

        if not in_trade and close[i] > r_val:
            tp_price = close[i] * (1 + tp_percent)
            sl_price = close[i] * (1 - sl_percent)
            hp_i = i + hold_period
            in_trade = True

            # Record trade details
            trades.loc[trade_i, 'entry_i'] = i
            trades.loc[trade_i, 'entry_p'] = close[i]
            trades.loc[trade_i, 'sl'] = sl_price 
            trades.loc[trade_i, 'tp'] = tp_price 
            trades.loc[trade_i, 'hp_i'] = i + hold_period
            trades.loc[trade_i, 'slope'] = r_coefs[0]
            trades.loc[trade_i, 'intercept'] = r_coefs[1]

            # Additional features
            trades.loc[trade_i, 'resist_s'] = r_coefs[0]  
            line_vals = (r_coefs[1] + np.arange(lookback) * r_coefs[0])
            err = np.sum(line_vals - window) / lookback
            trades.loc[trade_i, 'tl_err'] = err
            diff = line_vals - window
            trades.loc[trade_i, 'max_dist'] = diff.max()
            trades.loc[trade_i, 'vol'] = ohlcv['volume'].iloc[i]

        if in_trade:
            if close[i] >= tp_price or close[i] <= sl_price or i >= hp_i:
                trades.loc[trade_i, 'exit_i'] = i
                trades.loc[trade_i, 'exit_p'] = close[i]
                in_trade = False
                trade_i += 1

    trades['return'] = trades['exit_p'] - trades['entry_p']
    data_x = trades[['resist_s', 'tl_err', 'vol', 'max_dist']]
    data_y = pd.Series(0, index=trades.index)
    data_y.loc[trades['return'] > 0] = 1

    return trades, data_x, data_y

if __name__ == '__main__':
    # Fetch data
    data = yf.download('^NSEI', start='2000-01-03', end='2024-01-03')
    data.columns = [x.lower() for x in data.columns]
    data = data.dropna()

    # Generate trades
    trades, data_x, data_y = trendline_breakout_dataset(data)

    # Calculate returns
    trades = trades.dropna()
    signal = np.zeros(len(data))
    for i in range(len(trades)):
        trade = trades.iloc[i]
        signal[int(trade['entry_i']):int(trade['exit_i'])] = 1.
    data['r'] = data['close'].diff().shift(-1)
    data['sig'] = signal
    returns = data['r'] * data['sig']
    print(trades)
    
    # Print metrics
    print("Profit Factor", returns[returns > 0].sum() / returns[returns < 0].abs().sum())
    print("Win Rate", len(trades[trades['return'] > 0]) / len(trades))
    print("Average Trade", trades['return'].mean()) 

    # Plot returns
    plt.style.use('dark_background')
    returns.cumsum().plot()
    plt.ylabel("Cumulative Log Return")



