import yaml
import pandas as pd
import os
import datetime
import decimal

MIN_LEVERAGE = 1
DEFAULT_PRICE_SCALE = 2
DEFAULT_QTY_STEP = "1"

def load_config(config_file: str) -> dict:
    with open(config_file, 'r') as stream:
        try:
            parsed_yaml = yaml.safe_load(stream)
            return parsed_yaml
        except yaml.YAMLError as exc:
            print(exc)

def transform_trades(trades_raw: pd.DataFrame, instruments_info: dict, config: dict, account_type: str) -> pd.DataFrame:
    trades = trades_raw.copy()

    risk_per_trade_usd = config[account_type]["riskPerTradeUsd"]
    futures_account_size_usd = config[account_type]["futuresAccountSizeUsd"] * \
        config[account_type]["usedMarginAccount"]
    trigger_price_distance_percentage = config[account_type]["triggerPriceDistancePercentage"]

    trades["move"] = trades["entry_price"] - trades["stop_loss"]
    trades["profit_target"] = trades["entry_price"] + trades["move"]
    trades["position"] = abs(risk_per_trade_usd/trades["move"])
    trades["position_usd"] = trades["position"] * trades["entry_price"]
    trades["leverage"] = trades["position_usd"] / futures_account_size_usd
    trades["trigger_price"] = trades["entry_price"] + (trades["move"] * trigger_price_distance_percentage)

    # Round leverage
    trades['leverage'] = trades['leverage'].astype(float)
    trades.loc[trades["leverage"] < MIN_LEVERAGE, "leverage"] = MIN_LEVERAGE
    trades = trades.round({"leverage": 2})

    # Roud prices by contract specs
    trades["price_scale"] = trades.apply(
        lambda row: __parse_price_scale(instruments_info, row["ticker"]), axis=1)
    trades["qty_step"] = trades.apply(lambda row: __parse_qty_step(
        instruments_info, row["ticker"]), axis=1)
    trades["entry_price"] = trades.apply(lambda x: round(
        x["entry_price"], x["price_scale"]), axis=1)
    trades["trigger_price"] = trades.apply(lambda x: round(
        x["trigger_price"], x["price_scale"]), axis=1)
    trades["profit_target"] = trades.apply(lambda x: round(
        x["profit_target"], x["price_scale"]), axis=1)
    trades["stop_loss"] = trades.apply(lambda x: round(
        x["stop_loss"], x["price_scale"]), axis=1)
    trades["move"] = trades.apply(lambda x: round(
        x["move"], x["price_scale"]), axis=1)

    # Round position
    trades["position"] = trades.apply(lambda x: round(
        x["position"], decimal.Decimal(x["qty_step"]).as_tuple().exponent * -1), axis=1)

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
            __set_isolate_margin(exchange,
                                 trade["ticker"],
                                 trade["leverage"],
                                 trade["leverage"])
            
            __set_leverage(exchange, trade["ticker"], trade["leverage"])

            exchange.place_order(
                category="linear",
                symbol=trade["ticker"],
                side="Buy" if trade["direction"] == "LONG" else "Sell",
                orderType="Limit",
                qty=str(trade["position"]),
                price=str(trade["entry_price"]),
                triggerPrice=str(trade["trigger_price"]),
                triggerDirection= 2 if trade["direction"] == "LONG" else 1,
                reduceOnly=False,
                closeOnTrigger=False,
                takeProfit=str(trade["profit_target"]),
                stopLoss=str(trade["stop_loss"]),
                positionIdx=0
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

def __parse_qty_step(instruments_info: dict, ticker: str) -> str:
    instruments_info_list = instruments_info["result"]["list"]
    qty_step = [x["lotSizeFilter"]["qtyStep"]
                for x in instruments_info_list if x["symbol"] == ticker]
    return qty_step[0] if any(qty_step) else DEFAULT_QTY_STEP

def __set_leverage(exchange, ticker: str, leverage: float) -> None:
    response = exchange.get_positions(category="linear", symbol=ticker)

    actual_leverage = float(response["result"]["list"][0]["leverage"])
    if leverage == actual_leverage:
        return

    exchange.set_leverage(
        category="linear",
        symbol=ticker,
        buy_leverage=str(leverage),
        sell_leverage=str(leverage)
    )


def __set_isolate_margin(exchange, ticker: str, buy_leverage: float, sell_leverage: float) -> None:
    response = exchange.get_positions(category="linear", symbol=ticker)
    
    is_isolated = response["result"]["list"][0]["tradeMode"] == 1
    if is_isolated:
        return

    exchange.switch_margin_mode(
                category="linear",
                symbol=ticker,
                tradeMode=1,
                buyLeverage=str(buy_leverage),
                sellLeverage=str(sell_leverage)
            )
