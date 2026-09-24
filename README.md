# FRS: Food Menu Viewer for Tarbiat Modares University

A desktop app for browsing the weekly meal menu of the
[Tarbiat Modares University food reservation system](https://frs.modares.ac.ir) and adding up
what a week of meals will cost.

The interface is in Persian (Farsi) and uses the Jalali calendar.

## Features

- Log in with your student number and password
- View breakfast, lunch and dinner for each day of the week
- See the meals you have already reserved and which days are closed
- Move to the previous, current or next week
- Tick foods to get a running total price (shown in toman)
- Click a day to see its full details in the side panel

The app only reads data. It does not reserve or cancel meals.

## Requirements

- Python 3.10 or newer (developed on 3.13)
- A Tarbiat Modares University account with access to FRS

## Installation

```bash
git clone https://github.com/russellzparadox/FRS.git
cd FRS
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install PyQt6 requests jdatetime
```

`requirements.txt` pins a larger set of packages. `pip install -r requirements.txt` also works on
Linux and macOS, but it includes `uvloop`, which does not install on Windows.

## Usage

```bash
python main.py
```

Enter your student number and password in the login window. After you log in, the current week's
menu loads.

### Keyboard shortcuts

| Key | Action                |
|-----|-----------------------|
| `n` | Next week             |
| `p` | Previous week         |
| `c` | Current week          |
| `r` | Clear selected foods  |
| `q` | Quit                  |

## Project structure

```
main.py              Entry point
core/api.py          FRS client: login and weekly menu requests
core/utils.py        Jalali date and price formatting helpers
ui/login_dialog.py   Login window
ui/main_window.py    Main window with the menu table and price summary
```

## Security note

Your credentials are sent only to `frs.modares.ac.ir` and are not stored. TLS certificate
verification is turned off for requests to that site, because its certificate chain does not
validate by default.

## Disclaimer

This is an unofficial project and is not affiliated with Tarbiat Modares University.
