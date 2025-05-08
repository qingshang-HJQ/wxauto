import sys
import re
import itchat
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTextEdit, QCheckBox,
                             QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox, QLabel)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QMetaObject, Qt, Q_ARG


# 自定义信号类（确保信号在全局作用域可访问）
class BotSignals(QObject):
    status_updated = pyqtSignal(str)  # 定义信号


class WechatBot(QThread):
    def __init__(self):
        super().__init__()
        self.signals = BotSignals()  # 实例化信号对象
        self.rules = []  # 存储匹配规则
        self.auto_accept = False  # 自动同意好友
        self.running = True

    def run(self):
        @itchat.msg_register(itchat.content.TEXT, isFriendChat=True, isGroupChat=True)
        def text_reply(msg):
            if not self.running:
                return
            content = msg['Text']
            sender = msg['User']['NickName'] if 'User' in msg else msg['ActualNickName']

            # 匹配规则
            for rule in self.rules:
                pattern = re.compile(rule['keyword'], re.IGNORECASE)
                if pattern.search(content):
                    reply = rule['reply']
                    itchat.send(reply, toUserName=msg['FromUserName'])
                    # 通过信号发射状态更新
                    QMetaObject.invokeMethod(
                        self.signals,
                        "status_updated",
                        Qt.QueuedConnection,
                        Q_ARG(str, f"[{sender}] 触发规则: {rule['keyword']} → 已回复")
                    )
                    break

        @itchat.msg_register(itchat.content.FRIENDS)
        def add_friend(msg):
            if self.auto_accept:
                itchat.add_friend(msg['RecommendInfo']['UserName'], status=2)
                itchat.send_msg("已自动同意好友请求", msg['RecommendInfo']['UserName'])
                # 通过信号发射状态更新
                QMetaObject.invokeMethod(
                    self.signals,
                    "status_updated",
                    Qt.QueuedConnection,
                    Q_ARG(str, f"已自动同意好友: {msg['RecommendInfo']['NickName']}")
                )
                # 设置备注
                if hasattr(self, 'remark_rule') and self.remark_rule:
                    itchat.update_friend(msg['RecommendInfo']['UserName'], remarkName=self.remark_rule)

        itchat.auto_login(hotReload=True, enableCmdQR=2)
        itchat.run()

    def add_rule(self, keyword, reply):
        self.rules.append({'keyword': keyword, 'reply': reply})

    def set_auto_accept(self, enabled, remark=""):
        self.auto_accept = enabled
        self.remark_rule = remark


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bot = WechatBot()
        self.bot.signals.status_updated.connect(self.update_status)  # 连接信号
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("微信自动化机器人")
        self.setGeometry(100, 100, 800, 600)

        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 规则管理区域
        rule_group = QWidget()
        rule_layout = QVBoxLayout(rule_group)

        self.rule_table = QTableWidget()
        self.rule_table.setColumnCount(2)
        self.rule_table.setHorizontalHeaderLabels(["关键词", "回复内容"])
        self.rule_table.horizontalHeader().setStretchLastSection(True)

        self.add_rule_btn = QPushButton("添加规则")
        self.add_rule_btn.clicked.connect(self.show_rule_dialog)

        rule_layout.addWidget(QLabel("匹配规则管理："))
        rule_layout.addWidget(self.rule_table)
        rule_layout.addWidget(self.add_rule_btn)

        # 自动同意设置
        auto_group = QWidget()
        auto_layout = QHBoxLayout(auto_group)

        self.auto_accept_cb = QCheckBox("自动同意好友请求")
        self.auto_accept_cb.toggled.connect(lambda checked: self.show_remark_input(checked))

        self.remark_input = QLineEdit()
        self.remark_input.setPlaceholderText("自动设置备注（可选）")
        self.remark_input.setEnabled(False)

        auto_layout.addWidget(self.auto_accept_cb)
        auto_layout.addWidget(self.remark_input)

        # 状态显示
        self.status_bar = self.addToolBar("状态")
        self.status_label = QLabel("未连接")
        self.status_bar.addWidget(self.status_label)

        # 控制按钮
        control_group = QWidget()
        control_layout = QHBoxLayout(control_group)

        self.start_btn = QPushButton("启动机器人")
        self.stop_btn = QPushButton("停止机器人")
        self.start_btn.clicked.connect(self.start_bot)
        self.stop_btn.clicked.connect(self.stop_bot)
        self.stop_btn.setEnabled(False)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        # 组合布局
        main_layout.addWidget(rule_group)
        main_layout.addWidget(auto_group)
        main_layout.addWidget(control_group)

    def show_rule_dialog(self):
        dialog = QWidget()
        dialog.setWindowTitle("添加规则")
        layout = QVBoxLayout(dialog)

        keyword_input = QLineEdit()
        keyword_input.setPlaceholderText("输入关键词（支持正则表达式）")

        reply_input = QTextEdit()
        reply_input.setPlaceholderText("输入回复内容（支持换行）")

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(lambda: self.save_rule(keyword_input.text(), reply_input.toPlainText()))

        layout.addWidget(QLabel("关键词："))
        layout.addWidget(keyword_input)
        layout.addWidget(QLabel("回复内容："))
        layout.addWidget(reply_input)
        layout.addWidget(save_btn)

        dialog.exec_()

    def save_rule(self, keyword, reply):
        if keyword and reply:
            row_position = self.rule_table.rowCount()
            self.rule_table.insertRow(row_position)
            self.rule_table.setItem(row_position, 0, QTableWidgetItem(keyword))
            self.rule_table.setItem(row_position, 1, QTableWidgetItem(reply))

    def show_remark_input(self, checked):
        self.remark_input.setEnabled(checked)

    def start_bot(self):
        self.bot.add_rule("[天气]", "今天北京晴，气温25℃")
        self.bot.set_auto_accept(self.auto_accept_cb.isChecked(), self.remark_input.text())
        self.bot.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("机器人正在运行...")

    def stop_bot(self):
        self.bot.running = False
        self.bot.terminate()
        self.bot.wait()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("已停止")

    def update_status(self, message):
        self.status_label.setText(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())