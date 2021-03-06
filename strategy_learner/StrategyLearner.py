"""
Template for implementing StrategyLearner  (c) 2016 Tucker Balch
"""
"""Author: Lu Wang, lwang496, lwang496@gatech.edu"""

import datetime as dt
import pandas as pd
import util as ut
import random
import numpy as np
import QLearner as ql

class StrategyLearner(object):

    # constructor
    # Author: Lu Wang lwang496
    def __init__(self, verbose = False, impact=0.0):
        self.verbose = verbose
        self.impact = impact
        self.qlearner = ql.QLearner(num_states=3000, \
                                   num_actions=3, \
                                   alpha=0.2, \
                                   gamma=0.9, \
                                   rar=0.5, \
                                   radr=0.99, \
                                   dyna=0, \
                                   verbose=False)

    # this method should create a QLearner, and train it for trading
    def addEvidence(self, symbol = "IBM", \
        sd=dt.datetime(2008,1,1), \
        ed=dt.datetime(2009,1,1), \
        sv = 10000):


        # add your code to do learning here

        # example usage of the old backward compatible util function
        syms = [symbol]
        dates = pd.date_range(sd, ed)
        prices_all = ut.get_data(syms, dates)  # automatically adds SPY
        prices = prices_all[syms]  # only portfolio symbols
        prices_SPY = prices_all['SPY']  # only SPY, for comparison later
        if self.verbose: print prices

        # example use with new colname
        volume_all = ut.get_data(syms, dates, colname="Volume")  # automatically adds SPY
        volume = volume_all[syms]  # only portfolio symbols
        volume_SPY = volume_all['SPY']  # only SPY, for comparison later
        if self.verbose: print volume

        train_SMA = prices.rolling(window=14, min_periods=14).mean()
        train_SMA.fillna(method='ffill', inplace=True)
        train_SMA.fillna(method='bfill', inplace=True)

        train_std = prices.rolling(window=14, min_periods=14).std()
        top_band = train_SMA + (2 * train_std)
        bottom_band = train_SMA - (2 * train_std)
        train_bbp = (prices - bottom_band) / (top_band - bottom_band)
        # turn sma into price/sma ratio
        train_SMAPrice_ratio = prices / train_SMA

        # caculate momentum
        train_momentum = (prices / prices.copy().shift(14)) - 1

        train_daily_rets = (prices / prices.shift(1)) - 1
        train_std = train_daily_rets.rolling(14, 14).std()
        train_std.fillna(method='ffill', inplace=True)
        train_std.fillna(method='bfill', inplace=True)

        train_SMAPrice_ratio_n, train_bbp_n, train_momentum_n, train_std_n = self.discritize(train_SMAPrice_ratio, train_bbp, train_momentum, train_std)

        strategy =  train_SMAPrice_ratio_n * 100 + train_bbp_n * 10 + train_momentum_n * 10 + train_std_n
        start = strategy.index[0]
        end = strategy.index[-1]
        dates = pd.date_range(start, end)
        strategy_states = strategy.values
        df = pd.DataFrame(index = dates)

        df['positions'] = 0
        df['values'] = prices.ix[start:end, symbol]
        df['cash'] = sv
        df.fillna(method='ffill', inplace=True)
        df.fillna(method='bfill', inplace=True)
        train_array = df.values
        converged = False
        round = 0
        while not converged:

            p = 0
            state =  strategy_states[0, 0]
            action = self.qlearner.querysetstate(state)
            total_days = strategy_states.shape[0]
            prev_val = sv

            for i in range(1, total_days):
                # curr_price will be used to caculate impact
                curr_price = train_array[i, 1]
                amount = 0
                if p == 0 and action == 1:
                    amount = 1000
                    train_array[i, 2] = train_array[i - 1, 2] + train_array[
                                                                    i, 1] * 1000 - self.impact * curr_price * abs(
                        amount)
                    curr_val = train_array[i, 2] - 1000 * train_array[i, 1]
                    train_array[i, 0] = -1000

                    p = 1
                elif p == 0 and action == 2:
                    amount = 1000
                    train_array[i, 2] = train_array[i - 1, 2] - train_array[
                                                                    i, 1] * 1000 - self.impact * curr_price * abs(
                        amount)
                    curr_val = train_array[i, 2] + 1000 * train_array[i, 1]
                    train_array[i, 0] = 1000

                    p = 2

                elif p == 1 and action == 2:
                    amount = 2000
                    train_array[i, 2] = train_array[i - 1, 2] - train_array[
                                                                    i, 1] * 2000 - self.impact * curr_price * abs(
                        amount)
                    curr_val = train_array[i, 2] + 1000 * train_array[i, 1]
                    train_array[i, 0] = 1000

                    p = 2

                elif p == 2 and action == 1:
                    amount = 2000
                    train_array[i, 2] = train_array[i - 1, 2] + train_array[
                                                                    i, 1] * 2000 - self.impact * curr_price * abs(
                        amount)
                    curr_val = train_array[i, 2] - 1000 * train_array[i, 1]
                    train_array[i, 0] = -1000

                    p = 1

                else:
                    train_array[i, 0] = train_array[i - 1, 0]
                    train_array[i, 2] = train_array[i - 1, 2]
                    curr_val = train_array[i, 2] + train_array[i, 0] * train_array[i, 1]

                if prev_val == 0:
                    reward = 0
                else:
                    reward = curr_val / prev_val - 1
                prev_val = curr_val
                state = strategy_states[i, 0]
                action = self.qlearner.query(state, reward)

            round += 1
            if round > 1300:
                converged = True


    def testPolicy(self, symbol="IBM", \
                   sd=dt.datetime(2009, 1, 1), \
                   ed=dt.datetime(2010, 1, 1), \
                   sv=100000):

        # here we build a fake set of trades
        # your code should return the same sort of data
        dates = pd.date_range(sd, ed)
        prices_all = ut.get_data([symbol], dates)  # automatically adds SPY
        prices = prices_all[[symbol,]]
        trades = prices_all[[symbol, ]]  # only portfolio symbols
        trades_SPY = prices_all['SPY']  # only SPY, for comparison later
        trades.values[:, :] = 0

        test_SMA = prices.rolling(window=14, min_periods=14).mean()
        test_SMA.fillna(method='ffill', inplace=True)
        test_SMA.fillna(method='bfill', inplace=True)

        test_std = prices.rolling(window=14, min_periods=14).std()
        top_band = test_SMA + (2 * test_std)
        bottom_band = test_SMA - (2 * test_std)
        test_bbp = (prices - bottom_band) / (top_band - bottom_band)
        # turn sma into price/sma ratio
        test_SMAPrice_ratio = prices / test_SMA

        # caculate momentum
        test_momentum = (prices / prices.copy().shift(14)) - 1

        test_daily_rets = (prices / prices.shift(1)) - 1
        test_std = test_daily_rets.rolling(14, 14).std()
        test_std.fillna(method='ffill', inplace=True)
        test_std.fillna(method='bfill', inplace=True)

        test_SMA_ratio_n, test_bbp_n, test_momentum_n, test_std_n = self.discritize(test_SMAPrice_ratio,test_bbp,test_momentum, test_std)

        test_strategy_states = (test_bbp_n * 100 + test_momentum_n * 10 + test_std_n).values

        test_total_dates = test_strategy_states.size
        p = 0
        for i in range(1, test_total_dates):
            state = test_strategy_states[i - 1, 0] + p * 1000
            action = self.qlearner.querysetstate(state)
            status = 0
            if p == 0 and action == 1:

                status = -1000
                p = 1
            elif p == 0 and action == 2:
                status = 1000
                p = 2

            elif p == 1 and action == 2:
                status = 2000
                p = 2

            elif p == 2 and action == 1:
                status = -2000
                p = 1
            trades.values[i, :] = status

        if self.verbose: print type(trades)  # it better be a DataFrame!
        if self.verbose: print trades
        if self.verbose: print prices_all
        return trades

    def discritize(self,SMA_ratio,bbp,momentum, vol ):

        SMA_ratio_n = SMA_ratio
        min1 = SMA_ratio.ix[:, 0].min()
        max1 = SMA_ratio.ix[:, 0].max()
        SMA_ratio_n.ix[:, 0] = np.digitize(SMA_ratio.ix[:, 0], np.linspace(min1, max1, 10)) - 1
        bbp_n = bbp
        min2 = bbp.ix[:, 0].min()
        max2 = bbp.ix[:, 0].max()

        bbp_n.ix[:, 0] = np.digitize(bbp.ix[:, 0], np.linspace(min2, max2, 10)) - 1

        momentum_n = momentum
        min3 = momentum.ix[:, 0].min()
        max3 = momentum.ix[:, 0].max()
        momentum_n.ix[:, 0] = np.digitize(momentum.ix[:, 0], np.linspace(min3, max3, 10)) - 1

        vol_n = vol
        min4 = vol.ix[:, 0].min()
        max4 = vol.ix[:, 0].max()
        vol_n.ix[:, 0] = np.digitize(vol.ix[:, 0], np.linspace(min4, max4, 10)) - 1
        return SMA_ratio_n,bbp_n,momentum_n, vol_n

    def author(self):
        return 'lwang496'

    if __name__ == "__main__":
        print "One does not simply think up a strategy"



