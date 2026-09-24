# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A PyQt6 desktop client for the food reservation system (FRS) of Tarbiat Modares University
(`https://frs.modares.ac.ir`). The user logs in with their student number and password, then
browses the weekly meal menu (breakfast, lunch, dinner), sees what is already reserved, and ticks
foods to get a running total price for the week. It only reads data; it does not place reservations.

The UI text is Persian (Farsi) and dates are Jalali (Shamsi).

## Running

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Run from the repo root: `main.py` imports `ui.*` and `core.*` as top-level packages.

The only runtime dependencies the code actually uses are `PyQt6`, `requests` and `jdatetime`.
`requirements.txt` is a full `pip freeze` of an older environment (FastAPI, Textual, uvicorn, etc.)
and includes `uvloop`, which does not install on Windows. For a minimal install:

```bash
pip install PyQt6 requests jdatetime
```

There are no tests, linter config or CI. The code is formatted in Black style (88-column lines,
double quotes); keep new code consistent with that.

## Layout

```
main.py              Entry point: creates QApplication, shows LoginDialog, logs in, opens MainWindow
core/api.py          FRSClient: requests.Session wrapper for login and the weekly menu API
core/utils.py        Jalali Saturday of the current week, price formatting, HTML escaping
ui/login_dialog.py   LoginDialog: student number + password form
ui/main_window.py    MainWindow: week navigation, menu table, details panel, price summary
```

## How it works

### Login (`FRSClient.login`)

1. `GET https://frs.modares.ac.ir/` and pull the JSON inside `<script id="modelJson">`
   (HTML-unescaped) to get `loginUrl` and `antiForgery.value`.
2. `POST` the credentials plus `idsrv.xsrf` to that login URL (IdentityServer).
3. If the response contains a `<form action=...>`, it is the SAML/OIDC hand-off: collect all
   `name`/`value` inputs and `POST` them to the form action.
4. Success is detected by keywords in the final page (`خروج`, `رزرو غذا`, `داشبورد`, `logout`).

Cookies live on the shared `requests.Session`, so every later API call is authenticated.
All requests use `verify=False` (urllib3 warnings are disabled) because the site's TLS chain does
not validate out of the box.

### Weekly menu (`FRSClient.get_week_menu`)

`GET https://frs.modares.ac.ir/api/v0/Reservation`

- Current week: `?lastdate=&navigation=0`
- Other weeks: `?lastdate=<YYYY/MM/DD Jalali Saturday>&navigation=<offset * 7>`

The response is a list of days. Fields the UI relies on:

```
Day:   DayTitle, DayDate, DayState (2 = closed / not reservable), Meals[]
Meal:  MealName ("صبحانه" | "ناهار" | "شام"), FoodMenu[], LastReserved[]
Food:  FoodName, SelfMenu[0].Price, SelfMenu[0].SelfName
LastReserved[0]: FoodName, SelfName
```

`MealName` values are matched as Persian strings in `ui/main_window.py`; don't translate them.

### Prices

The API returns prices in **rials**. `format_price` divides by 10 and shows **toman** with the
Persian thousands separator `٬`. A price of 0 shows as "رایگان" (free).

### Main window state

- `base_saturday`: Jalali date of this week's Saturday (the Iranian week starts on Saturday).
- `current_offset`: weeks relative to the current week; prev/next/current buttons change it and
  call `load_week()`.
- `checkboxes`: list of `(QCheckBox, price, meal_info)` for reservable foods. It is rebuilt on
  every `update_table()`; `update_summary()` sums the checked prices.
- Keyboard shortcuts: `n` next week, `p` previous, `c` current, `r` reset selections, `q` quit.

Network calls run on the GUI thread; `QApplication.processEvents()` is called first so the status
bar message shows before the UI blocks.

## Conventions

- User-facing strings and code comments are in Persian. Keep new UI text in Persian.
- Any API text inserted into rich-text `QLabel`s or the details `QTextEdit` must go through
  `core.utils.escape` first.
- `core/api.py` shows errors with `QMessageBox` directly, so it depends on a running `QApplication`.
- Never hardcode or log credentials. Don't commit `.venv`, `temp/` or `__pycache__`.

## Known issues

- `ui/__init__py.py` is misnamed (should be `ui/__init__.py`). Imports still work because Python 3
  treats `ui/` as a namespace package.
- `__pycache__/*.pyc` files are committed, including stale `core/auth.py` and `ui/login_window.py`
  bytecode. `.gitignore` does not exclude `__pycache__/`.
- The header comments in `ui/*.py` say `gui/...`; the directory is `ui/`.
- `requirements.txt` is much larger than what the app needs (see Running).
- In `FRSClient.login`, a failure in steps 2–4 that isn't an exception returns `False` with no
  message; `main.py` then shows a generic "wrong username or password" error.
