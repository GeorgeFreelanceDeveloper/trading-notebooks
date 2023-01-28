import yaml
import pandas as pd

DEFAULT_PRICE_SCALE = 2


def load_config(config_file: str) -> dict:
    with open(config_file, 'r') as stream:
        try:
            parsed_yaml = yaml.safe_load(stream)
            return parsed_yaml
        except yaml.YAMLError as exc:
            print(exc)


def transform_positions(positions_raw: dict) -> pd.DataFrame:
    result = []

    for position in positions_raw["result"]:
        result.append(position["data"])

    return pd.DataFrame(result)


def parse_active_positions(positions: pd.DataFrame, instruments_info: pd.DataFrame):
    active_positions = positions[positions["position_value"] > 0]
    active_positions["price_scale"] = active_positions.apply(
        lambda row: __parse_price_scale(instruments_info, row["symbol"]), axis=1)

    if not active_positions.empty:
        active_positions["compute_trailing_stop"] = active_positions.apply(
            lambda x: round(x["compute_trailing_stop"], x["price_scale"]), axis=1)
            
    return active_positions


def place_trailing_stops(active_positions: pd.DataFrame, exchange) -> pd.DataFrame:
    # TODO: check please
    response = []

    for index, active_position in active_positions.iterrows():
        if __is_active_trailing_stop(active_position):
            continue

        try:
            exchange.set_trading_stop(
                symbol=active_position["symbol"],
                side=active_position["side"],
                trailing_stop=active_position["compute_trailing_stop"]
            )
            response.append(
                {"symbol": active_position["symbol"], "status": "OK"})
        except Exception as e:
            print(e)
            response.append(
                {"symbol": active_position["symbol"], "status": "ERROR"})

    return pd.DataFrame(response)


def __is_active_trailing_stop(position):
    # TODO: check please
    return position["trailing_stop"] > 0


def __parse_price_scale(instruments_info: dict, ticker: str) -> float:
    instruments_info_list = instruments_info["result"]["list"]
    price_scale = [x["priceScale"]
                   for x in instruments_info_list if x["symbol"] == ticker]
    return int(price_scale[0]) if any(price_scale) else DEFAULT_PRICE_SCALE
