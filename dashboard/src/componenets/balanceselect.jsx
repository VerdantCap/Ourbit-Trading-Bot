import React, { useState } from "react";
import Select from "react-select";

const options = [
  { value: "btcusdt", label: "BTC-USDT" },
  { value: "ethusdt", label: "ETH-USDT" },
  // { value: "solusdt", label: "SOL-USDT" },
];

const BalanceSelect = ({ availablesymbols, onChange }) => {
  const [selectedOption, setSelected] = useState(options[0]);
  // const availableoptions = availablesymbols.map((symbol) => {
  //   const baseCurrency = symbol.slice(0, -4);
  //   const label = `${baseCurrency}-USDT`;
  //   const value = symbol.toLowerCase();
  //   return { value: value, label: label };
  // });

  const handleChange = (e) => {
    setSelected(e);
    (selectedOption !== e) & onChange(e.value);
  };

  return (
    <Select
      defaultValue={selectedOption}
      onChange={handleChange}
      options={options}
    />
  );
};

export default BalanceSelect;
