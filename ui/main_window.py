# gui/main_window.py
from PyQt6 import QtCore, QtGui, QtWidgets

from core.api import FRSClient
from core.utils import escape, format_price, get_shamsi_saturday


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("منوی غذا — دانشگاه تربیت مدرس")
        self.resize(1150, 700)

        self.client = FRSClient()
        self.base_saturday = get_shamsi_saturday()
        self.current_offset = 0
        self.week_data = []
        self.checkboxes = []  # (checkbox, price, meal_info)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # کنترل‌های بالا
        controls = QtWidgets.QHBoxLayout()
        self.prev_btn = QtWidgets.QPushButton("◀ هفته قبل")
        self.current_btn = QtWidgets.QPushButton("هفته جاری")
        self.next_btn = QtWidgets.QPushButton("هفته بعد ▶")
        for btn in (self.prev_btn, self.current_btn, self.next_btn):
            btn.setFixedHeight(38)
            btn.setStyleSheet("font-size: 14px;")
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.current_btn)
        controls.addWidget(self.next_btn)
        controls.addStretch()
        layout.addLayout(controls)

        # جدول + پنل راست
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        # جدول منو
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["روز", "تاریخ", "صبحانه", "ناهار", "شام"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        splitter.addWidget(self.table)

        # پنل راست: جزئیات + جمع قیمت
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)

        self.details = QtWidgets.QTextEdit()
        self.details.setReadOnly(True)
        self.details.setStyleSheet("font-size: 13px; background:#fdfdfd;")
        right_layout.addWidget(self.details, 1)

        # جمع قیمت
        summary_frame = QtWidgets.QFrame()
        summary_frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        summary_frame.setStyleSheet(
            "QFrame { background:#f9f9f9; border-top: 2px solid #d33682; }"
        )
        summary_layout = QtWidgets.QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(12, 10, 12, 10)

        self.summary_label = QtWidgets.QLabel("غذا انتخاب نشده")
        self.summary_label.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #d33682;"
        )
        summary_layout.addWidget(self.summary_label)

        summary_layout.addStretch()

        self.reset_btn = QtWidgets.QPushButton("ریست انتخاب‌ها")
        self.reset_btn.setFixedHeight(34)
        self.reset_btn.setStyleSheet("font-weight: bold;")
        self.reset_btn.clicked.connect(self.reset_selections)
        summary_layout.addWidget(self.reset_btn)

        right_layout.addWidget(summary_frame)
        splitter.addWidget(right)
        splitter.setSizes([780, 370])

        self.statusBar().showMessage("آماده")

    def _connect_signals(self):
        self.prev_btn.clicked.connect(self.prev_week)
        self.next_btn.clicked.connect(self.next_week)
        self.current_btn.clicked.connect(self.current_week)
        self.table.cellClicked.connect(self.on_cell_clicked)

        # کلیدهای میانبر
        shortcuts = [
            ("q", self.close),
            ("n", self.next_week),
            ("p", self.prev_week),
            ("c", self.current_week),
            ("r", self.reset_selections),
        ]
        for key, slot in shortcuts:
            QtGui.QShortcut(QtGui.QKeySequence(key), self, activated=slot)

    def load_week(self):
        self.statusBar().showMessage("در حال دریافت منو...")
        QtWidgets.QApplication.processEvents()

        base_str = self.base_saturday.strftime("%Y/%m/%d")
        try:
            self.week_data = self.client.get_week_menu(base_str, self.current_offset)
            self.update_table()
            self.update_title()
            self.statusBar().showMessage("منو با موفقیت بارگذاری شد", 5000)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", f"دریافت منو ناموفق بود:\n{e}")
            self.statusBar().showMessage("خطا در بارگذاری")

    def update_table(self):
        # پاک کردن چک‌باکس‌های قبلی
        for cb, _, _ in self.checkboxes:
            cb.setParent(None)
        self.checkboxes.clear()
        self.reset_selections()

        self.table.setRowCount(0)
        for day in self.week_data:
            row = self.table.rowCount()
            self.table.insertRow(row)

            date_item = QtWidgets.QTableWidgetItem(day.get("DayDate", ""))
            date_item.setData(QtCore.Qt.ItemDataRole.UserRole, day.get("DayDate"))
            self.table.setItem(
                row, 0, QtWidgets.QTableWidgetItem(day.get("DayTitle", ""))
            )
            self.table.setItem(row, 1, date_item)

            reserved = {
                m["MealName"]: m["LastReserved"][0]
                for m in day.get("Meals", [])
                if m.get("LastReserved")
            }

            for col, meal_name in enumerate(["صبحانه", "ناهار", "شام"], 2):
                meal = next(
                    (m for m in day["Meals"] if m.get("MealName") == meal_name), None
                )
                widget = self.render_meal_widget(
                    meal,
                    reserved.get(meal_name),
                    day.get("DayState") == 2,
                    day,
                    meal_name,
                )
                self.table.setCellWidget(row, col, widget)

        self.table.resizeRowsToContents()

    def render_meal_widget(
        self, meal, reserved, inactive=False, day=None, meal_name=None
    ):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(5)

        if not meal or not meal.get("FoodMenu"):
            lbl = QtWidgets.QLabel("—")
            lbl.setStyleSheet("color:#999;")
            layout.addWidget(lbl)
            return container

        if reserved:
            text = f'<span style="color:green;font-weight:bold">● رزرو شده:</span> {escape(reserved["FoodName"])} ({escape(reserved["SelfName"])})'
            lbl = QtWidgets.QLabel(text)
            lbl.setTextFormat(QtCore.Qt.TextFormat.RichText)
            layout.addWidget(lbl)
            return container

        if inactive:
            lbl = QtWidgets.QLabel("تعطیل / غیرقابل رزرو")
            lbl.setStyleSheet("color:#888;")
            layout.addWidget(lbl)
            return container

        # غذاهای قابل رزرو → چک‌باکس
        for food in meal["FoodMenu"]:
            price = food["SelfMenu"][0]["Price"] if food.get("SelfMenu") else 0
            food_name = food["FoodName"]
            self_name = (
                food["SelfMenu"][0]["SelfName"] if food.get("SelfMenu") else "نامشخص"
            )

            hbox = QtWidgets.QHBoxLayout()
            cb = QtWidgets.QCheckBox()
            cb.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; }")

            label_text = f"{escape(food_name)} <small style='color:#555'>— {format_price(price)} ({escape(self_name)})</small>"
            lbl = QtWidgets.QLabel(label_text)
            lbl.setTextFormat(QtCore.Qt.TextFormat.RichText)
            lbl.setWordWrap(True)

            hbox.addWidget(cb)
            hbox.addWidget(lbl, 1)
            layout.addLayout(hbox)

            meal_info = {
                "day": day["DayTitle"],
                "date": day["DayDate"],
                "meal": meal_name,
                "food": food_name,
                "self": self_name,
                "price": price,
            }
            self.checkboxes.append((cb, price, meal_info))
            cb.toggled.connect(self.update_summary)

        layout.addStretch()
        return container

    def update_summary(self):
        total = sum(price for cb, price, _ in self.checkboxes if cb.isChecked())
        count = sum(1 for cb, _, _ in self.checkboxes if cb.isChecked())

        if count == 0:
            text = "غذا انتخاب نشده"
        elif count == 1:
            text = f"جمع قیمت: <b>{format_price(total)}</b> — یک غذا انتخاب شده"
        else:
            text = f"جمع قیمت: <b>{format_price(total)}</b> — <b>{count}</b> غذا انتخاب شده"

        self.summary_label.setText(text)

    def reset_selections(self):
        for cb, _, _ in self.checkboxes:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self.update_summary()

    def update_title(self):
        if not self.week_data:
            self.setWindowTitle("منوی غذا — دانشگاه تربیت مدرس")
            return
        start = self.week_data[0]["DayDate"]
        end = self.week_data[-1]["DayDate"]
        title = f"منوی غذا — هفته {start} تا {end}"
        if self.current_offset:
            title += (
                f" ({'+' if self.current_offset > 0 else ''}{self.current_offset} هفته)"
            )
        self.setWindowTitle(title)

    def on_cell_clicked(self, row, col):
        date = self.table.item(row, 1).data(QtCore.Qt.ItemDataRole.UserRole)
        day = next((d for d in self.week_data if d["DayDate"] == date), None)
        if not day:
            return

        html = f"<h3 style='color:#d33682'>جزئیات {escape(day['DayTitle'])} — {escape(day['DayDate'])}</h3>"
        for meal in day.get("Meals", []):
            if not meal.get("FoodMenu") and not meal.get("LastReserved"):
                continue
            reserved = meal["LastReserved"][0] if meal.get("LastReserved") else None
            status = "رزرو شده" if reserved else "قابل رزرو"
            color = "green" if reserved else "orange"
            html += f"<b style='color:teal'>{escape(meal['MealName'])}</b> <span style='color:{color}'>[{status}]</span><br>"
            if reserved:
                html += f"&nbsp;&nbsp;→ {escape(reserved['FoodName'])} ({escape(reserved['SelfName'])})<br>"
            else:
                for food in meal["FoodMenu"]:
                    price = food["SelfMenu"][0]["Price"] if food.get("SelfMenu") else 0
                    html += f"&nbsp;&nbsp;• {escape(food['FoodName'])} — {format_price(price)}<br>"
            html += "<br>"
        self.details.setHtml(html)

    def prev_week(self):
        self.current_offset -= 1
        self.load_week()

    def next_week(self):
        self.current_offset += 1
        self.load_week()

    def current_week(self):
        self.current_offset = 0
        self.load_week()
