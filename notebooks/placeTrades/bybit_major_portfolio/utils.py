import yaml
import pandas as pd
import os
import datetime

MIN_LEVERAGE = 1
DEFAULT_PRICE_SCALE = 2
ACCOUNT_TYPE = "bybitMajorAccount"


def load_config(config_file: str) -> dict:
    with open(config_file, 'r') as stream:
        try:
            parsed_yaml = yaml.safe_load(stream)
            return parsed_yaml
        except yaml.YAMLError as exc:
            print(exc)


def create_account_info(wallet_balance_raw: dict, config: dict):
    wallet_balance = wallet_balance_raw["result"]["USDT"]["available_balance"]
    return {
        "balanceOnExchange": round(wallet_balance, 2),
        "balanceInBank": round(config[ACCOUNT_TYPE]["balanceInBank"], 2),
        "accountSize": round(wallet_balance + config[ACCOUNT_TYPE]["balanceInBank"], 2)
    }


def transform_trades(trades_raw: pd.DataFrame, instruments_info: dict, config: dict) -> pd.DataFrame:
    trades = trades_raw.copy()

    risk_per_trade_usd = config[ACCOUNT_TYPE]["riskPerTradeUsd"]
    futures_account_size_usd = config[ACCOUNT_TYPE]["futuresAccountSizeUsd"] * \
        config[ACCOUNT_TYPE]["usedMarginAccount"]

    trades["move"] = trades["entry_price"] - trades["stop_loss"]
    trades["profit_target"] = trades["entry_price"] + trades["move"]
    trades["position"] = abs(risk_per_trade_usd/trades["move"])
    trades["position_usd"] = trades["position"] * trades["entry_price"]
    trades["leverage"] = trades["position_usd"] / futures_account_size_usd

    # Round leverage
    trades['leverage'] = trades['leverage'].astype(float)
    trades.loc[trades["leverage"] < MIN_LEVERAGE, "leverage"] = MIN_LEVERAGE
    trades = trades.round({"leverage": 2})

    # Roud prices by contract specs
    trades["price_scale"] = trades.apply(
        lambda row: __parse_price_scale(instruments_info, row["ticker"]), axis=1)
    trades["entry_price"] = trades.apply(lambda x: round(
        x["entry_price"], x["price_scale"]), axis=1)
    trades["profit_target"] = trades.apply(lambda x: round(
        x["profit_target"], x["price_scale"]), axis=1)
    trades["stop_loss"] = trades.apply(lambda x: round(
        x["stop_loss"], x["price_scale"]), axis=1)
    trades["move"] = trades.apply(lambda x: round(
        x["move"], x["price_scale"]), axis=1)

    # Round position
    trades["position"] = trades.apply(lambda x: round(
        x["position"], 0 if x["position"] > 1 else 5), axis=1)

    # Compute expected profit and loss
    trades["expected_profit"] = abs(
        trades["entry_price"] - trades["profit_target"]) * trades["position"]
    trades["expected_loss"] = abs(
        trades["entry_price"] - trades["stop_loss"]) * trades["position"] * -1

    return trades


def place_trades_on_exchange(trades: pd.DataFrame, exchange) -> pd.DataFrame:
    response = []

    for index, trade in trades.iterrows():

        try:
            __set_leverage(exchange, trade["ticker"], trade["leverage"])

            __set_isolate_margin(exchange,
                                 trade["ticker"],
                                 trade["leverage"],
                                 trade["leverage"])

            exchange.place_conditional_order(
                symbol=trade["ticker"],
                order_type="Limit",
                side="Buy" if trade["direction"] == "LONG" else "Sell",
                qty=trade["position"],
                price=trade["entry_price"],
                base_price=round(trade["entry_price"] +
                                 trade["move"], trade["price_scale"]),
                stop_px=trade["entry_price"],
                time_in_force="GoodTillCancel",
                reduce_only=False,
                close_on_trigger=False,
                take_profit=trade["profit_target"],
                stop_loss=trade["stop_loss"],
                position_idx=0
            )

            trade_id = "{}_{}".format(trade["ticker"], trade["direction"])
            response.append({"trade_id": trade_id, "status": "OK"})
        except Exception as e:
            print(e)
            trade_id = "{}_{}".format(trade["ticker"], trade["direction"])
            response.append({"trade_id": trade_id, "status": "ERROR"})

    return pd.DataFrame(response)


def write_trades_to_audit_log(trades: pd.DataFrame, audit_log_path) -> None:
    trades["create_date"] = datetime.datetime.now()
    trades.to_csv(audit_log_path, mode='a',
                  header=not os.path.exists(audit_log_path), index=False)


def __parse_price_scale(instruments_info: dict, ticker: str) -> float:
    instruments_info_list = instruments_info["result"]["list"]
    price_scale = [x["priceScale"]
                   for x in instruments_info_list if x["symbol"] == ticker]
    return int(price_scale[0]) if any(price_scale) else DEFAULT_PRICE_SCALE


def __set_leverage(exchange, ticker: str, leverage: float) -> None:
    actual_leverage = exchange.my_position(
        symbol=ticker)["result"][0]["leverage"]

    if leverage == actual_leverage:
        return

    exchange.set_leverage(
        symbol=ticker,
        buy_leverage=leverage,
        sell_leverage=leverage
    )


def __set_isolate_margin(exchange, ticker: str, buy_leverage: float, sell_leverage: float) -> None:
    is_isolated = exchange.my_position(
        symbol=ticker)["result"][0]["is_isolated"]

    if is_isolated:
        return

    exchange.cross_isolated_margin_switch(
        symbol=ticker, is_isolated=True, buy_leverage=buy_leverage, sell_leverage=sell_leverage)
