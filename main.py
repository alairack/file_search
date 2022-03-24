import sys
import os
from PyQt5 import QtGui, QtWidgets, Qt, QtCore
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QSizePolicy, QSplitter, \
    QAbstractItemView
import time
import pickle
import ctypes
import resource
import subprocess
from functools import partial
from preview_area import PreviewArea


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.setWindowTitle("File Search")
        self.resize(1000, 800)

        self.search_frame = QtWidgets.QLineEdit()
        self.search_frame.setAlignment(QtCore.Qt.AlignLeft)

        self.search_button = QtWidgets.QPushButton("搜索")
        self.search_button.clicked.connect(self.click_search_button)

        self.choose_search_dir_button = QtWidgets.QPushButton("选择路径")
        self.choose_search_dir_button.clicked.connect(self.choose_search_dir)

        self.combobox = QComboBox(self)
        self.combobox.setLineEdit(self.search_frame)
        self.combobox.setMinimumWidth(self.width()-60)
        self.combobox.setMinimumHeight(26)
        self.combobox.setCompleter(None)
        self.combobox.activated.connect(self.choose_history)

        view = QtWidgets.QListView(self.combobox)
        view.setMinimumHeight(420)

        self.combobox.setView(view)

        hbox_layout = QtWidgets.QHBoxLayout()
        hbox_layout.addWidget(self.combobox, stretch=0, alignment=QtCore.Qt.AlignRight)
        hbox_layout.addWidget(self.choose_search_dir_button, alignment=QtCore.Qt.AlignRight)
        hbox_layout.addWidget(self.search_button, stretch=0, alignment=QtCore.Qt.AlignRight)
        hbox_layout.addStretch(10)

        # 初始化table_widget
        self.table_widget = ShowResultsTable(mainWindow=self)
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["文件名", "路径", '创建时间', "修改时间"])
        self.table_widget.doubleClicked.connect(self.table_widget.open_click_file)
        self.table_widget.cellClicked.connect(self.preview_table_cell)
        # 右键菜单策略
        # self.table_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        # 下面的方法对于调整大小很重要
        self.table_widget.horizontalHeader().resizeSections(QtWidgets.QHeaderView.Stretch)

        self.preview_area = PreviewArea()
        self.preview_area.hide()         # 默认隐藏

        self.splitter = QSplitter()

        self.splitter.addWidget(self.table_widget)
        self.splitter.addWidget(self.preview_area)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.setSpacing(15)
        vbox_layout.addLayout(hbox_layout)
        vbox_layout.addWidget(self.splitter)

        widget = QtWidgets.QWidget()
        widget.setLayout(vbox_layout)

        self.search_path = "/"
        self.info_number = 0

        self.update_statusbar()

        self.setCentralWidget(widget)
        self.history = History(self.combobox)

        self.file_search_thread = None

    def click_search_button(self):
        self.search_button.setEnabled(False)
        self.search_button.setText("正在搜索")
        self.history.save_history(self.search_frame.text())
        file_name = self.search_frame.text()
        if file_name == "":
            QMessageBox.warning(self, "警告", "你还没有输入文件名", buttons=QMessageBox.Ok)
        else:
            self.threadpool = QtCore.QThreadPool()
            self.file_search_thread = FileSearchThread(file_name, self.search_path)
            self.threadpool.start(self.file_search_thread)
            self.file_search_thread.signals.finished.connect(self.file_search_finish)

    def choose_search_dir(self):
        dir_choose = QtWidgets.QFileDialog.getExistingDirectory(self, "选取搜索文件夹")
        if dir_choose != "":
            self.search_path = dir_choose
        else:
            self.search_path = "/"
        self.update_statusbar()

    def file_search_finish(self):
        self.table_widget.clearContents()
        self.table_widget.setRowCount(0)
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

        self.info_number = len(self.file_search_thread.result)
        self.update_statusbar()
        self.search_button.setText("搜索")
        self.table_widget.horizontalHeader().resizeSections(QtWidgets.QHeaderView.Stretch)
        self.search_button.setEnabled(True)
        self.file_search_thread.is_running = False

    def choose_history(self, event):
        choose_text = self.combobox.itemText(event)
        self.search_frame.setText(choose_text)

    def closeEvent(self, event):
        event.accept()
        if self.preview_area.video_player is not None:
            self.preview_area.video_player.close()
        if self.preview_area.audio_player is not None:
            self.preview_area.audio_player.close()
        if self.file_search_thread is not None:
            if self.file_search_thread.is_running:
                self.file_search_thread.is_running = False

    def preview_table_cell(self, row, col):
        if col == 0:
            try:
                file_name = self.table_widget.item(row, col).text()
            except Exception:
                pass
            else:
                file_name_extension = file_name.split(".")[-1]
                if file_name_extension in self.preview_area.support_formats["text"]:
                    self.preview_area.show_text(self.table_widget.item(row, 1).text())
                elif file_name_extension in self.preview_area.support_formats["image"]:
                    self.preview_area.show_image(self.table_widget.item(row, 1).text())
                elif file_name_extension in self.preview_area.support_formats["audio"]:
                    self.preview_area.play_audio(self.table_widget.item(row, 1).text(), True)
                elif file_name_extension in self.preview_area.support_formats["video"]:
                    self.preview_area.open_video(self.table_widget.item(row, 1).text())


    def update_statusbar(self):
        """
        更新状态栏以显示最新信息数量及搜索路径
        """
        self.statusBar().showMessage(f"{self.info_number}个对象       {self.search_path}")


