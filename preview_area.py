from PyQt5.QtGui import QPixmap, QPainter, QImage, QPalette, QImageReader
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import (QHBoxLayout, QWidget, QLabel, QMainWindow, QAction, QMenu,
                             QScrollArea, QSizePolicy, QTextEdit)
from PyQt5.QtMultimedia import QMediaContent
from videoplayer import VideoPlayer
from audio_player import AudioPlayer


class PreviewArea(QWidget):
    def __init__(self):
        super(PreviewArea, self).__init__()

        self.support_formats = {}

        self.get_support_formats()

        self.video_player = None

        self.image_viewer = ImageViewer()
        self.image_viewer.hide()
        self.text_viewer = QTextEdit()
        self.text_viewer.setReadOnly(True)
        self.text_viewer.hide()

        self.audio_player = AudioPlayer()

        self.hboxLayout = QHBoxLayout()

        self.hboxLayout.addWidget(self.image_viewer)
        self.hboxLayout.addWidget(self.text_viewer)
        self.setLayout(self.hboxLayout)

    def show_image(self, image_path):
        self.image_viewer.open(image_path)
        self.text_viewer.hide()
        self.image_viewer.show()

    def open_video(self, video_path):
        self.video_player = VideoPlayer(video_path)
        self.video_player.show()

    def show_text(self, text_file_path):
        file_coding = self.get_file_encoding(text_file_path)
        if file_coding == "unknown":
            return "unknown code"
        with open(text_file_path, "r", encoding=file_coding) as f:
            content = f.read()

        self.text_viewer.setText(content)
        self.image_viewer.hide()
        self.text_viewer.show()

    def play_audio(self, path, play_immediately=False):
        self.audio_player.currentPlaylist.addMedia(QMediaContent(QUrl.fromLocalFile(path)))
        self.audio_player.player.setPlaylist(self.audio_player.currentPlaylist)
        self.audio_player.currentPlaylist.setCurrentIndex(self.audio_player.currentPlaylist.mediaCount() - 1)
        if play_immediately:
            self.audio_player.player.play()

    def get_support_formats(self):
        """
        ???ffpyplayer???????????????????????????
                video_support_formats = tools.get_fmts(False, True)[2]
                for x in video_support_formats:
                    if x:           # ????????????????????????
                        for y in x:         # ?????????????????????????????????
                            self.support_formats["video"].append(y)
                """

        self.support_formats["image"] = []
        self.support_formats["video"] = ["mp4", "wmv", "avi", "flv", "3gp"]

        for i in QImageReader.supportedImageFormats():
            self.support_formats["image"].append(bytes(i).decode())

        self.support_formats["text"] = ["txt", "ini", "doc", "docx"]
        self.support_formats["audio"] = ["wav", "mp3"]

    def get_file_encoding(self, file_path):
        """
        ????????????????????????
        ??????: https://blog.csdn.net/u013314786/article/details/77931548
        :param file_path: ????????????????????????
        """

        codes = ['UTF-8', 'GB18030', 'BIG5', "gbk", "UTF-16"]
        # UTF-8 BOM????????????
        utf8_bom = b'\xef\xbb\xbf'
        # ??????????????????

        with open(file_path, 'rb') as f:
            data = f.read()
        for code in codes:
            try:
                data.decode(encoding=code)
                if 'UTF-8' == code and data.startswith(utf8_bom):
                    return 'UTF-8-SIG'
                return code
            except UnicodeDecodeError:
                continue
        return 'unknown'


class ImageViewer(QMainWindow):
    def __init__(self):
        super(ImageViewer, self).__init__()

        self.printer = QPrinter()
        self.scaleFactor = 0.0

        self.imageLabel = QLabel()
        self.imageLabel.setBackgroundRole(QPalette.Base)
        self.imageLabel.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.imageLabel.setScaledContents(True)

        self.scrollArea = QScrollArea()
        self.scrollArea.setBackgroundRole(QPalette.Dark)
        self.scrollArea.setWidget(self.imageLabel)
        self.setCentralWidget(self.scrollArea)

        self.createActions()
        self.createMenu()

        self.setWindowTitle("Image Viewer")

    def open(self, image_path):
        if image_path:
            image = QImage(image_path)
            self.imageLabel.setPixmap(QPixmap.fromImage(image))
            self.scaleFactor = 1.0

            self.fitToWindowAct.setEnabled(True)
            self.updateActions()

            if not self.fitToWindowAct.isChecked():
                self.imageLabel.adjustSize()

    def print_(self):
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec_():
            painter = QPainter(self.printer)
            rect = painter.viewport()
            size = self.imageLabel.pixmap().size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(self.imageLabel.pixmap().rect())
            painter.drawPixmap(0, 0, self.imageLabel.pixmap())

    def zoomIn(self):
        self.scaleImage(1.25)

    def zoomOut(self):
        self.scaleImage(0.8)

    def normalSize(self):
        self.imageLabel.adjustSize()
        self.scaleFactor = 1.0

    def fitToWindow(self):
        fitToWindow = self.fitToWindowAct.isChecked()
        self.scrollArea.setWidgetResizable(fitToWindow)
        if not fitToWindow:
            self.normalSize()

        self.updateActions()

    def createActions(self):
        self.zoomInAct = QAction("Zoom &In (25%)", self, shortcut="Ctrl++",
                enabled=False, triggered=self.zoomIn)

        self.zoomOutAct = QAction("Zoom &Out (25%)", self, shortcut="Ctrl+-",
                enabled=False, triggered=self.zoomOut)

        self.normalSizeAct = QAction("&Normal Size", self, shortcut="Ctrl+S",
                enabled=False, triggered=self.normalSize)

        self.fitToWindowAct = QAction("&Fit to Window", self, enabled=False,
                checkable=True, shortcut="Ctrl+F", triggered=self.fitToWindow)


    def createMenu(self):
        self.viewMenu = QMenu("&View", self)
        self.viewMenu.addAction(self.zoomInAct)
        self.viewMenu.addAction(self.zoomOutAct)
        self.viewMenu.addAction(self.normalSizeAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.fitToWindowAct)

        self.menuBar().addMenu(self.viewMenu)

    def updateActions(self):
        self.zoomInAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.zoomOutAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.normalSizeAct.setEnabled(not self.fitToWindowAct.isChecked())

    def scaleImage(self, factor):
        self.scaleFactor *= factor
        self.imageLabel.resize(self.scaleFactor * self.imageLabel.pixmap().size())

        self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
        self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)

        self.zoomInAct.setEnabled(self.scaleFactor < 3.0)
        self.zoomOutAct.setEnabled(self.scaleFactor > 0.333)

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value()
                                + ((factor - 1) * scrollBar.pageStep()/2)))


