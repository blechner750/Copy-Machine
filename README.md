# Welcome to the COPY MACHINE

This project is a two-part system.
One part is a Python-based Flask server using Selenium to perform browser interactions.
The second part is a MQL5 based program, used to send HTTP POST requests to the server.

Together this is an end-to-end system meant to copy trades from a MetaTrader 5 terminal to a Web-Browser based trading terminal.

## Features

- Automated trade execution
- Automated trade modification
- Fallbacks in the event the browser crashed or doesn't respond correctly
- Click button interactions based on availability
- Logic to ensure all buttons are available upon request

## Requirements

- Python 3.8+
- Selenium
- Flask
- WebDriver (compatible with the browser used)

## Caveat / Author's notes

Obviously this is VERY purpose built. Every inch of this is built for specific components.
I have no interest in modifying this for anybody else. If you are looking at this because you want to use it, you are on your own.
This is here just for source-control and to show off a little (just a little).

Good hunting
