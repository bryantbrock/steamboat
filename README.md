# Steamboat - trade, backtest, and deploy a stock market algorithm using python.
Steamboat comes prebuilt with two primary classes: `AlpacaTrade` and `AlpacaBacktest`. Create simple logic once, and run it through both the backtest and the live trading class. No need for different logic. `AlpacaTrade` has built in support for paper, just specificy `paper=True` when initializing it. Both classes are based on the [alpaca api](alpaca.markets). Signup there to get the keys you will need to get started. 


## Installation
Simply clone the repository to the root folder of your strategy.
```git clone https://github.com/bryantbrock/steamboat.git```

Then, access it via `import`, as if you had built the framework yourself.
```from steamboat import AlpacaTrade, AlpacaBacktest```


## Documentation
### `AlpacaTrade`
### `AlpacaBacktest`
