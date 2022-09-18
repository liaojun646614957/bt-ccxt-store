from ccxtbt import CCXTStore
import backtrader as bt
from datetime import datetime, timedelta, timezone
from backtrader import Order
import json


class TestStrategy(bt.Strategy):
    params = (
        ('period5', 5),
        ('period20', 20),
    )

    def __init__(self):
        self.ema5 = bt.indicators.ExponentialMovingAverage(self.datas[0], period=self.params.period5)
        self.ema20 = bt.indicators.ExponentialMovingAverage(self.datas[0], period=self.params.period20)
        self.emaDiff = self.ema5 - self.ema20

        self.bought = False
        self.live_data = False
        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyExecutedBar = 0

    def log(self, txt, dt=None):
        # 记录策略的执行日志
        tz = timezone(timedelta(hours=8))
        dt = dt or self.datas[0].datetime.datetime(tz=tz)
        print('%s: %s' % (dt, txt))

    def next(self):
        # Get cash and balance
        # New broker method that will let you get the cash and balance for
        # any wallet. It also means we can disable the getcash() and getvalue()
        # rest calls before and after next which slows things down.

        # NOTE: If you try to get the wallet balance from a wallet you have
        # never funded, a KeyError will be raised! Change LTC below as approriate
        if self.live_data:
            cash, value = self.broker.get_wallet_balance('USDT')
            btcCash, btcValue = self.broker.get_wallet_balance('BTC')
            btcCash = "{:.8f}".format(float(btcCash))
        else:
            # Avoid checking the balance during a backfill. Otherwise, it will
            # Slow things down.
            cash = 'NA'
            btcCash = 'NA'
        for data in self.datas:
            self.log('{} | Cash {} BTC {}  | O: {} H: {} L: {} C: {} V:{} EMA5:{}  EMA20:{} EMA DIFF {}'.format(
                data._name, cash, btcCash, data.open[0],
                data.high[0], data.low[0],
                data.close[0], data.volume[0],
                self.ema5[0], self.ema20[0], self.emaDiff[0]))
            if self.order:
                self.log('exists hanging on order....')
                return
            if not self.live_data:
                return
            if self.buyExecutedBar > 0 and float(btcCash) > 0:  # 已买入btc
                if len(self) - self.buyExecutedBar >= 2:
                    self.order = self.broker.sell(owner=None, data=self.data, size=btcCash, exectype=Order.Market,
                                                  price=1500, amount=5, parent='', transmit='')
            else:
                # Buy
                # size x price should be >10 USDT at a minimum at Binance
                # make sure you use a price that is below the market price if you don't want to actually buy
                self.order = self.broker.buy(owner=None, data=self.data, size=0.0003, exectype=Order.Market, price=1500,
                                             amount=5, parent='', transmit='')

    # 订单状态通知，买入卖出都是下单
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # broker 提交/接受了，买/卖订单则什么都不做
            return
        # 检查一个订单是否完成
        # 注意: 当资金不足时，broker会拒绝订单
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    '已买入, 价格: %.2f, 费用: %.2f, 手续费 %.8f' %
                    (order.price,
                     order.cost,
                     order.fee))
                # 记录买入下单时是第几个
                self.buyExecutedBar = len(self)
            elif order.issell():
                self.log('已卖出, 价格: %.2f, 费用: %.2f, 手续费 %.8f' %
                         (order.price,
                          order.cost,
                          order.fee))
                self.buyExecutedBar = 0

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

        # 其他状态记录为：无挂起订单
        self.order = None

    # 交易状态通知，一买一卖算交易
    def notify_trade(self, trade):
        print('notify_trade called')
        if not trade.isclosed:
            return
        self.log('交易利润, 毛利润 %.2f, 净利润 %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()
        msg = 'Data Status: {}'.format(data._getstatusname(status))
        print(dt, dn, msg)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False


with open('../params.json', 'r') as f:
    params = json.load(f)

cerebro = bt.Cerebro(quicknotify=True)

# Add the strategy
cerebro.addstrategy(TestStrategy)

# Create our store
config = {'apiKey': params["okx"]["apikey"],
          'secret': params["okx"]["secret"],
          'password': params["okx"]["password"],
          'proxies': {'https': 'http://127.0.0.1:7890', 'http': 'http://127.0.0.1:7890'},
          'enableRateLimit': True,
          }

# IMPORTANT NOTE - Kraken (and some other exchanges) will not return any values
# for get cash or value if You have never held any BNB coins in your account.
# So switch BNB to a coin you have funded previously if you get errors
store = CCXTStore(exchange='okx', currency='BTC', config=config, retries=3, debug=False)

# Get the broker and pass any kwargs if needed.
# ----------------------------------------------
# Broker mappings have been added since some exchanges expect different values
# to the defaults. Case in point, Kraken vs Bitmex. NOTE: Broker mappings are not
# required if the broker uses the same values as the defaults in CCXTBroker.
broker_mapping = {
    'order_types': {
        bt.Order.Market: 'market',
        bt.Order.Limit: 'limit',
        bt.Order.Stop: 'stop-loss',  # stop-loss for kraken, stop for bitmex
        bt.Order.StopLimit: 'stop limit'
    },
    'mappings': {
        'closed_order': {
            'key': 'status',
            'value': 'closed'
        },
        'canceled_order': {
            'key': 'status',
            'value': 'canceled'
        }
    }
}

broker = store.getbroker(broker_mapping=broker_mapping, debug=False)
cerebro.setbroker(broker)

# Get our data
# Drop newest will prevent us from loading partial data from incomplete candles
hist_start_date = datetime.utcnow() - timedelta(minutes=50)
data = store.getdata(dataname='BTC/USDT', name="BTCUSDT",
                     timeframe=bt.TimeFrame.Minutes, fromdate=hist_start_date,
                     compression=1, ohlcv_limit=50, drop_newest=True)  # , historical=True)

# Add the feed
cerebro.adddata(data)

# Run the strategy
cerebro.run()
