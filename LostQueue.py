# coding: utf-8
import sys
import pyautogui
from PyQt5.Qt import Qt
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QCursor
from core.lautils import LostArkManager

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        # Instanciating a lost ark manager
        self.lamanager = LostArkManager()
        self.queue_status = self.lamanager.get_queue_status()

        # Right click handling
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.exit_on_right_click)

        # Initial windows flag: we need the overlay to stay on top of everything.
        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.X11BypassWindowManagerHint
        )

        # Setting opacity to translucent
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.8)


        # Window size
        # Get w,h of the screen (ie: 1920x1080)
        w, h = pyautogui.size()
        self.res_w = w
        self.res_h = h

        # Handle resolution scaling
        scale_factor = 0
        font_size = 0
        print("Current Resolution: {}x{}".format(w,h))
        if h <= 768:
            font_size =  12
            scale_factor = 0.5
            self.overlay_w = 310
            self.overlay_h = 110
        elif h <= 1080:
            scale_factor = 1
            font_size = 13
            self.overlay_w = 350
            self.overlay_h = 140
        elif h <= 1440:
            self.overlay_w = 430
            self.overlay_h = 170
            font_size = 16
            scale_factor = 2
        elif h <= 2160:
            self.overlay_w = 530
            self.overlay_h = 270
            font_size = 16
            scale_factor = 3
        else:
            self.overlay_w = 500
            self.overlay_h = 130
            font_size = 14
            scale_factor = 5

        # Widget creation: we do assign a name to this external frame since we do
        # want to apply the stylesheet only to the external frame and not all the
        # children aswell. We also resize the frame based on the overlay w,h computed
        # before.
        self.resize(self.overlay_w, self.overlay_h)
        self.centralwidget = QWidget(self)
        self.centralwidget.resize(self.overlay_w, self.overlay_h)
        self.centralwidget.setObjectName('ExternalFrame')

        # Stylesheet creation and application
        stylesheet = """
        QWidget#ExternalFrame {
            border-image: url("background.jpg");
            background-repeat: no-repeat;
            border : 3px solid black;
            border-radius: 20px;
        }
        """
        self.centralwidget.setStyleSheet(stylesheet)

        # Setting the central widget just created inside the qmainwindow
        self.setCentralWidget(self.centralwidget)

        # Define timer: we need to synchronize with the server timer, so initially
        # thats set to 1 sec in polling to refresh the queue status. Once we've been
        # sinchronized we then change the timer timeout to 20 sec.
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.timeout.connect(self.update_label)
        self.update_timer.start(1000)
        self.is_synchronized = False

        # Creating label
        if self.queue_status == '':
            queue_text = '    Not in queue!    '
            time_text = '    Please choose a server.    '
            player_text = '    And try again.    '
        else:
            queue_text = '  Position in Queue: {}  '.format(self.queue_status)
            player_text = '  Players per minute: Synch..    '
            time_text = '  Time to get in: Synch..  '


        self.queue_label = self.create_label('Lato', font_size, 10, 90+(scale_factor), queue_text)
        self.player_label = self.create_label('Lato', font_size, 10, 115+(scale_factor), player_text)
        self.time_label = self.create_label('Lato', font_size, 10, 115+10*scale_factor, time_text)

        # Creating a layout to align labels and object inside
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.queue_label)
        layout.addWidget(self.player_label)
        layout.addWidget(self.time_label)
        self.centralwidget.setLayout(layout)


    def update_label(self):

        # Get cur queue from the Lost Ark Manager
        cur_queue = self.lamanager.get_queue_status()

        # Check if we´ve logged in: if the last queue status was lesser than 15,
        # and the new status is empty that means we´ve finally managed to get in the game.
        if self.queue_status != '':
            if int(self.queue_status) < 100 and cur_queue == '':
                self.queue_label.setVisible(False)
                self.player_label.setText('LOGGED IN!')
                self.time_label.setVisible(False)
                return

        # Check if we're synchronized with the client: we achieve that comapring
        # the initial queue status with the fetched one; if equal that means we're
        # still on the same number, if not we set the correct timer timeout (20 sec)
        # and then set the synch flag to true.
        if not self.is_synchronized:
            if cur_queue != self.queue_status:
                self.is_synchronized = True
                self.update_timer.start(20100)
            else:
                return

        # Update queue and time left. We need to handle some cases, since we can
        # have none values or empty string.
        # If the queue status is empy, that means we do not have information yet.
        if self.queue_status == '':
            time_text = '  Time to get in: Computing..  '
        else:

            # Get the avg time from the manager
            avg_time = self.lamanager.compute_wait_time(cur_queue, self.queue_status)

            # We can have the cases in which avg time is None (failed to fetch data).
            if not avg_time:
                time_text =  '  Time to get in: {}  '.format('Recomputing..')
            else:
                time_text =  '  Time to get in: {} minutes  '.format(avg_time)

        # Set the time label with the appropriate text
        self.time_label.setText(time_text)


        # If the cur queue is empty, that means tesseract failed the recognition.
        # Set the last queue if present or display a message.
        if cur_queue == '':
            if self.queue_status != '':
                if len(self.lamanager.avg_queue_decreases) != 0:
                    self.player_label.setText('  Players per minute: {}  '.format(int(self.lamanager.avg_queue_decreases.mean()*3)))
                    self.queue_label.setText('  Position in queue: {}  '.format(int(self.queue_status)-int(self.lamanager.avg_queue_decreases.mean())))
                else:
                    self.queue_label.setText('  Validating. Please wait..  ')
                    self.player_label.setText('  Validating. Please wait..  ')

            else:
                self.queue_label.setText('  Validating. Please wait..  ')
                self.player_label.setText('  Players per minute: {}  '.format(int(self.lamanager.avg_queue_decreases.mean()*3)))
        else:
            self.queue_label.setText('  Position in queue: {}  '.format(cur_queue))
            self.player_label.setText('  Players per minute: {}  '.format(int(self.lamanager.avg_queue_decreases.mean()*3)))



        # Update the queue status with the current queue fetch if valid
        if cur_queue != '':
            self.queue_status = cur_queue

    def create_label(self, fontname, fontsize, x, y, text, border_radius=15):
        """
            Function that handles label creations.
            INPUT:
            - fontname: name of the font used in the label
            - fontsize: size of the font
            - x,y: position of the label inside the widget
            - text: string that defines what to put inside the label
        """

        label = QLabel('', self)
        label.setScaledContents(True)
        label.setText(text)
        label.setFont(QtGui.QFont(fontname, fontsize))
        label.adjustSize()
        label.move(x,y)
        label.setStyleSheet(
            """ QLabel {
            background-color: rgba(187, 194, 194, 220);;
            border-radius:15px;
            }
            """
        )

        return label

    def exit_on_right_click(self):
        """
            Function that handles right click event. Basically we need to exit
            when the right click (menu context) happens.
        """

        qApp.quit()

    def mousePressEvent(self, event):
        """
            Function that handles left click event. Basically we need to move
            the window when we drag the widget around.
        """

        if event.button() == Qt.LeftButton:
            self.moveFlag = True
            self.movePosition = event.globalPos() - self.pos()
            self.setCursor(QCursor(Qt.OpenHandCursor))
            event.accept()

    def mouseMoveEvent(self, event):
        """
            Function that handles the drag event. Basically we need to move
            the window when we drag the widget around using the position of the
            widget itself.
        """

        if Qt.LeftButton and self.moveFlag:
            self.move(event.globalPos() - self.movePosition)
            event.accept()

    def mouseReleaseEvent(self, QMouseEvent):
        """
            Function that handles the release mouse event.
        """

        self.moveFlag = False
        self.setCursor(Qt.CrossCursor)


if __name__ == '__main__':

    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
