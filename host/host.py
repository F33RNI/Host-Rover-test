import glob
import sys
import threading
import urllib.request

import cv2
import numpy as np
import qimage2ndarray
import serial
from PyQt5 import uic
from PyQt5.QtGui import QPixmap, QKeySequence
from PyQt5.QtWidgets import QApplication, QMainWindow


class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        # System variables
        self.opencv_running = False
        self.serial_port = None

        # Load and show GUI file
        uic.loadUi('gui.ui', self)
        self.show()

        # Connect controls
        self.btn_refresh_ports.clicked.connect(self.refresh_ports)
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.checkbox_keyboard.stateChanged.connect(self.change_shortcuts)
        self.btn_move_forward.clicked.connect(self.move_forward)
        self.btn_move_left.clicked.connect(self.move_left)
        self.btn_move_backward.clicked.connect(self.move_backward)
        self.btn_move_right.clicked.connect(self.move_right)
        self.btn_move_stop.clicked.connect(self.move_stop)

        # Add com port baud rates
        self.combo_field_baud.clear()
        self.combo_field_baud.addItems(['9600', '110', '300', '600', '1200', '2400', '4800',
                                        '14400', '19200', '38400', '57600', '115200', '128000'])

        # Add available serial ports to the combo_field_port
        self.refresh_ports()

        # Connect keyboard to controls
        self.change_shortcuts()

    def change_shortcuts(self):
        """
        Adds or removes keyboard control of the rover
        """
        if self.checkbox_keyboard.isChecked():
            self.btn_move_forward.setShortcut('W')
            self.btn_move_left.setShortcut('A')
            self.btn_move_backward.setShortcut('S')
            self.btn_move_right.setShortcut('D')
            self.btn_move_stop.setShortcut(' ')
        else:
            self.btn_move_forward.setShortcut(QKeySequence())
            self.btn_move_left.setShortcut(QKeySequence())
            self.btn_move_backward.setShortcut(QKeySequence())
            self.btn_move_right.setShortcut(QKeySequence())
            self.btn_move_stop.setShortcut(QKeySequence())

    def start(self):
        """
        Starts openCV stream and opens connection to the field
        """
        # Open serial port
        if len(str(self.combo_field_port.currentText())) > 0:
            print('Using serial port', self.combo_field_port.currentText())
            self.serial_port = serial.Serial(self.combo_field_port.currentText(),
                                             int(self.combo_field_baud.currentText()))
            self.serial_port.close()
            self.serial_port.open()
            print('Port opened?', self.serial_port.isOpen())
        else:
            print('No serial port provided')

        # Start openCV background thread
        self.opencv_running = True
        threading.Thread(target=self.opencv_thread).start()

        # Change buttons state
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_refresh_ports.setEnabled(False)

    def stop(self):
        """
        Stops the openCV stream and closes connection to the field
        """
        # Stop OpenCV thread
        self.opencv_running = False

        # Close serial port
        # noinspection PyBroadException
        try:
            if self.serial_port.isOpen():
                self.serial_port.flush()
                self.serial_port.close()
        except:
            pass

        # Change buttons state
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_refresh_ports.setEnabled(True)

    def refresh_ports(self):
        """
        Updates the list of available serial ports
        """
        self.combo_field_port.clear()
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                self.combo_field_port.addItem(port)
            except (OSError, serial.SerialException):
                pass

    def opencv_thread(self):
        """
        The main thread that receives and processes the image from the rover camera
        """
        video_url = str(self.line_ip.text()) + '/video_feed'
        print('Video URL', video_url)

        try:
            # Starting video stream
            stream = urllib.request.urlopen(video_url)
            video_bytes = bytes()
            while self.opencv_running:
                # Read chunk of bytes
                video_bytes += stream.read(1024)

                # JPEG chars
                a = video_bytes.find(b'\xff\xd8')
                b = video_bytes.find(b'\xff\xd9')

                # New frame
                if a != -1 and b != -1:
                    jpg = video_bytes[a:b + 2]
                    video_bytes = video_bytes[b + 2:]

                    # Convert from JPEG to OpenCV frame
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)

                    # TODO: Some OpenCV calculations
                    # This is just an example drawing a purple circle on a frame
                    # and sending text to the serial port when the frame goes dark
                    cv2.circle(frame, (420, 69), 9, (255, 0, 255), 3)
                    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    if np.sum(frame_gray < 10) > (frame.shape[0] * frame.shape[1]) / 2:
                        print('Sending a message to the serial port...')
                        self.serial_port.write(b'Message from host\n')

                    # Show rover image
                    self.rover_image.setPixmap(QPixmap.fromImage(qimage2ndarray.array2qimage(
                        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))))

        except Exception as e:
            print('Error during openCV video thread!', e)

    def move_forward(self):
        """
        Sends /move/forward GET request
        """
        print('Sending forward request')
        try:
            urllib.request.urlopen(str(self.line_ip.text()) + '/move/forward')
        except Exception as e:
            print('Error sending /move/forward request!', e)

    def move_left(self):
        """
        Sends /move/left GET request
        """
        print('Sending left request')
        try:
            urllib.request.urlopen(str(self.line_ip.text()) + '/move/left')
        except Exception as e:
            print('Error sending /move/left request!', e)

    def move_right(self):
        """
        Sends /move/right GET request
        """
        print('Sending right request')
        try:
            urllib.request.urlopen(str(self.line_ip.text()) + '/move/right')
        except Exception as e:
            print('Error sending /move/right request!', e)

    def move_backward(self):
        """
        Sends /move/backward GET request
        """
        print('Sending backward request')
        try:
            urllib.request.urlopen(str(self.line_ip.text()) + '/move/backward')
        except Exception as e:
            print('Error sending /move/backward request!', e)

    def move_stop(self):
        """
        Sends /move/stop GET request
        """
        print('Sending stop request')
        try:
            urllib.request.urlopen(str(self.line_ip.text()) + '/move/stop')
        except Exception as e:
            print('Error sending /move/stop request!', e)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('fusion')
    win = Window()
    sys.exit(app.exec_())
