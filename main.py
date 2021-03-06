import sys
import os
from PyQt5 import QtGui, QtWidgets, Qt, QtCore
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QSizePolicy, QSplitter, \
    QAbstractItemView, QAction, QLineEdit
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
        self.search_frame.setFont(Qt.QFont("Segoe UI", 12))

        self.choose_search_dir_button = QtWidgets.QPushButton("选择路径")
        self.choose_search_dir_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.choose_search_dir_button.clicked.connect(self.choose_search_dir)

        self.stop_button = QtWidgets.QPushButton("停止搜索")
        self.stop_button.clicked.connect(self.stop_search)
        self.stop_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.stop_button.hide()

        self.combobox = QComboBox(self)
        self.combobox.setLineEdit(self.search_frame)
        self.combobox.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.combobox.setMinimumHeight(26)
        self.combobox.setCompleter(None)
        self.combobox.activated.connect(self.choose_history)

        view = QtWidgets.QListView(self.combobox)
        view.setMinimumHeight(420)

        self.combobox.setView(view)

        hbox_layout = QtWidgets.QHBoxLayout()
        hbox_layout.addWidget(self.combobox)
        hbox_layout.addWidget(self.choose_search_dir_button)
        hbox_layout.addWidget(self.stop_button)

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

        self.splitter = QSplitter()

        self.splitter.addWidget(self.table_widget)
        self.splitter.addWidget(self.preview_area)

        self.splitter.setSizes([1, 0])

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.setSpacing(15)
        vbox_layout.addLayout(hbox_layout)
        vbox_layout.addWidget(self.splitter)

        self.history = History(self.combobox)

        self.createMenu()

        self.statusLabel = QtWidgets.QLabel()
        self.statusBar().addPermanentWidget(self.statusLabel, stretch=1)

        widget = QtWidgets.QWidget()
        widget.setLayout(vbox_layout)

        self.search_path = "/"

        self.update_statusbar()

        self.setCentralWidget(widget)

        self.about_window = AboutWindow()

        self.file_search_thread = None
        self.is_reading_results = False
        self.update_timer = Qt.QTimer()
        self.update_timer.setInterval(1500)
        self.update_timer.timeout.connect(self.update_table)

    def createMenu(self):
        menu = self.menuBar()

        statusBar_action = ViewAction("状态栏", self, self.switching_display_state, self.statusBar())
        preview_area_action = ViewAction("预览区域", self, self.switching_display_state, self.preview_area)
        audio_player_action = ViewAction("音频预览器", self, self.switching_display_state, self.preview_area.audio_player)
        audio_player_action.setChecked(False)

        view_menu = menu.addMenu("视图")
        view_menu.addAction(statusBar_action)
        view_menu.addAction(preview_area_action)
        view_menu.addAction(audio_player_action)

        history_limit = HistoryLimitAction(self)
        setting_menu = menu.addMenu("设置")
        setting_menu.addAction(history_limit)

        about_action = QAction("关于", self)
        about_action.setIcon(self.style().standardIcon(Qt.QStyle.SP_MessageBoxInformation))
        about_action.triggered.connect(self.show_about_window)

        about_menu = menu.addMenu('关于')
        about_menu.addAction(about_action)

    def start_search(self):
        file_name = self.search_frame.text()
        if file_name == "":
            self.update_timer.setInterval(5)          # 在搜索结果数量非常庞大时，应快速更新，否则界面十分卡顿
        else:
            self.history.save_history(self.search_frame.text())
        self.choose_search_dir_button.hide()
        self.stop_button.show()

        self.threadpool = QtCore.QThreadPool()
        self.file_search_thread = FileSearchThread(file_name, self.search_path)
        self.threadpool.start(self.file_search_thread)
        self.file_search_thread.signals.finished.connect(self.stop_search)

        self.table_widget.clearContents()
        self.table_widget.setRowCount(0)

        self.update_timer.start()

    def stop_search(self):
        self.update_timer.stop()
        self.file_search_thread.is_running = False
        self.update_table()
        self.stop_button.hide()
        self.choose_search_dir_button.show()

    def update_table(self):
        if self.is_reading_results:
            return
        else:
            self.is_reading_results = True
        current_resultCount = self.table_widget.rowCount()
        self.table_widget.setRowCount(len(self.file_search_thread.result) + current_resultCount)
        for info_list in self.file_search_thread.result:
            for j, info in enumerate(info_list):
                table_cell = QTableWidgetItem(info)
                table_cell.setToolTip(info)
                if j == 0:
                    file_icon = QtWidgets.QFileIconProvider().icon(QtCore.QFileInfo(info_list[1]))
                    table_cell.setIcon(file_icon)
                self.table_widget.setItem(current_resultCount, j, table_cell)

            current_resultCount = current_resultCount + 1

        self.file_search_thread.result = []
        self.is_reading_results = False

        self.update_statusbar()
        self.table_widget.horizontalHeader().resizeSections(QtWidgets.QHeaderView.Stretch)

    def choose_search_dir(self):
        dir_choose = QtWidgets.QFileDialog.getExistingDirectory(self, "选取搜索文件夹")
        if dir_choose != "":
            self.search_path = dir_choose
        else:
            self.search_path = "/"
        self.update_statusbar()

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
        if self.about_window is not None:
            self.about_window.close()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            self.start_search()

    def preview_table_cell(self, row, col):
        if col == 0:
            try:
                file_name = self.table_widget.item(row, col).text()
            except Exception:
                pass
            else:
                file_name_extension = file_name.split(".")[-1]
                if file_name_extension in self.preview_area.support_formats["text"]:
                    if not self.preview_area.isHidden() and self.splitter.sizes()[1] == 0:
                        self.splitter.setSizes([1, 1])
                    self.preview_area.show_text(self.table_widget.item(row, 1).text())
                elif file_name_extension in self.preview_area.support_formats["image"]:
                    if not self.preview_area.isHidden() and self.splitter.sizes()[1] == 0:
                        self.splitter.setSizes([1, 1])
                    self.preview_area.show_image(self.table_widget.item(row, 1).text())
                elif file_name_extension in self.preview_area.support_formats["audio"]:
                    self.preview_area.play_audio(self.table_widget.item(row, 1).text(), True)
                elif file_name_extension in self.preview_area.support_formats["video"]:
                    self.preview_area.open_video(self.table_widget.item(row, 1).text())

    def update_statusbar(self):
        """
        更新状态栏以显示最新信息数量及搜索路径
        """
        self.statusLabel.setText(f"{self.table_widget.rowCount()}个对象       {self.search_path}")

    def switching_display_state(self, event, widget):
        if widget is not None:
            if event:
                widget.show()
            else:
                widget.hide()

    def show_about_window(self):
        self.about_window.show()


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

        self.setSortingEnabled(True)

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
        self.result = []
        self.search_file(self.file_name, self.search_path)
        self.signals.finished.emit()

    def search_file(self, name, path):
        if path is None:
            path = "/"
        if len(name) > 1 and name[0] == ".":
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

                    self.result.append([file_name, file_path, create_time, modif_time])  # 保存路径与盘符


