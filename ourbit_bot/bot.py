import os
import spot.v3.ourbit_spot_v3 as ourbit_spot_v3
import json
import datetime
import pandas as pd
import numpy as np
import time
import threading
from db import MGDB
import asyncio
import websockets
import dotenv
import logging
import pytz
import csv
import asyncio

from tgbot import TGbot

# Basic configuration to log to console
logging.basicConfig(filename='app.log', filemode='w',
                    level=logging.DEBUG,
                    format='%(name)s - %(levelname)s - %(message)s')
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.INFO)

dotenv.load_dotenv(".env", override=True)


async def websocket_client(symbol):
    uri = os.getenv("WEBSOCKET_URI")
    async with websockets.connect(uri) as websocket:
        print("websocket connected")
        logging.info("websocket connected")

        message = {"method": "SUBSCRIPTION", "params": [
            f"spot@public.kline.v3.api@{symbol}@Min1"]}

        await websocket.send(json.dumps(message))

        # To receive data
        while True:
            data = await websocket.recv()
            print(f"Data received: {data}")


class Bot:
    def __init__(self):
        self.kline = []
        self.df_kline = []

        # Set up the Env
        self.hosts = os.getenv("HOSTS")
        self.api_key = os.getenv("API_KEY")
        self.secret_key = os.getenv("API_SECRET")

        # Length of MA
        self.short_period = 5
        self.long_period = 20

        # Market Data
        self.market_data = ourbit_spot_v3.ourbit_market(
            ourbit_hosts=self.hosts)

        # Strategy
        self.strategy = "MACD"

        # Spot Trade
        self.trade = ourbit_spot_v3.ourbit_trade(
            ourbit_key=self.api_key, ourbit_secret=self.secret_key, ourbit_hosts=self.hosts)

        # Spot account
        self.account = ourbit_spot_v3.ourbit_account(
            ourbit_key=self.api_key, ourbit_secret=self.secret_key, ourbit_hosts=self.hosts)

        # Connect DB
        self.db = MGDB()

        # TG bot
        self.tgbot = TGbot()

        # running
        self.running = False
        self.trading = False

        # recently ordered
        self.recently_ordered = False

        self.test_balance = {
            "BTC": 1.5,
            "ETH": 20,
            "SOL": 70,
            "USDT": 1000,
        }

        # trading parameters
        self.symbol = "BTCUSDT"
        self.trade_available = False
        self.is_new_timestamp = False
        self.tp = 1.0015
        self.sl = 0.0

        # last order parameters
        self.last_order_type = None
        self.last_order_time = 0
        self.last_order_price = 0
        self.last_fetch_time = 0

        # half limit order paramteters
        self.half_limit_id = None
        self.half_limit_status = None

        self.get_last_order(self.symbol)

        # last 1 min prices
        self.last_one_min_prices = []
        self.first_entry_time = 0

        self.mtv = 500

        self.order_data = []
        self.metadata = []

        self.ath = np.inf

    def get_db_orders(self, symbol):
        return self.db.get_orders_by_symbol(symbol.upper())

    def get_last_order(self, symbol):
        orders = self.get_db_orders(symbol)

        if len(orders) > 0:
            self.last_order_type = orders[0]["action"]
            self.last_order_price = float(orders[0]["price"])
        else:
            self.last_order_type = "sell"
            self.last_order_price = self.get_current_price(self.symbol)

    def remove_new_orders(self, side, symbol):
        orders = self.trade.get_allorders({"symbol": symbol})
        for order in orders:
            if order["status"] == "NEW" and order["side"] == side.upper():
                self.trade.delete_order(
                    {"symbol": symbol, "orderId": order["orderId"]})

    def get_metadata(self):
        return self.db.get_metadata()

    def convert_list_to_df(self, kline):
        headers = ["Open time", "Open", "High", "Low", "Close",
                   "Volume", "Close time", "Qute asset volume"]

        # Create DataFrame with specified headers
        df = pd.DataFrame(kline, columns=headers)

        # df["Open time"] = df["Open time"].apply(lambda x: datetime.datetime.fromtimestamp(x/1000.0))

        # Define the Eastern timezone
        eastern = pytz.timezone('America/New_York')
        df["Close time"] = df["Close time"].apply(
            lambda x: str(datetime.datetime.fromtimestamp(x/1000.0).astimezone(eastern).strftime('%Y-%m-%d %H:%M')))

        df["Open"] = df["Close"].apply(lambda x: float(x))
        df["High"] = df["Close"].apply(lambda x: float(x))
        df["Low"] = df["Close"].apply(lambda x: float(x))
        df["Close"] = df["Close"].apply(lambda x: float(x))
        df["Volume"] = df["Volume"].apply(lambda x: float(x))
        df["Qute asset volume"] = df["Qute asset volume"].apply(
            lambda x: float(x))

        return df

    def calc_ma(self, df, window_size):
        close_df = df["Close"]

        df['MA_5'] = close_df.rolling(window=5).mean()
        df['MA_10'] = close_df.rolling(window=10).mean()
        df['EMA_12'] = close_df.ewm(span=12, adjust=False).mean()
        df['EMA_26'] = close_df.ewm(span=26, adjust=False).mean()
        df['EMA_diff'] = df['EMA_12'] - df['EMA_26']
        df['EMA_signal'] = df['EMA_diff'].ewm(span=9, adjust=False).mean()

        return df

    def get_balance(self):
        response = self.account.get_account_info()

        balance = {}
        for currency in response["balances"]:
            balance[currency["asset"]] = {}
            balance[currency["asset"]]["free"] = float(currency["free"])
            balance[currency["asset"]]["locked"] = float(currency["locked"])

        return balance

    def get_current_price(self, symbol):
        params = {
            'symbol': symbol,
            'interval': '1m',
            'limit': 1
        }

        # fetch market data
        kline = self.market_data.get_kline(params)
        return float(kline[0][4])

    def trade_limit_order(self, side, price, quantity):
        price = float(price)

        params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "LIMIT",
            "quantity": quantity,
            "price": str(price)
        }
        response = self.trade.post_order(params)
        return response

    def insert_order(self, orderId, side, price, quantity, last_price, highest_price, highest_time, last_buy_price, symbol=None):
        # insert db
        utc_time = datetime.datetime.now(pytz.utc)
        edt_zone = pytz.timezone('America/New_York')
        current_datetime = utc_time.astimezone(edt_zone)

        # Format the date and time to "MM/DD/YYYY HH:MM:SS"
        formatted_datetime = current_datetime.strftime(
            "%m/%d/%Y %H:%M:%S")
        timestamp = current_datetime.timestamp()

        profit = None
        hp = None
        # if sell. calc profit
        if side.upper() == "SELL":
            profit = {}
            profit["amount"] = int((
                float(price) - last_price) * float(quantity) * 100) / 100
            profit["percent"] = int((
                float(price) - last_price) * 10000 / last_price) / 100
        print(highest_price, last_buy_price)
        if last_buy_price and highest_price > 0 and last_buy_price > 0:
            hp = {
                "price": highest_price,
                "time": highest_time,
                "percent": int(float(highest_price) * 10000 / float(last_buy_price)) / 100
            }

        if not symbol:
            symbol = self.symbol
        order_item = {
            "time": {
                "stamp": timestamp,
                "EDT": formatted_datetime
            },
            "orderId": orderId,
            "symbol": symbol,
            "status": "FILLED",
            "action": side.lower(),
            "amount": float(quantity),
            "price": float(price),
            "profit": profit,
            "hp": hp
        }
        print(order_item)
        self.db.insert_order(**order_item)

        return order_item

    def focus_order(self, symbol, side, amount, buy_price):
        def order(side, symbol, price, amount):
            price = float(price)
            balance = self.get_balance()

            # Calculate quantity
            if side == "BUY":
                quantity = int(amount / price * 1000) / 1000
            elif side == "SELL":
                quantity = amount
            params = {
                "symbol": symbol,
                "side": side,
                "type": "LIMIT",
                "quantity": quantity,
                "price": str(price)
            }
            response = self.trade.post_order(params)
            return response

        side = side.upper()
        symbol = symbol.upper()
        token = symbol.split("USDT")[0]
        feedback = {}

        while True:
            try:
                price = self.get_current_price(self.symbol)
                response = order(side, symbol, price, amount)

                if "orderId" not in response.keys():
                    print(f"{side} order is failed", response)
                else:
                    order_id = response['orderId']
                    feedback["price"] = float(response["price"])
                    feedback["orderId"] = response["orderId"]
                    feedback["origQty"] = float(response["origQty"])
                    time.sleep(1)

                balance = self.get_balance()

                if side.upper() == "BUY" and balance["USDT"]["locked"] > 0.0:
                    print('{} hasbeen locked'.format(order_id))
                    self.trade.delete_order(
                        {"symbol": self.symbol.upper(), "orderId": order_id})
                elif "code" in response.keys():
                    if response["code"] == 30004:
                        continue
                    elif response["code"] == 30005:     # Oversold
                        break
                    # time.sleep(0.3)
                elif side.upper() == "SELL" and token in balance.keys() and balance[token]["locked"] > 0.0:
                    print('{} hasbeen locked'.format(order_id))
                    self.trade.delete_order(
                        {"symbol": self.symbol.upper(), "orderId": order_id})
                    # time.sleep(0.3)
                else:
                    break
            except Exception as e:
                print(e)

        # insert order
        params = {
            "orderId": feedback["orderId"],
            "side": side,
            "price": feedback["price"],
            "quantity": feedback["origQty"],
            "last_price": buy_price,
            "highest_price": self.highest_price,
            "highest_time": self.highest_time,
            "last_buy_price": buy_price
        }
        orderItem = self.insert_order(**params)
        feedback["profit"] = orderItem["profit"]

        return feedback

    def trade_manual(self, symbol, side, amount):
        def order(side, symbol, price, amount):
            price = float(price)
            balance = self.get_balance()
            print(balance)

            # Calculate quantity
            if side.upper() == "BUY":
                quantity = int(amount / price * 1000) / 1000
            elif side.upper() == "SELL":
                quantity = amount
            params = {
                "symbol": symbol,
                "side": side.upper(),
                "type": "LIMIT",
                "quantity": quantity,
                "price": str(price)
            }
            response = self.trade.post_order(params)
            return response

        token = symbol.upper().split("USDT")[0]
        feedback = {}

        while True:
            try:
                price = self.get_current_price(self.symbol)
                response = order(side, symbol, price, amount)

                if "orderId" not in response.keys():
                    print(f"{side} order is failed", response)
                else:
                    order_id = response['orderId']
                    feedback["price"] = float(response["price"])
                    feedback["orderId"] = response["orderId"]
                    feedback["origQty"] = float(response["origQty"])
                    time.sleep(1)

                balance = self.get_balance()

                if side.upper() == "BUY" and balance["USDT"]["locked"] > 0.0:
                    print('{} hasbeen locked'.format(order_id))
                    self.trade.delete_order(
                        {"symbol": self.symbol.upper(), "orderId": order_id})
                    # time.sleep(0.3)
                elif side.upper() == "SELL" and token in balance.keys() and balance[token]["locked"] > 0.0:
                    print('{} hasbeen locked'.format(order_id))
                    self.trade.delete_order(
                        {"symbol": self.symbol.upper(), "orderId": order_id})
                    # time.sleep(0.3)
                else:
                    break
            except Exception as e:
                print(e)

        # insert db
        self.insert_order(feedback["orderId"], side, feedback["price"], feedback["origQty"], self.last_order_price,
                          self.highest_price, self.highest_time, None, symbol)

        self.recently_ordered = True

        return feedback

    def manual_order(self, symbol, side, amount):
        token = symbol.upper().split("USDT")[0]
        balance = self.get_balance()

        if side.upper() == "BUY" and "USDT" in balance.keys():
            if amount < 0 or balance["USDT"]["free"] + balance["USDT"]["locked"] < amount:
                return False
            self.remove_new_orders(side.upper(), symbol)
            response = self.trade_manual(symbol, side, amount)
            print(response)

            self.db.insert_trade(
                response["origQty"], response["orderId"], self.symbol, response["price"])
            time.sleep(0.1)
            trade_thread = threading.Thread(
                target=self.one_trade, args=(response["orderId"], ))
            trade_thread.start()

            return True

        elif side.upper() == "SELL" and token in balance.keys():
            return False
            if amount < 0 or balance[token]["free"] + balance[token]["locked"] < amount:
                return False
            self.remove_new_orders(side.upper(), symbol)
            response = self.trade_manual(symbol, side, amount)
            print(response)

            return True

        return False

    def fetch_market(self, symbol):
        params = {
            'symbol': symbol,
            'interval': '1m',
            'limit': 100
        }

        # fetch market data
        kline = []
        try:
            kline = self.market_data.get_kline(params)
        except:
            print("market fetching error")
            self.market_data = ourbit_spot_v3.ourbit_market(
                ourbit_hosts=self.hosts)
        df = self.convert_list_to_df(kline)

        # calculate MA
        df = self.calc_ma(df, self.short_period)
        # df = self.calc_ma(df, self.long_period)

        return df

    def get_ATH(self, symbol):
        params = {
            'symbol': symbol,
            'interval': '4h',
            'limit': 6
        }

        ath = 0

        kline = self.market_data.get_kline(params)
        ath = 0
        for kl in kline:
            if float(kl[2]) > ath:
                ath = float(kl[2])

        return ath

    def update_order(self, orderId, status):
        # current time
        # utc_time = datetime.datetime.now(pytz.utc)
        # edt_zone = pytz.timezone('America/New_York')
        # current_datetime = utc_time.astimezone(edt_zone)

        # # Format the date and time to "MM/DD/YYYY HH:MM:SS"
        # formatted_datetime = current_datetime.strftime(
        #     "%m/%d/%Y %H:%M:%S")
        # timestamp = current_datetime.timestamp()

        updated_item = {
            # "time": {
            #     "stamp": timestamp,
            #     "EDT": formatted_datetime
            # },
            "orderId": orderId,
            "status": status,
        }

        self.db.update_status(**updated_item)

    def download_orders(self):
        db_orders = self.db.find_orders({})

        flat_orders = []
        for order in db_orders:
            profit = None
            hp = None

            if order["profit"]:
                profit = f'{order["profit"]["amount"]
                            } ({order["profit"]["percent"]}%)'
            if "highest price" in order.keys() and order["highest price"]:
                hp = f'{order["highest price"]["price"]} ({order["highest price"]["percent"]}%), {
                    order["highest price"]["time"]["EDT"]}'
            item = {
                "time": order["time"]["EDT"],
                "orderId": order["orderId"],
                "symbol": order["symbol"],
                "status": order["status"],
                "action": order["action"],
                "amount": order["amount"],
                "price": order["price"],
                "profit": profit,
                "highest price": hp
            }
            flat_orders.append(item)
        try:
            # specify the file name
            csv_file = "./assets/output.csv"

            # Opening a CSV file and writing the data
            with open(csv_file, 'w', newline='') as file:
                if flat_orders:
                    writer = csv.DictWriter(
                        file, fieldnames=flat_orders[0].keys())
                    writer.writeheader()
                    writer.writerows(flat_orders)

            print(f'Data has been written to {csv_file}')
            return csv_file
        except Exception as e:
            print(e)
            return False

    def get_available_trades(self, symbol):
        available_trades = self.db.query_all_trades(
            {"symbol": symbol, "live": True}, {"orderId": 1, "_id": 0})

        return available_trades

    def send_tgmsg(self, side, price, quantity, profit=None):
        text = ""
        text += f"• Action: {side}\n"
        text += f"• Price: {price}\n"
        text += f"• Amount: {quantity}\n"

        if profit:
            text += f"• Profit: {profit["amount"]} ({profit["percent"]}%)"

        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)

        # loop.run_until_complete(self.tgbot.send_message(text))
        # loop.close()

        # msg_thread = threading.Thread(
        #     target=asyncio.run, args=(self.tgbot.send_message(text),))
        try:
            asyncio.run(self.tgbot.send_message(text))
        except:
            print("TG notfication error")

    def one_trade(self, orderId):
        tradeItem = self.db.query_one_trade({"orderId": orderId})
        if not tradeItem:
            print("Can't find trade with orderId {}".format(orderId))
            return

        buy_price = tradeItem["price"]
        pending_orderId = tradeItem["pendingOrder"]
        available_amount = tradeItem["availableAmount"]

        print(tradeItem)

        # trade parameters
        is_ordered_main = False
        sell_time_for_delay = None

        while self.running:
            latest_row = self.df_kline.iloc[-1]
            price = self.df_kline.iloc[-1]["Close"]
            # print(price, buy_price, orderId)

            if available_amount < 0.001:
                self.db.update_one_trade(
                    orderId, {"$set": {"availableAmount": 0.0, "pendingOrder": "", "live": False}})
                self.recently_ordered = True
                break

            if pending_orderId:
                pending_order = self.trade.get_order(
                    {"symbol": self.symbol, "orderId": pending_orderId})

                if pending_order["status"] == "CANCELED":
                    pending_orderId = ""

                    # update DB
                    self.db.update_one_trade(
                        orderId, {"$set": {"pendingOrder": ""}})

                elif pending_order["status"] == "FILLED":
                    available_amount = round(
                        available_amount - float(pending_order["origQty"]), 3)

                    # insert order
                    order_item = self.db.is_existing(
                        {"orderId": pending_orderId})
                    print(order_item)
                    if order_item:
                        pass
                    else:
                        params = {
                            "orderId": pending_orderId,
                            "side": "sell",
                            "price": pending_order["price"],
                            "quantity": pending_order["origQty"],
                            "last_price": buy_price,
                            "highest_price": self.highest_price,
                            "highest_time": self.highest_time,
                            "last_buy_price": buy_price
                        }
                        order_item = self.insert_order(**params)

                    # send tg message
                    self.send_tgmsg(
                        "SELL", order_item["price"], order_item["amount"], order_item["profit"])
                    pending_orderId = ""

                    if is_ordered_main:
                        is_ordered_main = False

                        self.db.update_one_trade(
                            orderId, {"$set": {"availableAmount": 0.0, "pendingOrder": "", "live": False}})

                        balance = self.get_balance()
                        print(balance)

                        print(f"One trade {orderId} has been finished.")
                        self.recently_ordered = True
                        break

                    if available_amount > 0.0:
                        print("continue pending")
                        # New Half pending order
                        pending_price = float(pending_order["price"]) * self.tp

                        if order_item["profit"]["percent"] >= 0.29 or available_amount < 0.002:
                            pending_quantity = available_amount
                        else:
                            pending_quantity = int(
                                available_amount * 500) / 1000

                        # trade limit order
                        response = self.trade_limit_order(
                            "sell", pending_price, pending_quantity)

                        if "orderId" in response.keys():
                            pending_orderId = response["orderId"]
                        else:
                            pending_orderId = ""

                        # update trade DB
                        self.db.update_one_trade(orderId, {"$set": {
                                                 "availableAmount": available_amount, "pendingOrder": pending_orderId}})

                    self.recently_ordered = True
            elif available_amount > 0.0:
                # New Half pending order
                print("New pending")
                pending_price = buy_price * self.tp

                if available_amount < 0.002:
                    pending_quantity = available_amount
                else:
                    pending_quantity = int(available_amount * 500) / 1000

                # trade limit order
                response = self.trade_limit_order(
                    "sell", pending_price, pending_quantity)
                print(response)

                if "orderId" in response.keys():
                    pending_orderId = response["orderId"]
                else:
                    pending_orderId = ""
                # print({"orderId": orderId}, {"$set": {"pendingOrder": pending_orderId}})

                # update trade DB
                self.db.update_one_trade(
                    orderId, {"$set": {"pendingOrder": pending_orderId}})

                self.recently_ordered = True

            # sell position
            if latest_row["EMA_diff"] < latest_row["EMA_signal"]:
                if not sell_time_for_delay:
                    sell_time_for_delay = time.time()
                    continue

                elif time.time() - sell_time_for_delay < 15:
                    continue
                else:
                    sell_time_for_delay = None

                # able to sell
                if price > buy_price * 1.00025:
                    if pending_orderId:
                        self.trade.delete_order(
                            {"symbol": self.symbol, "orderId": pending_orderId})
                    time.sleep(0.1)

                    response = self.focus_order(
                        symbol=self.symbol, side="sell", amount=available_amount, buy_price=buy_price)

                    # update trade DB
                    self.db.update_one_trade(
                        orderId, {"$set": {"availableAmount": 0.0, "pendingOrder": "", "live": False}})

                    # send TG message
                    self.send_tgmsg(
                        "SELL", response["price"], response["origQty"], response["profit"])

                    balance = self.get_balance()
                    print(response)
                    print(balance)

                    print(f"One trade {orderId} has been finished.")

                    available_amount = 0.0
                    self.recently_ordered = True
                    break
                # in case of price is lower
                else:
                    if not is_ordered_main:
                        if pending_orderId:
                            self.trade.delete_order(
                                {"symbol": self.symbol, "orderId": pending_orderId})

                        pending_price = buy_price * 1.00025
                        response = self.trade_limit_order(
                            "sell", pending_price, available_amount)

                        print(response)

                        # update trade DB
                        self.db.update_one_trade(
                            orderId, {"$set": {"pendingOrder": response["orderId"]}})
                        pending_orderId = response["orderId"]
                        is_ordered_main = True

                        self.recently_ordered = True
            else:
                sell_time_for_delay = None
            time.sleep(0.5)

    def start(self):

        last_condition = None

        self.highest_price = 0
        self.highest_time = None

        buy_time_for_delay = None

        trades = self.get_available_trades("BTCUSDT")

        # trade_thread.join()

        # response = self.focus_order(
        #     symbol=self.symbol, side="buy", amount=self.mtv, buy_price=self.get_current_price(self.symbol))

        # send message in TG
        # self.send_tgmsg(
        #     "BUY", "123123", "123123")
        # asyncio.run(self.tgbot.send_message("123123"))

        while self.running:
            try:
                self.df_kline = self.fetch_market(self.symbol)
                token = self.symbol.upper().split("USDT")[0]
                balance = self.get_balance()

                # trades = []
                if len(trades) > 0:
                    for trade in trades:
                        trade_thread = threading.Thread(
                            target=self.one_trade, args=(trade["orderId"], ))
                        trade_thread.start()

                    trades = []

                latest_row = self.df_kline.iloc[-1]
                price = self.df_kline.iloc[-1]["Close"]

                if price > self.highest_price:
                    utc_time = datetime.datetime.now(pytz.utc)
                    edt_zone = pytz.timezone('America/New_York')
                    current_datetime = utc_time.astimezone(edt_zone)

                    # Format the date and time to "MM/DD/YYYY HH:MM:SS"
                    formatted_datetime = current_datetime.strftime(
                        "%m/%d/%Y %H:%M:%S")
                    timestamp = current_datetime.timestamp()

                    self.highest_price = float(price)
                    self.highest_time = {
                        "stamp": timestamp,
                        "EDT": formatted_datetime
                    }

                # buy position
                if latest_row["EMA_diff"] > latest_row["EMA_signal"]:
                    if last_condition == "sell":
                        if price < latest_row["MA_10"] or price < latest_row["MA_5"]:
                            buy_time_for_delay = None
                            continue
                        if not buy_time_for_delay:
                            buy_time_for_delay = time.time()
                            continue

                        elif time.time() - buy_time_for_delay < 30:
                            continue
                        else:
                            buy_time_for_delay = None

                        # ajust trade amount
                        trade_amount = balance["USDT"]["free"]
                        ath = self.get_ATH(self.symbol)
                        if price > ath * 0.99:
                            # print("over ATH")
                            trade_amount = balance["USDT"]["free"] / 2

                        if trade_amount / price > 0.002:
                            print("buy")
                            response = self.focus_order(symbol=self.symbol, side="buy", amount=min(
                                self.mtv, trade_amount), buy_price=price)
                            # create one trade
                            self.db.insert_trade(
                                response["origQty"], response["orderId"], self.symbol, response["price"])
                            # send message in TG
                            self.send_tgmsg(
                                "BUY", response["price"], response["origQty"])

                            logging.info(balance)
                            print(response)

                            time.sleep(0.1)
                            trade_thread = threading.Thread(
                                target=self.one_trade, args=(response["orderId"], ))
                            trade_thread.start()

                            # self.last_buy_price = float(response["price"])

                            # # limit order for half
                            # half_price = response["price"] * self.tp
                            # half_quantity = int(response["origQty"] / 2 * 1000) / 1000
                            # response = self.trade_limit_order("sell", half_price, half_quantity)
                            # print(response)

                            # self.half_limit_id = response["orderId"]
                            # self.half_limit_status = "NEW"

                            # self.highest_price = 0
                            # self.highest_time = None

                    last_condition = "buy"
                else:                                                       # sell position
                    last_condition = "sell"
                    buy_time_for_delay = None
            except Exception as e:
                print(e)

            time.sleep(0.3)


# asyncio.run(websocket_client("BTCUSDT"))
# def runner():
#     bot = Bot()
#     bot.running = True
#     bot.start()

bot = Bot()
# print(bot.get_db_orders("BTCUSDT"))
print(bot.get_ATH("BTCUSDT"))
# print(bot.get_current_price("BTCUSDT"))
# bot.running = True
# bot_thread = threading.Thread(target=bot.start, daemon=True)

# bot_thread.start()
# while True:
#     time.sleep(3)
# bot.send_tgmsg("BUY", "123123", "123123")
