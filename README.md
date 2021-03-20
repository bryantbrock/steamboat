# Steamboat - trade, backtest, and deploy a stock market algorithms
Steamboat is a python framework for building financial algorithms for the trading stocks on the stock market. It allows you to backtest strategies and trade both live and paper via the [alpaca api](alpaca.markets).Itcomes prebuilt with two primary classes: `AlpacaTrade` and `AlpacaBacktest`. Create simple logic once, and run it through both the backtest and the live trading class. No need for different logic. `AlpacaTrade` has built in support for paper, just specificy `paper=True` when initializing it. Before installing, head over to alpaca's website to get a paper account setup and grab the api keys provided.


## Installation
Simply clone the repository to the root folder of your strategy.
```
git clone https://github.com/bryantbrock/steamboat.git
```


Then, access it via import, as if you had built the framework yourself.
```
from steamboat import AlpacaTrade, AlpacaBacktest
```


## Documentation
### `AlpacaTrade`
### `AlpacaBacktest`
