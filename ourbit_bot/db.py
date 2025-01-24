from pymongo import MongoClient
import certifi
import os
import dotenv
import random
from datetime import datetime, timedelta

dotenv.load_dotenv(".env", override=True)


def generate_random_data(num_documents):
    symbols = ['btcusdt', 'ethusdt', 'solusdt']
    actions = ['buy', 'sell']
    data_list = []

    for _ in range(num_documents):
        # Create random date and time
        random_minutes = random.randint(0, 4320)  # Total minutes in a year
        random_second = random.randint(0, 59)  # Second granularity
        random_date = datetime.now() - timedelta(minutes=random_minutes, seconds=random_second)
        # Use zero-padded month and day for compatibility
        date_str = random_date.strftime('%m/%d/%Y %H:%M:%S')
        # date_str = date_str.lstrip("0").replace(
        #     "/0", "/")  # Remove leading zeros manually

        stamp_str = str(int(random_date.timestamp()))

        doc = {
            "time": {
                "stamp": stamp_str,
                "EDT": date_str
            },
            "orderID": str(random.randint(100000, 999999)),
            "symbol": random.choice(symbols),
            "action": random.choice(actions),
            "amount": round(random.uniform(0.005, 0.02), 3),
            "price": round(random.uniform(100000, 200000), 2),
            "profit": {
                "amount": round(random.uniform(10, 20), 1),
                "percent": round(random.uniform(0.05, 0.15), 2)
            }
        }

        data_list.append(doc)

    return data_list


