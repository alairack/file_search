import sys
import os
from PyQt5 import QtGui, QtWidgets, Qt, QtCore
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QMessageBox
from file_search import search_file


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.setWindowTitle("file search")
        self.resize(1000, 800)

        self.search_frame = QtWidgets.QLineEdit()
        self.search_frame.setMinimumHeight(27)

        hbox_layout = QtWidgets.QHBoxLayout()
        hbox_layout.addWidget(self.search_frame, alignment=QtCore.Qt.AlignTop)

        search_button = QtWidgets.QPushButton("搜索")
        search_button.clicked.connect(self.click_search_button)

        hbox_layout.addWidget(search_button)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addLayout(hbox_layout)

        # 初始化table_widget
        self.table_widget = ShowResultsTable()
        self.table_widget.setRowCount(19)
        self.table_widget.setColumnCount(4)
        self.table_widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table_widget.setHorizontalHeaderLabels(["文件名", "路径", '创建时间', "修改时间"])
        self.table_widget.setColumnWidth(0, 200)
        self.table_widget.setColumnWidth(1, 300)
        self.table_widget.setColumnWidth(2, 250)
        self.table_widget.doubleClicked.connect(self.open_click_file)

        widget = QtWidgets.QWidget()
        widget.setLayout(vbox_layout)

        menu = self.menuBar()
        history_menu = menu.addMenu("history")

        self.statusBar().showMessage("0个对象")

        vbox_layout.addWidget(self.table_widget)
        self.setCentralWidget(widget)

    def click_search_button(self):
        file_name = self.search_frame.text()
        if file_name == "":
            QMessageBox.warning(self, "警告", "你还没有输入文件名", buttons=QMessageBox.Ok)
        else:
            self.threadpool = QtCore.QThreadPool()
            self.file_search_thread = FileSearchThread(file_name)
            self.threadpool.start(self.file_search_thread)
            self.file_search_thread.signals.finished.connect(self.file_search_finish)

    def file_search_finish(self):
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

    def open_click_file(self, index):
        row = index.row()
        col = index.column()
        if col == 0:
            try:
                file_path = self.table_widget.item(row, 1).text()
                os.startfile(file_path)
            except Exception:
                pass


class ShowResultsTable(QtWidgets.QTableWidget):
    def __init__(self):
        super(ShowResultsTable, self).__init__()

        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)


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


class Signals(QtCore.QObject):
    finished = QtCore.pyqtSignal()


app = QtWidgets.QApplication(sys.argv)
app.setWindowIcon(QtGui.QIcon("logo.ico"))
main_window = MainWindow(None)

main_window.show()
sys.exit(app.exec_())
