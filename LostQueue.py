# coding: utf-8

import os
import sys
import pyautogui

from PyQt5.Qt import Qt
from PyQt5.QtWidgets import *
from playsound import playsound
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QCursor
from core.lautils import LostArkManager

# Function that handles the background image load inside the exe
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        # Window size
        # Get w,h of the screen (ie: 1920x1080)
        w, h = pyautogui.size()
        self.res_w = w
        self.res_h = h

        # Instanciating a lost ark manager
        self.lamanager = LostArkManager(screen_res=(w,h))

        # Try to fetch queue status: if returns some error,
        # assign an empty string
        try:
            self.queue_status = self.lamanager.get_queue_status()
        except:
            self.queue_status = ''

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


        # Handle resolution scaling
        scale_factor = 0
        font_size = 0
        print("Current Resolution: {}x{}".format(w,h))
        print("Current Game resolution: {}x{}".format(self.lamanager.screen_res[0], self.lamanager.screen_res[1]))
        if h <= 768:
            font_size =  14
            scale_factor = 0.5
            self.overlay_w = 280
            self.overlay_h = 140
        elif h <= 1080:
            scale_factor = 1
            font_size = 16
            self.overlay_w = 300
            self.overlay_h = 150
        elif h <= 1440:
            self.overlay_w = 380
            self.overlay_h = 190
            font_size = 18
            scale_factor = 2
        elif h <= 2160:
            self.overlay_w = 530
            self.overlay_h = 265
            font_size = 19
            scale_factor = 3
        else:
            exit(0)

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
            border-image: url("assets/background.jpg");
            background-repeat: no-repeat;
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
            queue_text = ' Not in queue. '
            player_text = ' Please choose a server '
            time_text = ' And try again! '
        else:
            queue_text = ' Position in Queue: {}'.format(self.queue_status)
            player_text = ' Players per minute: Synch.. '
            time_text = ' Time left: Synch.. '


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

        # Try to get cur queue status, if some error returns, assign an empty string
        try:
            cur_queue = self.lamanager.get_queue_status()
        except:
            cur_queue = ''


        # Check if we´ve logged in: if the last queue status was lesser than 15,
        # and the new status is empty that means we´ve finally managed to get in the game.
        if self.queue_status != '':
            if int(self.queue_status) < 100 and cur_queue == '':
                self.queue_label.setVisible(False)
                self.player_label.setText('   LOGGED IN!   ')
                self.time_label.setVisible(False)

                # Playsound strangely wont work TODO: Understand whY!
                #self.update_timer.start(7000)
                #playsound('./assets/logged.wav')

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
            time_text = 'Time left: Computing..'
        else:

            # Get the avg time from the manager
            avg_time = self.lamanager.compute_wait_time(cur_queue, self.queue_status)

            # We can have the cases in which avg time is None (failed to fetch data).
            if not avg_time:
                time_text =  'Time to left: {}'.format('Recomputing..')
            else:
                time_text =  'Time left: {} minutes'.format(avg_time)

        # Set the time label with the appropriate text
        self.time_label.setText(time_text)


        # If the cur queue is empty, that means tesseract failed the recognition.
        # Set the last queue if present or display a message.
        if cur_queue == '':
            if self.queue_status != '':
                if self.lamanager.avg_queue_decreases.mean() != None:
                    try:
                        self.player_label.setText(' Players per minute: {} '.format(int(self.lamanager.avg_queue_decreases.mean()*3)))
                        self.queue_label.setText(' Position in queue: {} '.format(int(self.queue_status)-int(self.lamanager.avg_queue_decreases.mean())))
                    except:
                        self.player_label.setText(' Validating. Please wait.. ')
                        self.queue_label.setText(' Validating. Please wait.. ')
                else:
                    self.queue_label.setText(' Validating. Please wait.. ')
                    self.player_label.setText(' Validating. Please wait.. ')

            else:
                self.queue_label.setText(' Validating. Please wait.. ')
                try:
                    self.player_label.setText(' Players per minute: {} '.format(int(self.lamanager.avg_queue_decreases.mean()*3)))
                except:
                    self.player_label.setText(' Validating. Please wait.. ')
        else:
            self.queue_label.setText(' Position in queue: {} '.format(cur_queue))
            try:
                self.player_label.setText(' Players per minute: {} '.format(int(self.lamanager.avg_queue_decreases.mean()*3)))
            except:
                self.player_label.setText(' Validating. Please wait.. ')




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
        label.setText(text)
        label.setFont(QtGui.QFont(fontname, fontsize))
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setScaledContents(True)
        label.setStyleSheet(
            """ QLabel {
            background-color: rgba(187, 194, 194, 220);
            border-radius: 10px;
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
