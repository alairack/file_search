import sys
from os.path import expanduser
from PyQt5.QtWidgets import *
from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *


class AudioPlayer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.userAction = -1
        self.init_player()
        self.init_window()

    def init_window(self):
        self.setWindowTitle('音乐播放器')

        self.createMenubar()

        controlBar = self.addControls()

        centralWidget = QWidget()
        centralWidget.setLayout(controlBar)
        self.setCentralWidget(centralWidget)

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.resize(200, 100)

    def init_player(self):
        self.currentPlaylist = QMediaPlaylist()
        self.player = QMediaPlayer()
        self.player.setVolume(60)

        self.player.mediaStatusChanged.connect(self.qmp_mediaStatusChanged)
        self.player.stateChanged.connect(self.qmp_stateChanged)
        self.player.positionChanged.connect(self.qmp_positionChanged)

        self.statusLabel = QLabel()
        self.statusLabel.setText(f'无音频 :: {self.player.volume()}')

        # 在statusBar 添加永久小部件于左侧的方法
        # https://forum.qt.io/topic/13179/solved-qstatusbar-permanent-widget-on-the-left/10
        self.statusBar().addPermanentWidget(self.statusLabel, stretch=1)

        self.player.volumeChanged.connect(self.qmp_volumeChanged)

    def createMenubar(self):
        menubar = self.menuBar()
        filemenu = menubar.addMenu('文件')
        filemenu.addAction(self.fileOpen())
        filemenu.addAction(self.songInfo())

    def addControls(self):
        controlArea = QVBoxLayout()
        seekSliderLayout = QHBoxLayout()
        controls = QHBoxLayout()
        playlistCtrlLayout = QHBoxLayout()

        self.playBtn = QPushButton('播放')
        self.pauseBtn = QPushButton('暂停')
        self.rm_mediaBtn = QPushButton('移除此歌曲')
        self.pauseBtn.hide()

        stopBtn = QPushButton('停止')
        volumeDescBtn = QPushButton('V (-)')
        volumeIncBtn = QPushButton('V (+)')

        prevBtn = QPushButton('上一首')
        nextBtn = QPushButton('下一首')

        self.seekSlider = QSlider()
        self.seekSlider.setMinimum(0)
        self.seekSlider.setMaximum(100)
        self.seekSlider.setOrientation(Qt.Horizontal)
        self.seekSlider.setTracking(False)
        self.seekSlider.sliderMoved.connect(self.seekPosition)

        self.seekSliderLabel1 = QLabel('0.00')
        self.seekSliderLabel2 = QLabel('0.00')
        seekSliderLayout.addWidget(self.seekSliderLabel1)
        seekSliderLayout.addWidget(self.seekSlider)
        seekSliderLayout.addWidget(self.seekSliderLabel2)

        self.playBtn.clicked.connect(self.playHandler)
        self.pauseBtn.clicked.connect(self.pauseHandler)
        self.rm_mediaBtn.clicked.connect(self.remove_current_audio)
        stopBtn.clicked.connect(self.stopHandler)
        volumeDescBtn.clicked.connect(self.decreaseVolume)
        volumeIncBtn.clicked.connect(self.increaseVolume)
        prevBtn.clicked.connect(self.prevItemPlaylist)
        nextBtn.clicked.connect(self.nextItemPlaylist)

        controls.addWidget(volumeDescBtn)
        controls.addWidget(self.playBtn)
        controls.addWidget(self.pauseBtn)
        controls.addWidget(self.rm_mediaBtn)
        controls.addWidget(stopBtn)
        controls.addWidget(volumeIncBtn)

        playlistCtrlLayout.addWidget(prevBtn)
        playlistCtrlLayout.addWidget(nextBtn)

        controlArea.addLayout(seekSliderLayout)
        controlArea.addLayout(controls)
        controlArea.addLayout(playlistCtrlLayout)
        return controlArea

    def playHandler(self):
        # print(f'media count {self.currentPlaylist.mediaCount()}')
        self.userAction = 1
        if self.player.state() == QMediaPlayer.StoppedState:
            if self.player.mediaStatus() == QMediaPlayer.NoMedia:
                if self.currentPlaylist.mediaCount() == 0:
                    self.openFile()
                if self.currentPlaylist.mediaCount() != 0:
                    self.player.setPlaylist(self.currentPlaylist)
            elif self.player.mediaStatus() == QMediaPlayer.LoadedMedia:
                self.player.play()
            elif self.player.mediaStatus() == QMediaPlayer.BufferedMedia:
                self.player.play()
        elif self.player.state() == QMediaPlayer.PausedState:
            self.player.play()

    def pauseHandler(self):
        self.userAction = 2
        self.player.pause()

    def stopHandler(self):
        self.userAction = 0
        if self.player.state() != QMediaPlayer.StoppedState:
            self.player.stop()

    def qmp_mediaStatusChanged(self):
        # print(f"media status{self.player.mediaStatus()}")
        if self.player.mediaStatus() == QMediaPlayer.LoadedMedia and self.userAction == 1:
            self.player.play()

        elif self.player.mediaStatus() == QMediaPlayer.BufferedMedia:
            media_duration = self.player.duration()
            self.seekSlider.setRange(0, media_duration)
            self.seekSliderLabel2.setText('%d:%02d' % (int(media_duration/60000), int((media_duration/1000) % 60)))

            file_path = self.player.currentMedia().canonicalUrl().toString()
            self.statusLabel.setText(f'正在播放 {file_path.split("///", 1)[1]}  音量: {self.player.volume()}')

        elif self.player.mediaStatus() == QMediaPlayer.EndOfMedia:
            self.player.pause()

    def qmp_stateChanged(self):
        # print(self.player.state())
        # 按钮显示和隐藏的顺序不能变，否则界面会自动拉伸
        if self.player.state() == QMediaPlayer.PlayingState:
            file_path = self.player.currentMedia().canonicalUrl().toString()
            self.statusLabel.setText(f'正在播放 {file_path.split("///", 1)[1]}  音量: {self.player.volume()}')
            self.playBtn.hide()
            self.pauseBtn.show()

        elif self.player.state() == QMediaPlayer.PausedState:
            self.statusLabel.setText(f'暂停中  音量为 {self.player.volume()}')
            self.pauseBtn.hide()
            self.playBtn.show()

        elif self.player.state() == QMediaPlayer.StoppedState:
            self.player.stop()
            self.statusLabel.setText('停止播放  音量为 %d' % (self.player.volume()))

            self.pauseBtn.hide()
            self.playBtn.show()

    def qmp_positionChanged(self, position, sender_type=False):
        if not sender_type:
            self.seekSlider.setValue(position)
        self.seekSliderLabel1.setText('%d:%02d' % (int(position/60000), int((position/1000) % 60)))

    def seekPosition(self, position):
        sender = self.sender()
        if isinstance(sender, QSlider):
            if self.player.isSeekable():
                self.player.setPosition(position)

    def qmp_volumeChanged(self):
        msg = self.statusLabel.text()
        msg = msg[:-2] + str(self.player.volume())
        self.statusLabel.setText(msg)

    def increaseVolume(self):
        vol = self.player.volume()
        vol = min(vol + 5, 100)
        self.player.setVolume(vol)

    def decreaseVolume(self):
        vol = self.player.volume()
        vol = max(vol - 5, 0)
        self.player.setVolume(vol)

    def fileOpen(self):
        open_file_action = QAction('打开文件', self)
        open_file_action.setStatusTip('打开文件')
        open_file_action.triggered.connect(self.openFile)
        return open_file_action

    def openFile(self):
        fileChoosen = QFileDialog.getOpenFileUrl(self, '选择音频文件', "", '音频文件(*.mp3 *.ogg *.wav)')
        if fileChoosen is not None and fileChoosen[0].toString() is not "":
            self.currentPlaylist.addMedia(QMediaContent(fileChoosen[0]))
        else:
            self.statusLabel.setText("无音频")

    def songInfo(self):
        infoAc = QAction('歌曲信息', self)
        infoAc.setStatusTip('显示歌曲信息')
        infoAc.triggered.connect(self.displaySongInfo)
        return infoAc

    def displaySongInfo(self):
        metaDataKeyList = self.player.availableMetaData()
        fullText = '<table class="tftable" border="0">'
        for key in metaDataKeyList:
            value = self.player.metaData(key)
            fullText = fullText + '<tr><td>' + key + '</td><td>' + str(value) + '</td></tr>'
        fullText = fullText + '</table>'
        infoBox = QMessageBox(self)
        infoBox.setWindowTitle('歌曲信息')
        infoBox.setTextFormat(Qt.RichText)
        infoBox.setText(fullText)
        infoBox.addButton('OK', QMessageBox.AcceptRole)
        infoBox.show()

    def prevItemPlaylist(self):
        # print(f'media count {self.currentPlaylist.mediaCount()}')
        if self.currentPlaylist.mediaCount() > 0:
            self.player.playlist().previous()

            if self.player.mediaStatus() == QMediaPlayer.NoMedia:
                self.player.setPlaylist(self.currentPlaylist)
                self.currentPlaylist.setCurrentIndex(self.currentPlaylist.mediaCount() - 1)  # 播放队列最后一首歌曲
            self.player.play()

    def nextItemPlaylist(self):
        if self.currentPlaylist.mediaCount() > 0:
            self.player.playlist().next()

            if self.player.mediaStatus() == QMediaPlayer.NoMedia:
                self.player.setPlaylist(self.currentPlaylist)
            self.player.play()

    def remove_current_audio(self):
        if self.currentPlaylist.mediaCount() > 0:
            current_index = self.currentPlaylist.currentIndex()
            self.currentPlaylist.removeMedia(current_index)
            self.player.setPlaylist(self.currentPlaylist)
            if self.currentPlaylist.mediaCount() > 1:
                self.currentPlaylist.setCurrentIndex(current_index)
                self.player.pause()
        else:
            pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    wd = AudioPlayer()
    sys.exit(app.exec_())