import pandas as pd
import datetime


def transform_data(tickers_response: dict, instruments_info_response: dict) -> pd.DataFrame:
    coins_info_dict = {}

    tickers = tickers_response["result"]["list"]
    instruments_info = instruments_info_response["result"]["list"]

    for row in tickers:
        coins_info_dict[row["symbol"]] = {
            "symbol": row["symbol"],
            "price24hPcnt": float(row["price24hPcnt"]),
            "volume24h": float(row["volume24h"]),
            "fundingRate": float(row["fundingRate"]),
            "openInterest": float(row["openInterest"])
        }
    
    for row in instruments_info:
        symbol = row["symbol"]
        if symbol in coins_info_dict:
            value = coins_info_dict[symbol]
            launch_time_unix_format = int(row["launchTime"])
            value["launchTime"] = datetime.datetime.fromtimestamp(launch_time_unix_format/1000)

    return pd.DataFrame(list(coins_info_dict.values()))
