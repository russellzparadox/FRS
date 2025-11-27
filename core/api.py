# core/api.py
import html
import json
import re
from urllib.parse import urlencode

import requests
from PyQt6 import QtWidgets

BASE_API = "https://frs.modares.ac.ir/api/v0/Reservation"


class FRSClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        requests.packages.urllib3.disable_warnings()

    def login(self, username: str, password: str) -> bool:
        try:
            resp = self.session.get(
                "https://frs.modares.ac.ir/", verify=False, timeout=15
            )
            resp.raise_for_status()
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "خطا", f"خطا در اتصال: {e}")
            return False

        match = re.search(
            r'<script id=["\']modelJson["\'].*?>(.*?)</script>', resp.text, re.DOTALL
        )
        if not match:
            QtWidgets.QMessageBox.critical(
                None, "خطا", "نتوانستم اطلاعات ورود را استخراج کنم."
            )
            return False

        try:
            data = json.loads(html.unescape(match.group(1)))
        except json.JSONDecodeError:
            QtWidgets.QMessageBox.critical(None, "خطا", "خطا در تجزیه JSON صفحه ورود.")
            return False

        login_url = "https://frs.modares.ac.ir" + data.get("loginUrl", "")
        antiforgery = data.get("antiForgery", {}).get("value", "")

        try:
            r = self.session.post(
                login_url,
                data={
                    "username": username,
                    "password": password,
                    "idsrv.xsrf": antiforgery,
                },
                verify=False,
                headers={
                    "Origin": "https://frs.modares.ac.ir",
                    "Referer": "https://frs.modares.ac.ir/",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            # مرحله دوم SAML
            action = re.search(r'<form[^>]*action="([^"]+)"', r.text)
            if not action:
                return "خروج" in r.text.lower() or "داشبورد" in r.text.lower()

            form_action = action.group(1)
            inputs = re.findall(r'name="([^"]+)"[^>]*value="([^"]*)"', r.text)
            form_data = {k: v for k, v in inputs}

            final = self.session.post(form_action, data=form_data, verify=False)
            return any(
                kw in final.text.lower()
                for kw in ["خروج", "رزرو غذا", "داشبورد", "logout"]
            )

        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "خطا", f"خطای ورود: {e}")
            return False

    def get_week_menu(self, base_saturday: str, offset: int = 0):
        params = (
            {}
            if offset == 0
            else {"lastdate": base_saturday, "navigation": str(offset * 7)}
        )
        url = (
            f"{BASE_API}?{urlencode(params)}"
            if params
            else f"{BASE_API}?lastdate=&navigation=0"
        )
        resp = self.session.get(url, verify=False, timeout=20)
        resp.raise_for_status()
        return resp.json()
