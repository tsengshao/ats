from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd


DATE_OUTPUT_FORMAT = "%d%b%Y"
DATE_INPUT_FORMAT = "%d%b%Y"
TIME_COLUMN_CANDIDATES = ("time", "date", "datetime")


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y"}:
        return True
    if normalized in {"0", "false", "f", "no", "n"}:
        return False
    raise ValueError(f"Cannot parse boolean value: {value}")


def _coerce_condition_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    text = value.strip()
    if not text:
        return text

    lower = text.lower()
    if lower in {"true", "false", "t", "f", "yes", "no", "y", "n", "0", "1"}:
        return _parse_bool(text)

    try:
        return int(text)
    except ValueError:
        pass

    try:
        return float(text)
    except ValueError:
        pass

    return text


def _resolve_time_column(df: pd.DataFrame, time_column: str | None) -> str:
    if time_column is not None:
        if time_column not in df.columns:
            raise KeyError(f"Column '{time_column}' not found in csv.")
        return time_column

    for candidate in TIME_COLUMN_CANDIDATES:
        if candidate in df.columns:
            return candidate

    raise KeyError(
        "Cannot find time column. Please specify time_column explicitly."
    )


def _normalize_filter_columns(filters: dict[str, Any] | None) -> dict[str, Any]:
    if not filters:
        return {}

    normalized = {}
    for key, value in filters.items():
        normalized_key = "diurnal_rain" if key == "diurnal" else key
        normalized[normalized_key] = _coerce_condition_value(value)
    return normalized


def select_dates_from_csv(
    csv_path: str | Path,
    filters: dict[str, Any] | None = None,
    query: str | None = None,
    time_column: str | None = None,
) -> pd.DatetimeIndex:
    df = pd.read_csv(csv_path)
    resolved_time_column = _resolve_time_column(df, time_column)
    normalized_filters = _normalize_filter_columns(filters)

    mask = pd.Series(True, index=df.index)
    for column, expected in normalized_filters.items():
        if column not in df.columns:
            raise KeyError(f"Column '{column}' not found in csv.")
        series = df[column]
        if isinstance(expected, bool):
            mask &= series.map(lambda value: _coerce_condition_value(value) == expected)
        else:
            mask &= series == expected

    if query:
        query_mask = df.eval(query)
        if getattr(query_mask, "dtype", None) != bool:
            raise ValueError(f"Query must return boolean results: {query}")
        mask &= query_mask

    selected = pd.to_datetime(df.loc[mask, resolved_time_column])
    return pd.DatetimeIndex(selected.sort_values().unique(), name=resolved_time_column)


def write_selected_dates(
    dates: pd.Series | pd.DatetimeIndex | list[Any],
    output_path: str | Path,
    start_index: int = 1,
    date_format: str = DATE_OUTPUT_FORMAT,
) -> Path:
    date_index = pd.DatetimeIndex(pd.to_datetime(list(dates))).sort_values().unique()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"{idx} {date.strftime(date_format)}"
        for idx, date in enumerate(date_index, start=start_index)
    ]
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return output


def export_selected_dates(
    csv_path: str | Path,
    output_path: str | Path,
    filters: dict[str, Any] | None = None,
    query: str | None = None,
    time_column: str | None = None,
    start_index: int = 1,
) -> pd.DatetimeIndex:
    selected_dates = select_dates_from_csv(
        csv_path=csv_path,
        filters=filters,
        query=query,
        time_column=time_column,
    )
    write_selected_dates(
        dates=selected_dates,
        output_path=output_path,
        start_index=start_index,
    )
    return selected_dates


def read_selected_dates(
    txt_path: str | Path,
    date_format: str = DATE_INPUT_FORMAT,
) -> pd.DatetimeIndex:
    txt_file = Path(txt_path)
    dates = []
    for raw_line in txt_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ValueError(f"Invalid selected_date line: {raw_line}")
        dates.append(pd.to_datetime(parts[-1], format=date_format))
    return pd.DatetimeIndex(dates, name="selected_date")


def _parse_cli_filters(filter_args: list[str]) -> dict[str, Any]:
    filters = {}
    for item in filter_args:
        if "=" not in item:
            raise ValueError(f"Filter must use key=value format: {item}")
        key, value = item.split("=", 1)
        filters[key.strip()] = value.strip()
    return filters


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select dates from a weather csv and export selected_date txt."
    )
    parser.add_argument("csv_path", help="Input csv path")
    parser.add_argument("output_path", help="Output txt path")
    parser.add_argument(
        "--filter",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Equality filter, e.g. --filter wtype=other --filter diurnal=true",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Additional pandas eval query, e.g. \"tc_ivt_max > 500\"",
    )
    parser.add_argument(
        "--time-column",
        default=None,
        help="Time column name. Default tries time/date/datetime.",
    )
    args = parser.parse_args()

    selected_dates = export_selected_dates(
        csv_path=args.csv_path,
        output_path=args.output_path,
        filters=_parse_cli_filters(args.filter),
        query=args.query,
        time_column=args.time_column,
    )
    print(f"Wrote {len(selected_dates)} dates to {args.output_path}")


if __name__ == "__main__":
    main()
