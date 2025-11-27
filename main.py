# main.py
import sys

from PyQt6 import QtWidgets

from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")  # ظاهر بهتر

    win = MainWindow()

    # ورود
    login = LoginDialog()
    if login.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        sys.exit(0)

    username, password = login.get_credentials()
    if not username or not password:
        QtWidgets.QMessageBox.critical(None, "خطا", "نام کاربری و رمز عبور الزامی است.")
        sys.exit(1)

    win.statusBar().showMessage("در حال ورود...")
    QtWidgets.QApplication.processEvents()

    if not win.client.login(username, password):
        QtWidgets.QMessageBox.critical(
            None, "ورود ناموفق", "نام کاربری یا رمز عبور اشتباه است."
        )
        sys.exit(1)

    win.load_week()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
