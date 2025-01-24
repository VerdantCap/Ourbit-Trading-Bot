import React, { useState } from "react";
import axios from "axios";
import "./App.css";
import Chart from "./componenets/chart";
import MyTable from "./componenets/table";
import BalanceSelect from "./componenets/balanceselect";
import { Slider } from "primereact/slider";
import { InputText } from "primereact/inputtext";
import "primereact/resources/themes/lara-light-cyan/theme.css";

function App() {
  const [historicaldata, setHistoricalData] = useState();
  const [emadata, setEmaData] = useState();
  const [balancedata, setBalancelData] = useState([]);
  const [orderingdata, setOrderingData] = useState([]);
  const [symbol, setsymbol] = useState("btcusdt");
  const [availablesymbols, setAvailableSymbols] = useState([]);
  const [firstfetch, setFirstFetch] = useState(true);
  const [takeprofit, setTakeProfit] = useState(50);
  const [mbp, setMBP] = useState(0.0);
  const [msp, setMSP] = useState(0.0);
  const [mtv, setMtv] = useState();
  const [isrunning, setRunning] = useState(false);
  const [ispaused, setPaused] = useState(true);
  const [dailyprofitdata, setDailyProfitData] = useState([]);
  const [totalprofitdata, setTotalProfitData] = useState(null);
  const [tradesymbol, setTradeSymbol] = useState();
  const [trademtv, setTradeMtv] = useState();
  const [tradetakeprofit, setTradeTakeProfit] = useState();

  const bothosts = "http://23.27.125.35:5000";

  const fetchData = () => {
    const formdata = {
      symbol: symbol,
      firstfetch: firstfetch,
    };
    axios
      .post(`${bothosts}/api/post`, formdata)
      .then((res) => {
        // console.log(res);
        res.data.historical_data.length > 0 &&
          setHistoricalData(res.data.historical_data);
        res.data.emadata.length > 0 && setEmaData(res.data.emadata);
        res.data.balance && setBalancelData(res.data.balance);
        res.data.order_data && setOrderingData(res.data.order_data);
        res.data.daily_profit_data &&
          setDailyProfitData(res.data.daily_profit_data);
        res.data.total_profit_data &&
          setTotalProfitData(res.data.total_profit_data);
        res.data.available_symbols &&
          setAvailableSymbols(res.data.available_symbols);
        if (res.data.bot_running) {
          setRunning(true);
          setPaused(false);
        } else {
          setRunning(false);
          setPaused(true);
        }
        res.data.trade_symbol && setTradeSymbol(res.data.trade_symbol);
        res.data.trade_mtv && setTradeMtv(res.data.trade_mtv);
        res.data.trade_tp && setTradeTakeProfit(res.data.trade_tp);
      })
      .catch((error) => {
        console.error("There was an error!", error);
      });
  };

  //*
  React.useEffect(() => {
    setFirstFetch(true);
    fetchData();

    setFirstFetch(false);
    // Set up the interval to call the function every 15 seconds
    const interval = setInterval(fetchData, 1000);

    // Clear the interval on component unmount
    return () => clearInterval(interval);
  }, [firstfetch, symbol]);
  //*/

  const columns = React.useMemo(
    () => [
      {
        Header: "EDT",
        accessor: "time", // accessor is the "key" in the data
      },
      {
        Header: "Action",
        accessor: "action",
      },
      { Header: "Amount", accessor: "amount" },
      { Header: "Status", accessor: "status" },
      { Header: "Profit (USD)", accessor: "profit" },
      {
        Header: "Price",
        accessor: "price",
      },
    ],
    []
  );

  const balancecolumns = React.useMemo(() => [
    { Header: "Symbol", accessor: "symbol" },
    { Header: "Free", accessor: "free" },
    { Header: "Locked", accessor: "locked" },
  ]);

  const dailyprofitcolumns = React.useMemo(() => [
    { Header: "EDT Date", accessor: "date" },
    { Header: "Profit", accessor: "profit" },
    { Header: "Trades", accessor: "trades" },
  ]);

  const manualbuy = () => {
    if (
      !mbp ||
      mbp < historicaldata[historicaldata.length - 1]["price"] * 0.001
    ) {
      alert("Please enter a buy amount of 1 BTC or more.");
    }
    axios
      .post(`${bothosts}/api/manualbuy`, { symbol: symbol, mbp: mbp })
      .then((res) => {
        console.log(res);
        if (res.data.status == 500) alert("Successfully ordered!");
        else if (res.data.status == 400) alert("Invalid Requests");
        else alert("Order has been failed");
      })
      .catch((error) => {
        console.error("There was an error!", error);
      });
  };

  const manualsell = () => {
    if (!msp || msp <= 0) {
      alert("Please enter a sell amount of 0 or more.");
    }
    axios
      .post(`${bothosts}/api/manualsell`, { symbol: symbol, msp: msp })
      .then((res) => {
        console.log(res);
        if (res.data.status == 500) alert("Successfully ordered!");
        else if (res.data.status == 400) alert("Invalid Requests");
        else alert("Order has been failed");
      })
      .catch((error) => {
        console.error("There was an error!", error);
      });
  };

  const submittp = () => {
    axios
      .post(`${bothosts}/api/submittp`, { tp: takeprofit })
      .then((res) => {
        console.log(res);
        if (res.data.status == 500) alert("Successfully updated!");
        else if (res.data.status == 400) alert("Invalid Requests");
        else alert("Order has been failed");
      })
      .catch((error) => {
        console.error("There was an error!", error);
      });
  };

  const runbot = () => {
    if (!mtv || mtv < 20) {
      alert("Please enter a maximum transaction volume of 20 or more.");
    } else {
      setRunning(true);
      setPaused(true);
      axios
        .post(`${bothosts}/api/runtrade`, { symbol: symbol, mtv: mtv })
        .then((res) => {
          console.log(res);
          alert("bot started");
        })
        .catch((error) => {
          console.error("There was an error!", error);
        });
    }
  };

  const pausebot = () => {
    setRunning(true);
    setPaused(true);
    axios
      .post(`${bothosts}/api/pasuetrade`, { mtv: mtv })
      .then((res) => {
        console.log(res);
        alert("bot paused");
      })
      .catch((error) => {
        console.error("There was an error!", error);
      });
  };

  const downloaddata = async () => {
    const response = await fetch(`${bothosts}/api/downloaddata`);
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = "order_data.csv"; // Suggested filename for saving
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  return (
    <div className="tradeboard">
      <div className="controlpanel">
        <BalanceSelect
          availablesymbols={availablesymbols}
          onChange={(e) => {
            setsymbol(e);

            setFirstFetch(true);
            fetchData();
            // setFirstFetch(false);
          }}
        />
        <hr />
        <div className="portfolio">
          <MyTable
            columns={balancecolumns}
            data={balancedata}
            hiddenpage={true}
          />
        </div>
        <hr />
        <div className="manual control panel" style={{ display: "flex" }}>
          <div>
            <input
              name="manual buy price"
              type="number"
              style={{ fontSize: 14, height: 25, width: "90%" }}
              value={mbp}
              onChange={(e) => {
                setMBP(e.target.value);
              }}
            ></input>
            <button
              name="bt manual buy"
              style={{ marginTop: "5px", width: "90%", background: "#00ccff" }}
              onClick={manualbuy}
            >
              BUY
            </button>
          </div>
          <div>
            <input
              name="manual sell price"
              type="number"
              style={{ fontSize: 14, height: 25, width: "90%" }}
              value={msp}
              onChange={(e) => {
                setMSP(e.target.value);
              }}
            ></input>
            <button
              name="bt manual sell"
              style={{ marginTop: "5px", width: "90%", background: "#ffcc00" }}
              onClick={manualsell}
            >
              SELL
            </button>
          </div>
        </div>
        <hr />
        <div className="bot control panel">
          <div
            style={{ fontSize: "14px" }}
            hidden={ispaused}
            clasasName="botStatus"
          >
            Bot is running on {tradesymbol} with ${trademtv}, TP{" "}
            {tradetakeprofit}%
          </div>
          <div
            style={{ marginBottom: "10px", textAlign: "left" }}
            className="w-full"
          >
            Take profit Rate: {takeprofit / 100}%
            <Slider
              style={{ width: "100%", marginTop: "5px", marginBottom: "10px" }}
              value={takeprofit}
              onChange={(e) => setTakeProfit(e.value)}
              className="w-full"
              // step={20}
            />
            <button
              style={{ width: "100%", background: "#00ccff" }}
              id="submit"
              onClick={submittp}
            >
              Submit TP Rate
            </button>
          </div>
          <input
            type="number"
            style={{ fontSize: 14, height: 25, width: "90%" }}
            value={mtv}
            disabled={isrunning}
            onChange={(e) => {
              setMtv(e.target.value);
            }}
            placeholder="Max trading volume"
          ></input>
          <div className="buttongroup">
            <button
              style={{ width: "48%", background: "#00ccff" }}
              id="startbutton"
              onClick={runbot}
              disabled={isrunning}
            >
              Start
            </button>
            <button
              style={{ width: "48%", background: "#ffcc00" }}
              id="pausebutton"
              onClick={pausebot}
              disabled={ispaused}
            >
              Pause
            </button>
          </div>
        </div>
        <hr />
        <div className="profit panel">
          <div
            style={{ textAlign: "left", fontSize: "18px", marginBottom: "5px" }}
          >
            <div>
              Total profit (USD): {totalprofitdata && totalprofitdata["profit"]}
            </div>
            <div>
              Total Trades: {totalprofitdata && totalprofitdata["trades"]}
            </div>
          </div>
          <MyTable
            columns={dailyprofitcolumns}
            data={dailyprofitdata}
            hiddenpage={true}
          />
        </div>
      </div>
      <div className="dashboard">
        <div className="currentprice">
          Current Price: $
          {historicaldata &&
            historicaldata[historicaldata.length - 1]["price"].toLocaleString(
              "en-US",
              { minimumFractionDigits: 2, maximumFractionDigits: 2 }
            )}
        </div>
        <Chart
          historicaldata={historicaldata}
          keys={["MA5", "MA10"]}
          height={400}
        />
        <Chart
          style={{ height: "200" }}
          historicaldata={emadata}
          keys={["ema", "signal"]}
          height={200}
        />
        <MyTable
          columns={columns}
          data={orderingdata}
          coloredstatus={"FILLED"}
          hiddenpage={false}
          onclick={downloaddata}
        />
      </div>
    </div>
  );
}

export default App;
