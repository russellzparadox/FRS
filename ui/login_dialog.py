# gui/login_dialog.py
from PyQt6 import QtCore, QtWidgets


class LoginDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ورود به سیستم رزرو غذا")
        self.setModal(True)
        self.resize(360, 160)

        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("لطفاً اطلاعات ورود خود را وارد کنید")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        font = title.font()
        font.setPointSize(12)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        self.username = QtWidgets.QLineEdit()
        self.username.setPlaceholderText("مثال: 401211000")
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("رمز عبور یکتا")

        form.addRow("شماره دانشجویی:", self.username)
        form.addRow("رمز عبور:", self.password)
        layout.addLayout(form)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        login_btn = QtWidgets.QPushButton("ورود")
        login_btn.setDefault(True)
        login_btn.clicked.connect(self.accept)
        buttons.addWidget(login_btn)
        layout.addLayout(buttons)

    def get_credentials(self):
        return self.username.text().strip(), self.password.text().strip()
