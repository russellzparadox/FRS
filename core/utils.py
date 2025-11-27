# core/utils.py
import html
from datetime import date, timedelta

import jdatetime


def get_shamsi_saturday() -> jdatetime.date:
    today = date.today()
    days_to_sat = (today.weekday() + 1) % 7
    saturday = today - timedelta(days=days_to_sat)
    return jdatetime.date.fromgregorian(date=saturday)


def format_price(price: int) -> str:
    if not price:
        return "رایگان"
    return f"{int(price):,} تومان".replace(",", "٬")


def escape(text: str) -> str:
    return html.escape(text)
