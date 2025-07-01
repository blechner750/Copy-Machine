# Welcome to the COPY MACHINE

This project is a two-part system.
One part is a Python-based Flask server using Selenium to perform browser interactions.
The second part is a MQL5 based program, used to send HTTP POST requests to the server.

Together this is an end-to-end system meant to copy trades from a MetaTrader 5 terminal to a Web-Browser based trading terminal.

## Features

This system has the option to use a browser profile, otherwise it's currently setup to login on its own.

It will ensure trade confirmations are off when browser starts so all actions occur without additional prompting.

It's imperative to make sure the 'Favorites' have all symbols you intend to trade. It now has code that will select symbols from this list.

If the symbol isn't there, you don't get the trade.

Otherwise, when a trade is executed on the MT5 side, the system will open the symbol to trade, input volume, TP/SL (if necessary) and then click the BUY/SELL button.

It will then return back to the MT5 terminal on success with the ticket generated via the browser's trade terminal.

Any modifications to the TP or SL in MT5 will result in the same action taking place in the browser.

If trades are closed in MT5, whether via a manual close or the TP/SL being hit, it will send a 'delete' to the browser to close its trade as well.

If it's manual, you want this behavior. If it's via TP/SL, sometimes the browser will close first, sometimes it won't. This just keeps them in sync.

It also has code to close ALL positions. If there is some type of mechanism that closes all trades in MT5, it will perform the same action in the browser.

Sometimes the browser will crash, and sometimes the terminal will no longer update it's open positions. There is code to refresh the browser every twenty minutes to prevent issue with this.

It also has code to make sure no refresh occurs while any other operation is occurring, and it will also refresh automatically if a position if opened and the open positions does not show the change.

There are also comments pretty thoroughly in here, in the event something goes wrong there should be a reasonable way to figure out why.

But at this point, the system is basically as fleshed out as it can get. I've come across a LOT of bugs that I had to carefully build the code to prevent or work around.

## Requirements

- Python 3.8+
- Selenium
- Flask
- WebDriver (compatible with the browser used)

## Caveat / Author's notes

Obviously this is VERY purpose built. It's meant for one specific web terminal. Maybe in the future I'll apply it to others, but for now this is it.
If you came across this by search, and want to use it.. feel free, but you are on your own.
This is here just for source-control... and to show off a little (just a little).

Good hunting
