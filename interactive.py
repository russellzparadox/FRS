#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import html
import json
import re
from datetime import date, timedelta
from urllib.parse import urlencode

import jdatetime
import requests
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Footer, Header, Static

requests.packages.urllib3.disable_warnings()

USERNAME = "###"
PASSWORD = "###"
BASE_API = "https://frs.modares.ac.ir/api/v0/Reservation"


class FoodApp(App):
    CSS = """
    Screen {
        align: center top;
    }
    #header { height: 3; background: $primary; }
    #main { height: 1fr; margin: 1 2; }
    DataTable { height: 100%; width: 100%; }
    #details { height: auto; width: 80; margin: 1; padding: 1; background: $surface; }
    #nav { dock: bottom; height: 3; background: $accent; }
    """

    BINDINGS = [
        ("q", "quit", "خروج"),
        ("n", "next_week", "هفته بعد"),
        ("p", "prev_week", "هفته قبل"),
        ("c", "current_week", "هفته جاری"),
    ]

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.week_data = []
        self.current_offset = 0
        self.base_saturday = self.get_shamsi_saturday()

    def get_shamsi_saturday(self):
        today = date.today()
        days_to_sat = (today.weekday() + 1) % 7
        saturday = today - timedelta(days=days_to_sat)
        return jdatetime.date.fromgregorian(date=saturday)

    def login(self) -> bool:
        resp = self.session.get(
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

        raw_json = match.group(1).strip()
        json_data = json.loads(html.unescape(raw_json))  # handles &quot; → "

        login_url = "https://frs.modares.ac.ir" + json_data["loginUrl"]
        antiforgery = json_data["antiForgery"]["value"]

        login_resp = self.session.post(
            login_url,
            data={
                "username": USERNAME,
                "password": PASSWORD,
                "idsrv.xsrf": antiforgery,
            },
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

        form_action = action_match.group(1)

        # استخراج همه فیلدهای hidden
        inputs = re.findall(
            r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html2
        )

        form_data = {name: value for name, value in inputs}

        final_resp = self.session.post(
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

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main"):
            self.table = DataTable(id="week_table")
            yield self.table
            yield Static(id="details", markup=True)
        yield Footer()

    def on_mount(self):
        if not self.login():
            self.exit("ورود ناموفق!")
            return

        self.table.add_columns("روز", "تاریخ", "صبحانه", "ناهار", "شام")
        self.table.cursor_type = "row"
        self.table.zebra_stripes = True
        self.load_week()

    def load_week(self):
        base_str = self.base_saturday.strftime("%Y/%m/%d")
        params = (
            {"lastdate": "", "navigation": "0"}
            if self.current_offset == 0
            else {"lastdate": base_str, "navigation": str(self.current_offset * 7)}
        )
        url = f"{BASE_API}?{urlencode(params)}"
        try:
            data = self.session.get(url, verify=False).json()
            self.week_data = data
            self.update_table()
            self.set_title()
        except:
            self.notify("خطا در دریافت داده", severity="error")

    def update_table(self):
        try:
            self.table.clear()
            print("aaa")
            for day in self.week_data:
                # پیدا کردن رزرو شده‌هاq
                reserved = {}
                for meal in day["Meals"]:
                    if meal["LastReserved"]:
                        r = meal["LastReserved"][0]
                        reserved[meal["MealName"]] = {
                            "name": r["FoodName"],
                            "self": r["SelfName"],
                            "price": r["Price"],
                        }

                breakfast = "—"
                lunch = "—"
                dinner = "—"

                # ساختن متن هر وعده
                for meal in day["Meals"]:
                    name = meal["MealName"]
                    if not meal["FoodMenu"]:  # هیچ غذایی تعریف نشده
                        continue

                    # اگر رزرو شده → فقط همون رو نشون بده
                    if name in reserved:
                        r = reserved[name]
                        text = f"[bold green]● {r['name']} ({r['self']})[/]"
                    else:
                        # همه گزینه‌ها با قیمت
                        options = []
                        for food in meal["FoodMenu"]:
                            # بعضی غذاها چند سلف دارن، اولین رو می‌گیریم (یا می‌تونی انتخاب بدی)
                            price = 0
                            if food["SelfMenu"]:
                                price = food["SelfMenu"][0]["Price"]
                            price_str = self.format_price(price)
                            short_name = food["FoodName"].split("+")[0].strip()
                            options.append(f"{short_name} [dim]{price_str}[/]")
                        text = "[yellow]" + "  |  ".join(options) + "[/]"

                    if name == "صبحانه":
                        breakfast = text
                    elif name == "ناهار":
                        lunch = text
                    elif name == "شام":
                        dinner = text

                # اگر روز تعطیل بود (جمعه یا غیرفعال)
                if day["DayState"] == 2:  # غیرفعال
                    breakfast = f"[dim]{breakfast}[/]"
                    lunch = f"[dim]{lunch}[/]"
                    dinner = f"[dim]{dinner}[/]"

                self.table.add_row(
                    f"[bold]{day['DayTitle']}[/bold]",
                    day["DayDate"],
                    breakfast,
                    lunch,
                    dinner,
                    key=day["DayDate"],
                )
        except:
            self.notify("خطا در بروزرسانی جدول", severity="error")

    def set_title(self):
        start = self.week_data[0]["DayDate"]
        end = self.week_data[-1]["DayDate"]
        title = f"منوی غذا — هفته {start} تا {end}"
        if self.current_offset != 0:
            title += (
                f" ({'+' if self.current_offset > 0 else ''}{self.current_offset} هفته)"
            )
        self.title = title

    @on(DataTable.RowSelected)
    def show_day_details(self, event: DataTable.RowSelected):
        day_date = event.row_key.value
        day = next(d for d in self.week_data if d["DayDate"] == day_date)

        details = (
            f"[bold magenta]جزئیات روز {day['DayTitle']} — {day['DayDate']}[/]\n\n"
        )
        for meal in day["Meals"]:
            if meal["FoodMenu"] or meal["LastReserved"]:
                reserved = meal["LastReserved"][0] if meal["LastReserved"] else None
                status = "[green]رزرو شده[/]" if reserved else "[yellow]قابل رزرو[/]"
                details += f"[bold cyan]{meal['MealName']}[/] {status}\n"
                if reserved:
                    details += f"   → {reserved['FoodName']} ({reserved['SelfName']})\n"
                else:
                    for food in meal["FoodMenu"]:
                        price = food["SelfMenu"][0]["Price"] if food["SelfMenu"] else 0
                        details += (
                            f"   • {food['FoodName']} — {self.format_price(price)}\n"
                        )
                details += "\n"
        self.query_one("#details").update(details)

    def format_price(self, p):
        return "رایگان" if not p else f"{int(p):,} تومان".replace(",", "٬")

    def action_next_week(self):
        self.current_offset += 1
        self.load_week()

    def action_prev_week(self):
        self.current_offset -= 1
        self.load_week()

    def action_current_week(self):
        self.current_offset = 0
        self.load_week()


if __name__ == "__main__":
    FoodApp().run()
