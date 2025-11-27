# gui/main_window.py
from PyQt6 import QtCore, QtGui, QtWidgets

from core.api import FRSClient
from core.utils import escape, format_price, get_shamsi_saturday


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("منوی غذا — دانشگاه تربیت مدرس")
        self.resize(1100, 650)

        self.client = FRSClient()
        self.base_saturday = get_shamsi_saturday()
        self.current_offset = 0
        self.week_data = []

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # کنترل‌ها
        controls = QtWidgets.QHBoxLayout()
        self.prev_btn = QtWidgets.QPushButton("◀ هفته قبل")
        self.current_btn = QtWidgets.QPushButton("هفته جاری")
        self.next_btn = QtWidgets.QPushButton("هفته بعد ▶")
        for btn in (self.prev_btn, self.current_btn, self.next_btn):
            btn.setFixedHeight(36)
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.current_btn)
        controls.addWidget(self.next_btn)
        controls.addStretch()
        layout.addLayout(controls)

        # جدول + جزئیات
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

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

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        self.details = QtWidgets.QTextEdit()
        self.details.setReadOnly(True)
        self.details.setStyleSheet("font-size: 13px;")
        right_layout.addWidget(self.details)
        splitter.addWidget(right)
        splitter.setSizes([750, 350])

        self.statusBar().showMessage("آماده")

    def _connect_signals(self):
        self.prev_btn.clicked.connect(self.prev_week)
        self.next_btn.clicked.connect(self.next_week)
        self.current_btn.clicked.connect(self.current_week)
        self.table.cellClicked.connect(self.on_cell_clicked)

        # کلیدهای میانبر
        for key, slot in [
            ("q", self.close),
            ("n", self.next_week),
            ("p", self.prev_week),
            ("c", self.current_week),
        ]:
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
            QtWidgets.QMessageBox.critical(self, "خطا", f"دریافت منو失敗: {e}")
            self.statusBar().showMessage("خطا در بارگذاری")

    def update_table(self):
        self.table.setRowCount(0)
        for day in self.week_data:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ذخیره تاریخ برای جزئیات
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
                html = self.render_meal(
                    meal, reserved.get(meal_name), day.get("DayState") == 2
                )
                label = QtWidgets.QLabel(html)
                label.setTextFormat(QtCore.Qt.TextFormat.RichText)
                label.setWordWrap(True)
                label.setContentsMargins(6, 4, 6, 4)
                self.table.setCellWidget(row, col, label)

        self.table.resizeRowsToContents()

    def render_meal(self, meal, reserved, inactive=False):
        if not meal or not meal.get("FoodMenu"):
            text = "—"
        elif reserved:
            text = f'<span style="color:green;font-weight:bold">●</span> {escape(reserved["FoodName"])} ({escape(reserved["SelfName"])})'
        else:
            items = []
            for food in meal["FoodMenu"]:
                price = food["SelfMenu"][0]["Price"] if food.get("SelfMenu") else 0
                short = food["FoodName"].split("+")[0].strip()
                items.append(f"{escape(short)} <small>({format_price(price)})</small>")
            text = " | ".join(items) or "—"

        if inactive:
            text = f'<span style="color:#888">{text}</span>'
        return text

    def update_title(self):
        if not self.week_data:
            self.setWindowTitle("منوی غذا — FRS")
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
