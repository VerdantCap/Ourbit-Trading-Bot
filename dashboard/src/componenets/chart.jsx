import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Label,
} from "recharts";

// const data = [
//   { time: 'A', price: 400, MA50: 240, MA200: 100 },
//   { time: 'B', price: 600, MA50: 480, MA200: 480 },
//   { time: 'C', price: 800, MA50: 360, MA200: 240 },
//   { time: 'D', price: 1000, MA50: 800, MA200: 990 },
//   { time: 'E', price: 1200, MA50: 540, MA200: 760 },
//   { time: 'F', price: 1400, MA50: 960, MA200: 640 },
//   { time: 'G', price: 1600, MA50: 780, MA200: 840 },
//   { time: 'H', price: 1800, MA50: 620, MA200: 680 },
// ]

const Chart = ({ historicaldata, keys, height }) => {
  return (
    <LineChart
      // width={window.innerWidth * 0.8}
      width={1000}
      height={height}
      data={historicaldata}
      style={{
        marginLeft: "auto",
        marginRight: "auto",
      }}
    >
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis
        style={{
          fontSize: "12px",
        }}
        dataKey="time"
        tickFormatter={(unixTime) => {
          const date = new Date(unixTime);
          return `${date.getMonth() + 1}/${date.getDate()}/${date
            .getFullYear()
            .toString()
            .substr(-2)} ${date.getHours()}:${date.getMinutes()}`;
        }}
      />
      <YAxis
        style={{
          fontSize: "12px",
        }}
        domain={["auto", "auto"]}
        tickFormatter={(value) =>
          `$${value.toLocaleString("en-US", {
            // minimumFractionDigits: 2,
            // maximumFractionDigits: 2,
          })}`
        }
      />
      <Tooltip />
      <Legend />
      <Line
        type="monotone"
        dataKey="price"
        stroke="#8884d8"
        activeDot={{ r: 8 }}
      />
      <Line type="monotone" dataKey={keys[0]} stroke="#ffc658" />
      <Line type="monotone" dataKey={keys[1]} stroke="#82ca9d" />
    </LineChart>
  );
};

export default Chart;
