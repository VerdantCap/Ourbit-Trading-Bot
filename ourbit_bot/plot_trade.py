import spot.v3.ourbit_spot_v3 as ourbit_spot_v3

import numpy as np  
import matplotlib.pyplot as plt  
from matplotlib.animation import FuncAnimation
import pandas as pd
import datetime
import time

hosts = "https://api.ourbit.com"
ourbit_key = "ob0vglFmsLo8XMExyw"
ourbit_secret = "672ec2ba47b649fbbd25efe609cd9c54"

# Market Data
"""get kline"""
data = ourbit_spot_v3.ourbit_market(ourbit_hosts=hosts)

# Spot Trade
"""place an order"""
trade = ourbit_spot_v3.ourbit_trade(ourbit_key=ourbit_key, ourbit_secret=ourbit_secret, ourbit_hosts=hosts)

def convert_list_to_df(kline):
    headers = ["Open time", "Open", "High", "Low", "Close", "Volume", "Close time", "Qute asset volume"]

    # Create DataFrame with specified headers
    df = pd.DataFrame(kline, columns=headers)

    df["Open time"] = df["Open time"].apply(lambda x: datetime.datetime.fromtimestamp(x/1000.0))
    df["Close time"] = df["Close time"].apply(lambda x: datetime.datetime.fromtimestamp(x/1000.0))

    df["Close"] = df["Close"].apply(lambda x: float(x))

    return df

def trade_spot(side, quantity, price):
    params = {
        "symbol": "BTCUSDT",
        "side": side,
        "type": "LIMIT",
        "quantity":quantity,
        "price": price
    }

    response = trade.post_order(params)

def calc_ma(df, window_size):
    close_df = df["Close"]

    df[f'MA_{window_size}']=close_df.rolling(window=window_size).mean()

    return df
    


# Initial setup for dual lines  
fig, ax = plt.subplots()
plt.grid(True)
close_line, = ax.plot([], [], 'b-', label='Close Price')  # Close data series in red  
ma5_line, = ax.plot([], [], 'r-', label='MA5 Price')  # MA 5 data series in blue
ma20_line, = ax.plot([], [], 'g-', label='MA20 Price')  # MA 20 data series in green
ax.legend()

def fetch_data():
    params = {
        'symbol': 'BTCUSDT',
        'interval': '1m',
        'limit':  50
    }
    kline = data.get_kline(params)
    df = convert_list_to_df(kline)

    # Calcuate Moving Average
    df = calc_ma(df, 5)
    df = calc_ma(df, 20)

    return df

def init():  
    ax.set_xlim(0, 50)  # Assuming 50 data points max as per range  
    ax.set_ylim(0, 1)  # Set to relevant y-limits based on expected 'Close' values  
    return close_line, ma5_line, ma20_line 

def update(_):
    # print(frame)
    df = fetch_data()  
    x_data = list(range(len(df)))  # Updated to handle variable length data  
    close_data = df["Close"].tolist()  # Assuming 'Close' is a column in your DataFrame  
    ma5_data = df["MA_5"].tolist()
    ma_20_data = df["MA_20"].tolist()

    close_line.set_data(x_data, close_data)  
    ma5_line.set_data(x_data, ma5_data)
    ma20_line.set_data(x_data, ma_20_data)

    ax.relim()  # Recompute the ax.dataLim  
    ax.autoscale_view()  # Automatic rescaling of the view limits
    return close_line, ma5_line, ma20_line

# Animation  
ani = FuncAnimation(fig, update, blit=True, interval=500)  
plt.show()