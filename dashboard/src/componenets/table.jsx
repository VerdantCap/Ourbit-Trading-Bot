import React, { useEffect, useState } from "react";
import { useTable, useSortBy, useFilters, usePagination } from "react-table";
import "./table.css";

function DefaultColumnFilter({
  column: { filterValue, preFilteredRows, setFilter },
}) {
  const count = preFilteredRows.length;

  return (
    <input
      value={filterValue || ""}
      onChange={(e) => {
        setFilter(e.target.value || undefined);
      }}
      placeholder={`Search ${count} records...`}
    />
  );
}

function MyTable({ columns, data, hiddenpage, coloredstatus, onclick }) {
  const filterTypes = React.useMemo(
    () => ({
      text: (rows, id, filterValue) => {
        return rows.filter((row) => {
          const rowValue = row.values[id];
          return rowValue !== undefined
            ? String(rowValue)
                .toLowerCase()
                .startsWith(String(filterValue).toLowerCase())
            : true;
        });
      },
    }),
    []
  );

  const defaultColumn = React.useMemo(
    () => ({
      Filter: DefaultColumnFilter,
    }),
    []
  );

  const [recoverpageIndex, setrecoverpageIndex] = useState(0);

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    page,
    prepareRow,
    canPreviousPage,
    canNextPage,
    pageOptions,
    pageCount,
    gotoPage,
    nextPage,
    previousPage,
    setPageSize,
    state: { pageIndex, pageSize },
  } = useTable(
    {
      columns,
      data,
      defaultColumn,
      filterTypes,
      initialState: { pageIndex: recoverpageIndex },
    },
    useFilters,
    useSortBy,
    usePagination
  );

  useEffect(() => {
    setrecoverpageIndex(pageIndex);
  }, [pageIndex]);

  useEffect(() => {
    setrecoverpageIndex(pageIndex);
  }, [pageIndex]);

  return (
    <div>
      <table
        {...getTableProps()}
        style={{
          // border: isborder && "solid 1px blue",
          marginLeft: "auto",
          marginRight: "auto",
          width: "80%",
          color: "black",
        }}
      >
        <thead>
          {headerGroups.map((headerGroup) => (
            <tr {...headerGroup.getHeaderGroupProps()}>
              {headerGroup.headers.map((column) => (
                <th>
                  {column.render("Header")}
                  {/* {column.isSorted
                                        ? column.isSortedDesc
                                            ? ' 🔽'
                                            : ' 🔼'
                                        : ''}
                                    <div>{column.canFilter ? column.render('Filter') : null}</div> */}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody {...getTableBodyProps()}>
          {page.map((row) => {
            prepareRow(row);

            // Make sure `row.original` is used to access the row data for conditions
            let rowClassName = "gray-row";
            if (
              row.original.status === coloredstatus &&
              row.original.profit &&
              row.original.profit.startsWith("$")
            )
              rowClassName = "green-row";
            else if (
              row.original.status === coloredstatus &&
              row.original.profit &&
              row.original.profit.startsWith("-")
            )
              rowClassName = "red-row";
            return (
              <tr
                {...row.getRowProps()}
                className={rowClassName}
                style={{ border: "solid 1px gray" }}
              >
                {row.cells.map((cell) => (
                  <td {...cell.getCellProps()}>{cell.render("Cell")}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
      <div
        className="pagination"
        hidden={hiddenpage}
        style={{ marginLeft: "auto", marginRight: "auto", marginTop: "10px" }}
      >
        <button onClick={() => gotoPage(0)} disabled={!canPreviousPage}>
          {"<<"}
        </button>{" "}
        <button onClick={() => previousPage()} disabled={!canPreviousPage}>
          {"<"}
        </button>{" "}
        <button onClick={() => nextPage()} disabled={!canNextPage}>
          {">"}
        </button>{" "}
        <button onClick={() => gotoPage(pageCount - 1)} disabled={!canNextPage}>
          {">>"}
        </button>{" "}
        <span>
          Page{" "}
          <strong>
            {pageIndex + 1} of {pageOptions.length}
          </strong>{" "}
        </span>
        <span>
          | Go to page:{" "}
          <input
            type="number"
            defaultValue={pageIndex + 1}
            onChange={(e) => {
              const page = e.target.value ? Number(e.target.value) - 1 : 0;
              gotoPage(page);
            }}
            style={{ width: "100px" }}
          />
        </span>{" "}
        <select
          value={pageSize}
          onChange={(e) => {
            setPageSize(Number(e.target.value));
          }}
        >
          {[10, 20, 30, 40, 50].map((pageSize) => (
            <option key={pageSize} value={pageSize}>
              Show {pageSize}
            </option>
          ))}
        </select>{" "}
        <button onClick={onclick}>download</button>
      </div>
    </div>
  );
}

export default MyTable;
