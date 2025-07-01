# Welcome to the COPY MACHINE

This project is a two-part system.
One part is a Python-based Flask server using Selenium to perform browser interactions.
The second part is a MQL5 based program, used to send HTTP POST requests to the server.

Together this is an end-to-end system meant to copy trades from a MetaTrader 5 terminal to a Web-Browser based trading terminal.

## Features

This system has the option to use a browser profile, otherwise it's currently setup to login on its own.
It will ensure trade confirmations are off when browser starts, and will ensure the trade menu is available when needed.
From there it will copy any opened trades in MT5. It can also send modifications, so if the TP or SL move it will update that accordingly.
It *could* handle the closing of trades. It tracks it, but I didn't hook that up. Current system using this trades entirely through TPs and SLs.
I've seen the browser crash before. So I implemented a simple check, and added a refresh function.
I've also had issues with the 'Open Positions' table not updating after the trade is executed. I built a check to refresh the browser in this scenario too.

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
