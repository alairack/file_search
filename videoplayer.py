from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSlider,
                             QStyle, QVBoxLayout, QWidget)
import time
from ffpyplayer.player import MediaPlayer


class VideoPlayer(QWidget):

    def __init__(self, video_path, parent=None):
        super(VideoPlayer, self).__init__(parent)

        self.video_path = video_path

        self.setWindowTitle("视频预览")

        self.label = QLabel()
        self.label.setScaledContents(True)
        # self.label.resize(self.width(), self.height())

        # 重要代码，实现窗口可缩放
        # https://stackoverflow.com/questions/24940709/qt-designer-window-wont-get-smaller-than-a-qlabel-with-pixmap
        self.label.setMinimumSize(1, 1)

        self.playButton = QPushButton()
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.clicked.connect(self.play)

        self.pauseButton = QPushButton()
        self.pauseButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.pauseButton.clicked.connect(self.pause)
        self.pauseButton.hide()

        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setPosition)

        self.durationLabel = QLabel()
        self.durationLabel.setSizePolicy(QSizePolicy.Preferred,
                QSizePolicy.Maximum)

        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.pauseButton)
        controlLayout.addWidget(self.positionSlider)
        controlLayout.addWidget(self.durationLabel)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addLayout(controlLayout)

        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.showFrame)
        self.timer.setInterval(1000 / 8)   # 控制帧数

        self.video_media_data = None
        self.init_player()

    def init_player(self):
        """
        初始化播放器，获取第一帧画面及视频总时长
        """
        self.player = MediaPlayer(self.video_path)
        while 1:
            if self.showFrame()[0] is not None:
                self.video_media_data = self.player.get_metadata()
                self.player.set_pause(True)
                break
        self.positionSlider.setRange(0, self.video_media_data['duration'])   # 设置进度条长度
        self.durationLabel.setText(f"0/{self.video_media_data['duration']}")

    def play(self):
        if not self.timer.isActive():
            self.player.set_pause(False)
            self.timer.start()
            self.positionSlider.setValue(0)
        else:
            self.player.set_pause(False)
        self.playButton.hide()
        self.pauseButton.show()

    def pause(self):
        self.player.set_pause(True)
        self.pauseButton.hide()
        self.playButton.show()

    def showFrame(self):
        frame, val = self.player.get_frame()

        if val != 'eof' and frame is not None:
            time.sleep(val)
            img, t = frame

            data = img.to_bytearray()[0]
            width, height = img.get_size()

            # the technical name for the 'rgb24' default pixel format is RGB888,
            # which is QImage.Format_RGB888 in the QImage format enum
            qimage = QtGui.QImage(data, width, height, QtGui.QImage.Format_RGB888)
            self.pixmap = QtGui.QPixmap.fromImage(qimage)
            self.pixmap = self.pixmap.scaled(self.label.width(), self.label.height(),
                                   QtCore.Qt.IgnoreAspectRatio)
            self.label.setPixmap(self.pixmap)
            self.update()

            self.positionSlider.setValue(frame[1])
            if self.video_media_data is not None:
                self.durationLabel.setText(f"{round(frame[1], 1)}/{self.video_media_data['duration']}")

        elif val == "eof":
            self.player.seek(0, relative=False, accurate=False)            # 跳转回视频开头
            self.player.set_pause(True)
            self.pauseButton.hide()
            self.playButton.show()
            self.timer.stop()
        elif frame is None:
            time.sleep(0.01)
        return frame, val

    def setPosition(self, position):
        pass

    def closeEvent(self, event):
        self.timer.stop()
        self.player.close_player()


if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)

    player = VideoPlayer()
    player.resize(320, 240)
    player.show()

    sys.exit(app.exec_())