class MGDB:
    def __init__(self):
        # Connect MongoDB
        self.client = MongoClient(
            os.getenv("MONGO_URI"),
            maxPoolSize=20,
            minPoolSize=1,
            tlsCAFile=certifi.where()
        )

        self.db = self.client["ourbit_bot"]

    def update_metadata(self, symbol, profit):
        if not isinstance(symbol, str):
            raise TypeError("symbol must be a str")
        if not isinstance(profit, float):
            raise TypeError("profit must be a float")

        # update specific symbol
        if self.db["metadata"].count_documents({"symbol": symbol}) > 0:
            current_ele = self.db["metadata"].find_one({"symbol": symbol})

            query = {"_id": current_ele["_id"]}
            new_values = {"$set": {"profit": current_ele["profit"] +
                                   profit, "trades": current_ele["trades"]+1}}
            result = self.db["metadata"].update_one(query, new_values)
            print(result)
        else:
            self.db["metadata"].insert_one({
                "symbol": symbol,
                "profit": profit,
                "trades": 1,
            })

    def get_total_metadata(self):
        pipeline = [
            {
                "$match": {"profit": {"$exists": True}, "trades": {"$exists": True}}
            },
            {
                "$group": {
                    "_id": None,  # Grouping by 'None' means all documents treated as a single group
                    # Sum the 'profit' field from all documents
                    "total_profit": {"$sum": "$profit"},
                    "total_trades": {"$sum": "$trades"}
                }
            }
        ]

        # Execute the aggregation pipeline
        result = self.db["metadata"].aggregate(pipeline)

        # Print results
        for doc in result:
            return {"profit": doc["total_profit"], "trades": doc["total_trades"]}

    def get_metadata(self):
        pipeline = [
            {
                # Filter the documents to include only "sell" actions
                "$match": {
                    "action": "sell"
                }
            },
            {
                "$project": {
                    "profit_amount": "$profit.amount",
                    # Extracting date portion (assuming MM/DD/YYYY)
                    "date": {"$substr": ["$time.EDT", 0, 10]},
                    # "price": 1  # Keep price field for subsequent summation
                }
            },
            {
                "$group": {
                    "_id": "$date",  # Grouping by date
                    # Summing price for each group
                    "profit": {"$sum": "$profit_amount"},
                    "trades": {"$sum": 1}  # Counting documents in each group
                }
            },
            {
                "$sort": {"_id": -1}
            }
        ]

        result = self.db["orders"].aggregate(pipeline)

        metadata = {
            "daily_metadata": [],
            "total_metadata": {
                "profit": 0,
                "trades": 0
            }
        }
        for doc in result:
            metadata["daily_metadata"].append(doc)
            metadata["total_metadata"]["profit"] += doc["profit"]
            metadata["total_metadata"]["trades"] += doc["trades"]
        return metadata

    def insert_order(self, time, orderId, symbol, status, action, amount, price, profit=None, hp=None):
        if not isinstance(time, dict):
            raise TypeError("time must be a dict")
        if not isinstance(orderId, str):
            raise TypeError("orderID must be a dict")
        if not isinstance(symbol, str):
            raise TypeError("symbol must be a dict")
        if not isinstance(status, str):
            raise TypeError("status must be a dict")
        if not isinstance(action, str):
            raise TypeError("action must be a str")
        if not isinstance(amount, float):
            raise TypeError("amount must be a float")
        if not isinstance(price, float):
            raise TypeError("price must be a float")
        if profit and not isinstance(profit, dict):
            raise TypeError("profit must be a dict")
        if hp and not isinstance(hp, dict):
            raise TypeError("profit must be a dict")
        # if profit and not isinstance(profit, dict):
        #     raise TypeError("profit must be a dict")

        response = self.db["orders"].insert_one({
            "time": time,
            "orderId": orderId,
            "symbol": symbol,
            "status": status,
            "action": action,
            "amount": amount,
            "price": price,
            "profit": profit,
            "highest price": hp
        })
        return response

    def insert_random_orders(self, num_orders):
        random_data = generate_random_data(num_orders)
        self.db["test_orders"].insert_many(random_data)

    def update_status(self, orderId, status):
        self.db["orders"].update_one({"orderId": orderId, "status": {"$ne": status}}, {"$set": {"status": status}})

    def is_existing(self, query):
        response = self.db["orders"].find_one(query)
        if response:
            return response
        else:
            return False

    def find_orders(self, query):
        return list(self.db["orders"].find(query))

    def get_orders_by_symbol(self, symbol):
        query = {"symbol": symbol}

        sorted_orders = self.db["orders"].find(
            query).sort("time.stamp", -1)

        return list(sorted_orders)
    
    def query_orders(self, query):
        sorted_orders = self.db["orders"].find(
            query).sort("time.stamp", -1)

        return list(sorted_orders)

    def insert_trade(self, initialAmount, orderId, symbol, price):
        try:
            response = self.db["trades"].insert_one({
                "initialAmount": initialAmount,
                "availableAmount": initialAmount,
                "orderId": orderId,
                "symbol": symbol,
                "price": price,
                "pendingOrder": "",
                "live": True
            })

            return response
        except:
            False

    def query_one_trade(self, query):
        response = self.db["trades"].find_one(query)
        if response:
            return response
        else:
            return False
    
    def query_all_trades(self, query, project=None):
        response = self.db["trades"].find(query, project)
        if response:
            return list(response)
        else:
            return False
        
    def update_one_trade(self, orderId, query):
        self.db["trades"].update_one({"orderId": orderId}, query)



db = MGDB()
# print(db.is_existing({"orderId": "C01__454312489119657985"}))
# print(db.update_one_trade("C01__454843006269276161", {"$set": {"pendingOrder": "C01__454844619499253761"}}))
# # db.insert_random_orders(20)
# print(db.get_metadata())
# print(db.get_orders_by_symbol("btcusdt"))
# print(generate_random_data(20))

# db.update_metadata("solusdt", 3.0)
# print(db.get_total_metadata())
# print(db.get_daily_metada())
# print(db.db["metadata"])
# params = {
#     "time": {"stamp": "323114", "EDT": "8/9/2024 02:04"},
#     "orderID": "124524",
#     "symbol": "btcusdt",
#     "action": "sell",
#     "amount": 0.017,
#     "price": 123123.0,
#     "profit": {"amount": 12.1, "percent": 0.1}
# }
# db.insert(**params)
