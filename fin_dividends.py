import argparse
from pathlib import Path
from datetime import datetime, timedelta
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


def download_dividends(ticker_input: str, start_month_input: str):
    yf_symbol = ticker_input.strip()
    output_filename = f"{yf_symbol}_dividends.txt"

    start_date = parse_month_string(start_month_input)
    start_dt = pd.to_datetime(start_date)

    # Always run through today, not a hardcoded end date
    today = datetime.now()
    end_date_str = today.strftime("%Y-%m-%d")

    print(f"Connecting to Yahoo Finance for '{yf_symbol}'...")
    print(f"Target Range: {start_date} through {end_date_str} (all ex-dividend dates and amounts)")

    ticker_obj = yf.Ticker(yf_symbol)

    # ticker.dividends returns a pandas Series indexed by ex-dividend date (tz-aware),
    # values are the per-unit dividend/distribution amount in the counter's native currency.
    div_series = ticker_obj.dividends

    if div_series.empty:
        print(f"Error: No dividend/distribution data found for '{yf_symbol}'. Verify ticker symbol.")
        sys.exit(1)

    df = div_series.reset_index()
    df.columns = ["Date", "Dividend"]

    # Normalize to tz-naive dates for comparison/output
    df["Date_dt"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    df = df.sort_values("Date_dt").reset_index(drop=True)

    # Filter to the requested window: start_month's 1st day through today
    mask = (df["Date_dt"] >= start_dt) & (df["Date_dt"] <= pd.Timestamp(today))
    df_filtered = df.loc[mask].copy()

    if df_filtered.empty:
        print(f"Error: No dividend/distribution rows found for '{yf_symbol}' in the range "
              f"{start_date} to {end_date_str}.")
        sys.exit(1)

    df_filtered["Date"] = df_filtered["Date_dt"].dt.strftime("%Y-%m-%d")
    df_final = df_filtered[["Date", "Dividend"]]

    output_path = save_output(df_final, output_filename)

    print(f"SUCCESS: Saved {len(df_final)} dividend/distribution rows to '{output_path}'")
    print(f"Verified Date Range: {df_final['Date'].iloc[0]} to {df_final['Date'].iloc[-1]}")
    print(f"Total dividends/distributions in range: {df_final['Dividend'].sum():.6f} per unit")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch historical dividend/distribution data (ex-dividend date and per-unit amount) "
                    "from Yahoo Finance, from the given start month through today."
    )
    parser.add_argument(
        "ticker",
        type=str,
        help="Exact ticker symbol (e.g., CLR.SI, CFA.SI, ES3.SI)",
    )
    parser.add_argument(
        "start_month",
        type=str,
        help="Starting month in format Month-YYYY (e.g., July-2019 or Jul-2019). "
             "Dividends are returned from the 1st day of this month through today.",
    )

    args = parser.parse_args()
    download_dividends(args.ticker, args.start_month)


if __name__ == "__main__":
    main()