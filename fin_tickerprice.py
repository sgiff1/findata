import argparse
from pathlib import Path
from datetime import datetime
import sys
import pandas as pd
import yfinance as yf


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def save_output(df, filename: str) -> Path:
    """Write df as CSV into the 'outputs' folder next to this script (created if missing; existing file overwritten)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename
    try:
        df.to_csv(output_path, index=False)
    except PermissionError:
        print(f"Error: Cannot write '{output_path}'. The file may be open in another program (e.g. Excel). Close it and run again.")
        sys.exit(1)
    return output_path


def parse_month_string(month_str: str) -> str:
    """Parses a string like 'July-2019' or 'Jul-2019' into '2019-07-01'."""
    cleaned_str = month_str.strip()
    for fmt in ("%B-%Y", "%b-%Y"):
        try:
            dt = datetime.strptime(cleaned_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    print(
        f"Error: Invalid start month format '{month_str}'. Expected format like 'July-2019' or 'Jul-2019'."
    )
    sys.exit(1)


def download_data(ticker_input: str, start_month_input: str, mode: str):
    yf_symbol = ticker_input.strip()
    output_filename = f"{yf_symbol}_{mode}.txt"

    start_date = parse_month_string(start_month_input)

    # "to-date": always run through today, not a hardcoded end date
    from datetime import timedelta
    today = datetime.now()
    end_date_str = today.strftime("%Y-%m-%d")
    end_dt_exclusive = (today + timedelta(days=1)).strftime("%Y-%m-%d")  # yfinance 'end' is exclusive

    print(f"Connecting to Yahoo Finance for '{yf_symbol}'...")
    if mode == "monthly":
        print(
            f"Target Range: {start_date} through {end_date_str} (Extracting strictly the 1st trading day of each month)"
        )
    else:
        print(
            f"Target Range: {start_date} through {end_date_str} (Extracting every trading day)"
        )

    ticker_obj = yf.Ticker(yf_symbol)

    df = ticker_obj.history(
        start=start_date, end=end_dt_exclusive, auto_adjust=False
    )

    if df.empty:
        print(f"Error: No data found for '{yf_symbol}'. Verify ticker symbol.")
        sys.exit(1)

    # Format Date column and ensure datetime type for strict chronological sorting
    df.reset_index(inplace=True)
    df["Date_dt"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date_dt").reset_index(drop=True)

    if mode == "monthly":
        df["YearMonth"] = df["Date_dt"].dt.to_period("M")
        # Filter to keep ONLY the absolute earliest trading row for each calendar month
        df_filtered = df.groupby("YearMonth", sort=True).first().reset_index(drop=True)
    else:
        # daily: keep every trading day as-is
        df_filtered = df

    # Standardize Date string representation
    df_filtered["Date"] = pd.to_datetime(df_filtered["Date"]).dt.strftime("%Y-%m-%d")

    # Retain standard price columns
    cols = [
        "Date",
        "Open",
        "High",
        "Low",
        "Close",
        "Adj Close",
        "Volume",
    ]
    existing_cols = [c for c in cols if c in df_filtered.columns]
    df_final = df_filtered[existing_cols]

    # Save to .txt file in CSV format
    output_path = save_output(df_final, output_filename)

    label = "monthly rows (1st trading day of each month)" if mode == "monthly" else "daily trading rows"
    print(f"SUCCESS: Saved {len(df_final)} {label} to '{output_path}'")
    print(f"Verified Date Range: {df_final['Date'].iloc[0]} to {df_final['Date'].iloc[-1]}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch pricing data (monthly: 1st trading day of each month only, or daily: every trading day) from Yahoo Finance, from the given start month through today."
    )
    parser.add_argument(
        "ticker",
        type=str,
        help="Exact ticker symbol (e.g., NIFTYBEES.NS, MID150BEES.NS, GOLDBEES.NS)",
    )
    parser.add_argument(
        "start_month",
        type=str,
        help="Starting month in format Month-YYYY (e.g., July-2019 or Jul-2019). Data starts from the 1st trading day of this month.",
    )
    parser.add_argument(
        "mode",
        type=str,
        choices=["monthly", "daily"],
        help="'monthly' = only the 1st trading day of each month; 'daily' = every trading day, from the start month's 1st trading day through the last trading day to-date.",
    )

    args = parser.parse_args()
    download_data(args.ticker, args.start_month, args.mode)


if __name__ == "__main__":
    main()
