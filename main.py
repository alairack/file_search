import sys
import os
from PyQt5 import QtGui, QtWidgets, Qt, QtCore
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QMessageBox, QComboBox
from file_search import search_file
import pickle


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.setWindowTitle("file search")
        self.resize(1000, 800)

        self.search_frame = QtWidgets.QLineEdit()
        self.search_frame.setAlignment(QtCore.Qt.AlignLeft)

        search_button = QtWidgets.QPushButton("搜索")
        search_button.clicked.connect(self.click_search_button)

        self.combobox = QComboBox(self)
        self.combobox.setLineEdit(self.search_frame)
        self.combobox.setMinimumWidth(self.width()-60)
        self.combobox.setMinimumHeight(26)
        self.combobox.activated.connect(self.choose_history)

        view = QtWidgets.QListView(self.combobox)
        view.setMinimumHeight(420)

        self.combobox.setView(view)

        hbox_layout = QtWidgets.QHBoxLayout()
        hbox_layout.setSpacing(30)
        hbox_layout.addWidget(self.combobox, alignment=QtCore.Qt.AlignRight)
        hbox_layout.addWidget(search_button, alignment=QtCore.Qt.AlignRight)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.setSpacing(15)
        vbox_layout.addLayout(hbox_layout)

        # 初始化table_widget
        self.table_widget = ShowResultsTable()
        self.table_widget.setRowCount(19)
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["文件名", "路径", '创建时间', "修改时间"])
        self.table_widget.setColumnWidth(0, 200)
        self.table_widget.setColumnWidth(1, 300)
        self.table_widget.setColumnWidth(2, 250)
        self.table_widget.doubleClicked.connect(self.table_widget.open_click_file)

        widget = QtWidgets.QWidget()
        widget.setLayout(vbox_layout)

        self.statusBar().showMessage("0个对象")

        vbox_layout.addWidget(self.table_widget)
        self.setCentralWidget(widget)
        self.history = History(self.combobox)

    def click_search_button(self):
        self.history.save_history(self.search_frame.text())
        file_name = self.search_frame.text()
        if file_name == "":
            QMessageBox.warning(self, "警告", "你还没有输入文件名", buttons=QMessageBox.Ok)
        else:
            self.threadpool = QtCore.QThreadPool()
            self.file_search_thread = FileSearchThread(file_name)
            self.threadpool.start(self.file_search_thread)
            self.file_search_thread.signals.finished.connect(self.file_search_finish)

    def file_search_finish(self):
        self.table_widget.clearContents()
        if len(self.file_search_thread.result) > self.table_widget.rowCount():
            self.table_widget.setRowCount(len(self.file_search_thread.result))
        for i, info_list in enumerate(self.file_search_thread.result):
            for j, info in enumerate(info_list):
                table_cell = QTableWidgetItem(info)
                table_cell.setToolTip(info)
                if j == 0:
                    file_icon = QtWidgets.QFileIconProvider().icon(QtCore.QFileInfo(info_list[1]))
                    table_cell.setIcon(file_icon)
                self.table_widget.setItem(i, j, table_cell)
        self.statusBar().showMessage(f"{len(self.file_search_thread.result)}个对象")

    def choose_history(self, event):
        choose_text = self.combobox.itemText(event)
        self.search_frame.setText(choose_text)


class ShowResultsTable(QtWidgets.QTableWidget):
    def __init__(self):
        super(ShowResultsTable, self).__init__()

        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

    def open_click_file(self, index):
        row = index.row()
        col = index.column()
        if col == 0:
            try:
                file_path = self.item(row, 1).text()
                os.startfile(file_path)
            except Exception:
                pass


class FileSearchThread(QtCore.QRunnable):
    def __init__(self, file_name):
        super(FileSearchThread, self).__init__()
        self.file_name = file_name
        self.result = None
        self.signals = Signals()

    @QtCore.pyqtSlot()
    def run(self):
        self.result = search_file(self.file_name, [])
        self.signals.finished.emit()


class History(object):
    def __init__(self, combobox):
        self.history_number = None
        self.max_history_number = 20
        appdata_path = os.getenv("APPDATA")
        self.app_dir_path = os.path.join(appdata_path, "file_search")
        self.history_file_path = os.path.join(self.app_dir_path, "history.pickle")
        self.combobox = combobox
        self.init_combobox()

    def init_combobox(self):
        history = self.read_history()
        if history is not None:
            self.combobox.addItems(history)

    def save_history(self, text):
        current_history = self.read_history()
        if current_history is None:
            current_history = [text]
        else:
            if self.history_number == self.max_history_number:
                current_history.pop(-1)
            current_history.insert(0, text)
        self.combobox.clear()
        self.combobox.addItems(current_history)
        with open(self.history_file_path, "wb") as f:
            pickle.dump(current_history, f)

    def read_history(self):
        if not os.path.isdir(self.app_dir_path):
            os.mkdir(self.app_dir_path)
        if not os.path.isfile(self.history_file_path):
            with open(self.history_file_path, "wb+") as f:
                pass
            self.history_number = 0
            return None
        else:
            with open(self.history_file_path, "rb") as f:
                try:
                    file_data = pickle.load(f)
                    if file_data is not None:
                        self.history_number = len(file_data)
                except EOFError:
                    return None
            return file_data


class Signals(QtCore.QObject):
    finished = QtCore.pyqtSignal()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("logo.ico"))
    main_window = MainWindow(None)

    main_window.show()
    sys.exit(app.exec_())
