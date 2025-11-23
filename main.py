#!/usr/bin/env python3
import html
import json
import os
import re
import sys
from datetime import date, timedelta
from urllib.parse import urlencode

import jdatetime
import requests

# ================== CHANGE THESE ==================
USERNAME = "###"  # Your student number
PASSWORD = "###"  # Your password
# ==================================================
COOKIES_FILE = "cookies.txt"
PAGE_FILE = "page.html"
FINAL_FILE = "after_login.html"


def login(session, USERNAME, PASSWORD):
    # Remove old files
    for f in [COOKIES_FILE, PAGE_FILE, FINAL_FILE]:
        if os.path.exists(f):
            os.remove(f)

    print("Getting fresh login page…")
    resp = session.get(
        "https://frs.modares.ac.ir/",  # ← HTTPS! (important now)
        verify=False,
        allow_redirects=True,
    )

    # Save raw page (for debugging like your fish script)
    with open(PAGE_FILE, "w", encoding="utf-8") as f:
        f.write(resp.text)

    # Extract the JSON inside <script id="modelJson">
    match = re.search(
        r"<script id=['\"]modelJson['\"] type=['\"]application/json['\"]>\s*(.*?)\s*</script>",
        resp.text,
        re.DOTALL,
    )
    if not match:
        print("ERROR: modelJson block not found!")
        sys.exit(1)

    raw_json = match.group(1).strip()
    json_data = json.loads(html.unescape(raw_json))  # handles &quot; → "

    login_url = "https://frs.modares.ac.ir" + json_data["loginUrl"]
    antiforgery = json_data["antiForgery"]["value"]

    print("Fresh tokens received:")
    print(f"   loginUrl  → {json_data['loginUrl']}")
    print(f"   antiforgery → {antiforgery[:20]}…")

    print("Logging in…")
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
        print("No form action found!")
        sys.exit(1)

    form_action = action_match.group(1)

    # استخراج همه فیلدهای hidden
    inputs = re.findall(
        r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html2
    )

    form_data = {name: value for name, value in inputs}

    print("Submitting intermediate form…")
    print("Action:", form_action)
    print("Fields:", form_data)

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
    with open(FINAL_FILE, "w", encoding="utf-8") as f:
        f.write(final_resp.text)

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
    #     print("\nSUCCESSFULLY LOGGED IN!")
    #     print("You can now use the session or cookies.txt for everything else.")
    #     food_list = session.get(
    #         "https://frs.modares.ac.ir/api/v0/Reservation?lastdate=&navigation=0"
    #     )
    #     food_list = food_list.json()
    #     with open("sample.json", "w", encoding="utf-8") as f:
    #         json.dump(food_list, f, ensure_ascii=False, indent=4)

    #     # Save cookies in Netscape format (same as curl -c)
    #     def save_cookies_netscape(session, filename):
    #         with open(filename, "w") as f:
    #             f.write("# Netscape HTTP Cookie File\n")
    #             for cookie in session.cookies:
    #                 domain = cookie.domain
    #                 flag = "TRUE" if domain.startswith(".") else "FALSE"
    #                 path = cookie.path
    #                 secure = "TRUE" if cookie.secure else "FALSE"
    #                 expires = str(int(cookie.expires)) if cookie.expires else "0"
    #                 f.write(
    #                     f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{cookie.name}\t{cookie.value}\n"
    #                 )

    #     save_cookies_netscape(session, COOKIES_FILE)
    #     print(f"Cookies saved → {COOKIES_FILE}")

    #     # Example command (just like your fish script)
    #     print("\nExample:")
    #     print(
    #         f"   curl -b {COOKIES_FILE} --insecure 'https://frs.modares.ac.ir/food-reserve'"
    #     )

    # else:
    #     print("\nLogin FAILED")
    #     error_hint = re.search(r'"errorMessage":"([^"]*)"', final_resp.text)
    #     if error_hint:
    #         print("Server says:", html.unescape(error_hint.group(1)))
    #     else:
    #         print("No error message. Maybe wrong username/password?")

    # # Optional: keep files for debugging (just like fish)
    # print(f"\nDebug files: {PAGE_FILE}, {FINAL_FILE}, {COOKIES_FILE}")


def get_food_list(session,date):
    food_list = session.get(
        "https://frs.modares.ac.ir/api/v0/Reservation?" + date
    )
    return food_list.json()


def save_cookies_netscape(session, filename):
    with open(filename, "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for cookie in session.cookies:
            domain = cookie.domain
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path = cookie.path
            secure = "TRUE" if cookie.secure else "FALSE"
            expires = str(int(cookie.expires)) if cookie.expires else "0"
            f.write(
                f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{cookie.name}\t{cookie.value}\n"
            )


def logout(session):
    logout_resp = session.get("https://frs.modares.ac.ir/Home/Logout")
    return logout_resp


def main():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
        }
    )
    login(session, USERNAME, PASSWORD)
    gregorian_today = date.today()
    georgian_weekday = gregorian_today.weekday()
    days_to_saturday = (georgian_weekday + 1) % 7
    first_day_of_week = gregorian_today - timedelta(days=days_to_saturday)
    # Convert to Shamsi/Jalali
    shamsi_today = jdatetime.date.fromgregorian(date=first_day_of_week)

    # Print in YYYY-MM-DD format
    print(shamsi_today)  # e.g., 1404-08-30

    # Or format it nicely (e.g., Persian month names)
    print(shamsi_today.strftime("%Y/%m/%d"))  # 1404/08/30
    urlencoded = urlencode({"lastdate": shamsi_today.strftime("%Y/%m/%d"), "navigation": 7})
    food_list = get_food_list(session, urlencoded)
    print(food_list)
    save_cookies_netscape(session, COOKIES_FILE)

    print("Successfully logged out")


if __name__ == "__main__":
    main()
