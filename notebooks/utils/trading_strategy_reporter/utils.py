import pandas as pd

average_profit_usd = 1
average_loss_usd = -1

def add_cum_sum_column(trades):
    trades.loc[trades["StateProfitTarget1"] == "PROFIT", "StateUSD"] = average_profit_usd 
    trades.loc[trades["StateProfitTarget1"] == "EARLY-REACTION", "StateUSD"] = 0
    trades.loc[trades["StateProfitTarget1"] == "LOSS", "StateUSD"] = average_loss_usd

    trades["StateUSDCumSum"] = trades["StateUSD"].cumsum()


def compute_statistic(trades: pd.DataFrame):
    pt_states_count = trades["StateProfitTarget1"].value_counts()

    count_profit_trades = pt_states_count["PROFIT"] if "PROFIT" in pt_states_count else 0
    count_loss_trades = pt_states_count["LOSS"] if "LOSS" in pt_states_count else 0
    count_early_reaction_trades = pt_states_count["EARLY-REACTION"] if "EARLY-REACTION" in pt_states_count else 0
    success = round(count_profit_trades/(count_profit_trades+count_loss_trades),2)

    statistics = {
        "TotalNumberOfTrades" : [trades.shape[0]],
        "CountProfitTrades" : [count_profit_trades],
        "CountLossTrades" : [count_loss_trades],
        "CountEarlyReactionTrades": [count_early_reaction_trades],
        "Success": [success],
        "RiskRewardRatio": ["1:1"],
        "Expectation": [(success * average_profit_usd) - ((success-1) * average_loss_usd)]
    }

    result = pd.DataFrame(statistics).transpose()
    result.columns = ["Value"]
    return result
