from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from bot import Bot
import threading
import time

app = Flask(__name__)
CORS(app)

bot = Bot()


@app.route('/')
def hello_world():
    print(3)
    return 'Hello, World!'

# Fetch Data


@app.route('/api/post', methods=['Post'])
def data_post():
    # Here key is the URL parameter you want to fetch
    # print(request)
    data = request.get_json()
    symbol = data['symbol']
    firstfetch = data['firstfetch']

    # get order data
    feed_order_data = None
    feed_balance = None
    daily_profit_data = None
    total_profit_data = None
    available_symbols = None
    if firstfetch or bot.recently_ordered:
        if symbol:
            order_data = bot.get_db_orders(symbol)
        # print(order_data)
        feed_order_data = []
        for order in order_data:
            profit = None
            if order["action"].upper() == "SELL":
                if (order["profit"]["amount"] < 0):
                    profit = f'-${abs(order["profit"]["amount"])
                                  } ({order["profit"]["percent"]}%)'
                else:
                    profit = f'${order["profit"]["amount"]
                                 } ({order["profit"]["percent"]}%)'
                # if(order["profit"]["amount"] < 0):
                #     profit = f'-${abs(order["profit"]["amount"])} (0.5%)'
                # else:
                # profit = order["price"] * order["amount"] * 0.005 / 1.005
                # profit = f'${profit:,.2f} (0.5%)'
            feed_order_data.append({
                "time": order["time"]["EDT"],
                "action": order["action"],
                "amount": order["amount"],
                "status": order["status"],
                "profit": profit,
                "price": f'${order["price"]:,.2f}',
            })
        # print(feed_order_data)
        # Get Balance
        balance = bot.get_balance()
        feed_balance = []
        for sb in balance.keys():
            feed_balance.append({
                "symbol": sb,
                "free": f'{balance[sb]["free"]:,.3f}',
                "locked": f'{balance[sb]["locked"]:,.3f}',
            })
        # Get Metadata
        metadata = bot.get_metadata()
        daily_profit_data = []
        for mt in metadata["daily_metadata"]:
            # if(order["profit"]["amount"] < 0):
            profit = f'${abs(mt["profit"]):,.2f}'
            if mt["profit"] < 0:
                profit = f'-{profit}'
            daily_profit_data.append({
                "date": mt["_id"],
                "profit": profit,
                "trades": mt["trades"]
            })
        total_profit_data = metadata["total_metadata"]

        profit = f'${abs(total_profit_data["profit"]):,.2f}'

        if total_profit_data["profit"] < 0:
            profit = f'-{profit}'
        total_profit_data["profit"] = profit

        bot.recently_ordered = False

    # Get market data
    if symbol:
        if bot.running and symbol.upper() == bot.symbol.upper():
            market_data = bot.df_kline
        else:
            market_data = bot.fetch_market(symbol.upper())
    # convert df to json
    historicaldata = []
    emadata = []
    for _, row in market_data.tail(60).iterrows():
        data = {"time": str(row['Close time']), "price": row['Close'], "MA5": int(
            row['MA_5']*100)/100, "MA10": int(row['MA_10']*100)/100}
        # print(data)
        historicaldata.append(data)
        emadata.append({"time": str(row['Close time']), "ema": int(
            row['EMA_diff']*100)/100, "signal": int(row['EMA_signal']*100)/100})
    return {"historical_data": historicaldata, "emadata": emadata, "balance": feed_balance, "order_data": feed_order_data,
            "daily_profit_data": daily_profit_data, "total_profit_data": total_profit_data, "available_symbols": available_symbols,
            "bot_running": bot.running, "trade_symbol": bot.symbol, "trade_mtv": bot.mtv, "trade_tp": f'{(bot.tp-1)*100:,.2f}'}


@app.route('/api/pause', methods=['POST'])
def pause_bot():
    global bot
    print(f'bot is running {bot.running}')
    bot.running = False
    return {}


@app.route('/api/manualbuy', methods=['POST'])
def manual_buy():
    data = request.get_json()
    print(data)

    symbol = data["symbol"].upper()
    amount = float(data["mbp"])

    if bot.running:
        symbol = bot.symbol

    response = bot.manual_order(symbol, "BUY", amount)

    if response:
        return jsonify({"message": "Successfully ordered", "status": 500})
    else:
        return jsonify({"message": "Invaild requests", "status": 400})


@app.route('/api/manualsell', methods=['POST'])
def manual_sell():
    data = request.get_json()
    print(data)

    symbol = data["symbol"].upper()
    amount = float(data["msp"])

    if bot.running:
        symbol = bot.symbol

    response = bot.manual_order(symbol, "SELL", amount)

    if response:
        return jsonify({"message": "Successfully ordered", "status": 500})
    else:
        return jsonify({"message": "Invaild requests", "status": 400})


@app.route('/api/submittp', methods=['POST'])
def update_tp():
    data = request.get_json()
    print(data)

    if "tp" in data.keys():
        bot.tp = 1+float(data["tp"])/10000
        return jsonify({"message": "Successfully updated", "status": 500})
    else:
        return jsonify({"message": "Invaild requests", "status": 400})


@app.route('/api/runtrade', methods=['POST'])
def run_trade():
    data = request.get_json()
    print(data)
    # global bot
    # print(bot.symbol)
    bot.symbol = data["symbol"].upper()
    bot.mtv = float(data["mtv"])

    if not bot.running:
        bot.running = True
        bot_thread = threading.Thread(target=bot.start)
        bot_thread.start()
    # bot.trading = True
    return jsonify({"message": "Trade started", "data": data})


@app.route('/api/pasuetrade', methods=['POST'])
def pause_trade():
    data = request.get_json()
    print(data)

    bot.running = False

    # bot.trading = False
    return jsonify({"message": "Trade paused", "data": data})


@app.route('/api/downloaddata', methods=["GET"])
def download_data():
    csv_file = bot.download_orders()
    if csv_file:
        return send_file(csv_file, as_attachment=True)
    return jsonify({"message": "failed data"})


if __name__ == '__main__':
    # bot = Bot()

    # bot_thread = threading.Thread(target=bot.start)
    # bot_thread.start()
    # # time.sleep(5)
    # bot.running = False

    # app.debug = True
    app.run(port=5000, host='0.0.0.0')