class History(object):
    def __init__(self, combobox):
        self.history_number = None

        appdata_path = os.getenv("APPDATA")
        self.app_dir_path = os.path.join(appdata_path, "file_search")
        self.history_file_path = os.path.join(self.app_dir_path, "history.pickle")
        self.limit_setting_path = os.path.join(self.app_dir_path, "history_limit.ini")

        self.combobox = combobox
        self.init_combobox()
        self.history_limit = self.read_history_limit()

    def init_combobox(self):
        history = self.read_history()
        if history is not None:
            self.combobox.addItems(history)

    def save_history(self, text):
        current_history = self.read_history()
        if current_history is None:
            current_history = [text]
        else:
            if self.history_number == self.history_limit:
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

    def save_history_limit(self, limit):
        with open(self.limit_setting_path, "w") as f:
            f.write(str(limit))
        self.history_limit = limit

    def read_history_limit(self):
        if not os.path.isfile(self.limit_setting_path):
            self.save_history_limit(20)
            return 20
        else:
            with open(self.limit_setting_path, "r") as f:
                content = f.read()
            if content != "":
                limit = int(content)
                return limit
            else:
                self.save_history_limit(20)
                return 20


class Signals(QtCore.QObject):
    finished = QtCore.pyqtSignal()


class ViewAction(QAction):
    def __init__(self, text, parent, method, widget):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setChecked(True)
        self.triggered.connect(partial(method, widget=widget))


class AboutWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("关于File Search")

        self.controlLayout = QtWidgets.QHBoxLayout()

        about_text = "  File Search <br><br>   版本1.0.0 <br><br>   By alairack <br><br>   许可证:GPL 3.0 <br><br>   <a href=\"https://github.com/alairack/file_search\">github项目地址</a>"

        self.textLabel = QtWidgets.QLabel()
        self.textLabel.setFont(QtGui.QFont("SimSun", 11))
        self.textLabel.setTextFormat(QtCore.Qt.RichText)
        self.textLabel.setText(about_text)
        self.textLabel.setOpenExternalLinks(True)

        self.logoLabel = QtWidgets.QLabel()
        self.logoLabel.setPixmap(QtGui.QPixmap(":/icons/logo.ico").scaled(Qt.QSize(100, 100), QtCore.Qt.KeepAspectRatio))

        self.controlLayout.addWidget(self.logoLabel)
        self.controlLayout.addSpacing(20)
        self.controlLayout.addWidget(self.textLabel)
        self.setLayout(self.controlLayout)


class HistoryLimitAction(QtWidgets.QWidgetAction):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.widget = QtWidgets.QWidget()
        self.hbox_layout = QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QLabel("存储历史记录条数")
        self.spinbox = QtWidgets.QSpinBox()
        self.spinbox.setMaximum(40)
        self.spinbox.setValue(self.parent().history.history_limit)
        self.spinbox.valueChanged.connect(self.parent().history.save_history_limit)

        self.hbox_layout.addWidget(self.label)
        self.hbox_layout.addWidget(self.spinbox)
        self.widget.setLayout(self.hbox_layout)
        self.setDefaultWidget(self.widget)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("alairack")
    app.setWindowIcon(QtGui.QIcon(":/icons/logo.ico"))
    main_window = MainWindow(None)

    main_window.show()
    sys.exit(app.exec_())
