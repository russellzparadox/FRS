#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# food_reserve_tui.py - منوی غذا دانشگاه تربیت مدرس با TUI زیبا

import html
import json
import re
import sys
from datetime import date, timedelta
from urllib.parse import urlencode

import jdatetime
import requests
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()
requests.packages.urllib3.disable_warnings()

# ================== تنظیمات ==================
USERNAME = "###"
PASSWORD = "###"
# =============================================

BASE_API = "https://frs.modares.ac.ir/api/v0/Reservation"
COOKIES_FILE = "cookies.txt"


def login(session: requests.Session) -> bool:
    resp = session.get(
        "https://frs.modares.ac.ir/",  # ← HTTPS! (important now)
        verify=False,
        allow_redirects=True,
    )

    # Save raw page (for debugging like your fish script)

    # Extract the JSON inside <script id="modelJson">
    match = re.search(
        r"<script id=['\"]modelJson['\"] type=['\"]application/json['\"]>\s*(.*?)\s*</script>",
        resp.text,
        re.DOTALL,
    )
    if not match:
        console.print("ERROR: modelJson block not found!")
        sys.exit(1)

    raw_json = match.group(1).strip()
    json_data = json.loads(html.unescape(raw_json))  # handles &quot; → "

    login_url = "https://frs.modares.ac.ir" + json_data["loginUrl"]
    antiforgery = json_data["antiForgery"]["value"]

    login_resp = session.post(
        login_url,
        data={"username": USERNAME, "password": PASSWORD, "idsrv.xsrf": antiforgery},
        allow_redirects=True,
        verify=False,
        headers={
            "Origin": "https://frs.modares.ac.ir",
            "Referer": "https://frs.modares.ac.ir/",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    html2 = login_resp.text

    # استخراج action
    action_match = re.search(r'<form[^>]*action="([^"]+)"', html2)
    if not action_match:
        console.print("No form action found!")
        sys.exit(1)

    form_action = action_match.group(1)

    # استخراج همه فیلدهای hidden
    inputs = re.findall(
        r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html2
    )

    form_data = {name: value for name, value in inputs}

    final_resp = session.post(
        form_action,
        data=form_data,
        allow_redirects=True,
        verify=False,
        headers={
            "Origin": "https://frs.modares.ac.ir",
            "Referer": form_action,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    # Save final page
    # Success check (same as your fish script)
    if any(
        keyword in final_resp.text.lower()
        for keyword in [
            "خروج",
            "رزرو غذا",
            "داشبورد",
            "خوش آمدید",
            "food-reserve",
            "logout",
        ]
    ):
        return True
    return False


def get_shamsi_saturday(greg_date=None):
    if greg_date is None:
        greg_date = date.today()
    days_to_sat = (greg_date.weekday() + 1) % 7
    saturday = greg_date - timedelta(days=days_to_sat)
    return jdatetime.date.fromgregorian(date=saturday)


def get_food_data(session, base_saturday_str="", navigation=0):
    params = {}
    if navigation == 0:
        params = {"lastdate": "", "navigation": "0"}
    else:
        params = {"lastdate": base_saturday_str, "navigation": str(navigation * 7)}
    url = f"{BASE_API}?{urlencode(params)}"
    r = session.get(url, verify=False)
    r.raise_for_status()
    return r.json()


def format_price(p):
    return "رایگان" if not p else f"{int(p):,} تومان".replace(",", "٬")


def get_reserved_food(day_data):
    """برگرداندن غذای رزرو شده برای هر وعده (صبحانه هم اضافه شد)"""
    reserved = {"breakfast": None, "lunch": None, "dinner": None}
    for meal in day_data["Meals"]:
        if meal["LastReserved"]:
            name = meal["LastReserved"][0]["FoodName"]
            self_name = meal["LastReserved"][0]["SelfName"]
            price = meal["LastReserved"][0]["Price"]
            text = f"{name} ({self_name}) — {format_price(price)}"
            if meal["MealName"] == "صبحانه":
                reserved["breakfast"] = text
            elif meal["MealName"] == "ناهار":
                reserved["lunch"] = text
            elif meal["MealName"] == "شام":
                reserved["dinner"] = text
    return reserved


def show_week_menu(data, week_offset=0):
    console.clear()
    first_day = data[0]["DayDate"]
    last_day = data[-1]["DayDate"]
    title = f"منوی غذا — هفته {first_day} تا {last_day}"
    if week_offset != 0:
        title += f" ({'+' if week_offset > 0 else ''}{week_offset} هفته)"
    console.rule(f"[bold magenta]{title}[/bold magenta]")

    # جدول با ستون صبحانه
    table = Table(box=box.DOUBLE, show_header=True, header_style="bold cyan")
    table.add_column("روز", width=10, justify="center")
    table.add_column("تاریخ", width=12, justify="center")
    table.add_column("صبحانه", justify="right", style="dim")
    table.add_column("ناهار", justify="right")
    table.add_column("شام", justify="right")

    for day in data:
        reserved = get_reserved_food(day)

        # صبحانه
        breakfast_text = Text("—")
        breakfast_meal = next(
            (m for m in day["Meals"] if m["MealName"] == "صبحانه"), None
        )
        if breakfast_meal and breakfast_meal["FoodMenu"]:
            if reserved["breakfast"]:
                breakfast_text = Text(reserved["breakfast"], style="bold green")
            else:
                options = " | ".join(f["FoodName"] for f in breakfast_meal["FoodMenu"])
                breakfast_text = Text(options, style="white")

        # ناهار
        lunch_text = Text("—")
        lunch_meal = next((m for m in day["Meals"] if m["MealName"] == "ناهار"), None)
        if lunch_meal and lunch_meal["FoodMenu"]:
            if reserved["lunch"]:
                lunch_text = Text(reserved["lunch"], style="bold green")
            else:
                options = " | ".join(
                    f"{f['FoodName'].split('+')[0].strip()} ({format_price(f['SelfMenu'][0]['Price'])})"
                    for f in lunch_meal["FoodMenu"]
                )
                lunch_text = Text(options, style="yellow")

        # شام
        dinner_text = Text("—")
        dinner_meal = next((m for m in day["Meals"] if m["MealName"] == "شام"), None)
        if dinner_meal and dinner_meal["FoodMenu"]:
            if reserved["dinner"]:
                dinner_text = Text(reserved["dinner"], style="bold green")
            else:
                options = " | ".join(
                    f["FoodName"].split("+")[0].strip() for f in dinner_meal["FoodMenu"]
                )
                dinner_text = Text(options, style="cyan")

        # غیرفعال بودن روز (مثل جمعه)
        if day["DayState"] == 2:
            breakfast_text.stylize("dim")
            lunch_text.stylize("dim")
            dinner_text.stylize("dim")

        table.add_row(
            f"[bold]{day['DayTitle']}[/bold]",
            day["DayDate"],
            breakfast_text,
            lunch_text,
            dinner_text,
        )

    console.print(table)

    # راهنما
    nav = Text()
    nav.append(" [p] قبلی ", "bold white on blue")
    nav.append(" [c] جاری ", "bold white on magenta")
    nav.append(" [n] بعدی ", "bold white on blue")
    nav.append(" [q] خروج ", "bold white on red")
    console.print(Panel(nav, title="ناوبری", border_style="bright_black"))


def save_cookies(session):
    with open(COOKIES_FILE, "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for c in session.cookies:
            domain = c.domain
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path = c.path
            secure = "TRUE" if c.secure else "FALSE"
            expires = str(int(c.expires)) if c.expires else "0"
            f.write(
                f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{c.name}\t{c.value}\n"
            )
    console.print(f"[green]کوکی‌ها ذخیره شد → {COOKIES_FILE}[/green]")


def main():
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) Chrome/130"

    with console.status("[bold blue]در حال ورود...[/bold blue]"):
        if not login(session):
            console.print(
                "[bold red]ورود ناموفق! رمز یا نام کاربری اشتباه است.[/bold red]"
            )
            return
        console.print("[bold green]ورود موفق![/bold green]")

    base_saturday = get_shamsi_saturday()
    base_str = base_saturday.strftime("%Y/%m/%d")
    offset = 0

    try:
        while True:
            data = get_food_data(session, base_str if offset != 0 else "", offset)
            show_week_menu(data, offset)

            key = console.input("\n[bold yellow]دستور → [/bold yellow]").strip().lower()

            if key in ["q", "quit", "exit", "خروج", ""]:
                break
            elif key in ["n", "next", "بعدی"]:
                offset += 1
            elif key in ["p", "prev", "قبلی"]:
                offset -= 1
            elif key in ["c", "current", "جاری"]:
                offset = 0

    except KeyboardInterrupt:
        console.print("\n[yellow]خداحافظ![/yellow]")
    except Exception as e:
        console.print(f"[red]خطا: {e}[/red]")

    save_cookies(session)


if __name__ == "__main__":
    main()