class ShowResultsTable(QTableWidget):
    def __init__(self, mainWindow):
        super(ShowResultsTable, self).__init__()

        self.mainWindow = mainWindow
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def open_click_file(self, index):
        row = index.row()
        col = index.column()
        if col == 0:
            try:
                file_path = self.item(row, 1).text()
                os.startfile(file_path)
            except Exception:
                pass

    def open_folder(self, index):
        row = index.row()
        try:
            file_path = self.item(row, 1).text()
            cmd = 'explorer.exe /select, "{}", vbNormalFocus'.format(file_path)
            si = subprocess.STARTUPINFO()
            si.wShowWindow = subprocess.SW_HIDE
            subprocess.call(cmd, startupinfo=si)
        except Exception:
            pass

    def contextMenuEvent(self, event):
        index = self.currentIndex()
        menu = QtWidgets.QMenu(self)

        default_open_file = QtWidgets.QAction("使用默认应用打开文件")
        default_open_file.triggered.connect(partial(self.open_click_file, index))
        open_dir = QtWidgets.QAction("打开文件目录")
        open_dir.triggered.connect(partial(self.open_folder, index))

        open_audio = QtWidgets.QAction("在音频播放器中播放")
        open_audio.triggered.connect(partial(self.press_open_media, index, True))

        add_audio_to_list = QtWidgets.QAction("添加到音频播放列表")
        add_audio_to_list.triggered.connect(partial(self.press_open_media, index, False))

        open_video = QtWidgets.QAction("在视频播放器中播放")
        open_video.triggered.connect(partial(self.press_open_media, index))

        menu.addAction(default_open_file)
        menu.addAction(open_dir)
        menu.addSeparator()

        menu.addAction(open_audio)
        menu.addAction(add_audio_to_list)
        menu.addSeparator()

        menu.addAction(open_video)

        menu.exec(event.globalPos())

    def press_open_media(self, index, is_play_now=False):
        col = index.column()
        row = index.row()
        if col == 0:
            try:
                file_name = self.item(row, col).text()
            except Exception:
                pass
            else:
                file_name_extension = file_name.split(".")[-1]
                if file_name_extension in main_window.preview_area.support_formats["audio"]:
                    main_window.preview_area.play_audio(self.item(row, 1).text(), is_play_now)
                elif file_name_extension in main_window.preview_area.support_formats["video"]:
                    main_window.preview_area.open_video(self.item(row, 1).text())


class FileSearchThread(QtCore.QRunnable):
    def __init__(self, file_name, search_path):
        super(FileSearchThread, self).__init__()
        self.file_name = file_name
        self.search_path = search_path
        self.result = None
        self.is_running = True
        self.signals = Signals()

    @QtCore.pyqtSlot()
    def run(self):
        self.result = self.search_file(self.file_name, self.search_path)
        self.signals.finished.emit()

    def search_file(self, name, path):
        result = []
        if path is None:
            path = "/"
        if name[0] == "." and len(name) > 1:
            format_search = True
            name = name[1:]
        else:
            format_search = False
        for root, folder, files in os.walk(path):
            for file_name in files:
                if not self.is_running:
                    break
                if not format_search and name not in file_name:
                    continue
                elif format_search and name != file_name.split(".")[-1]:
                    continue
                else:
                    file_path = os.path.abspath(os.path.join(root, file_name))

                    stat_info = os.stat(file_path)

                    # 时间戳转换
                    create_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat_info.st_ctime))
                    modif_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat_info.st_mtime))

                    result.append([file_name, file_path, create_time, modif_time])  # 保存路径与盘符
        return result


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
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("alairack")
    app.setWindowIcon(QtGui.QIcon(":/icons/logo.ico"))
    main_window = MainWindow(None)

    main_window.show()
    sys.exit(app.exec_())
