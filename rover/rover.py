"""
This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <https://unlicense.org>
"""

import socket
import threading

import cv2
from flask import Flask, render_template, Response
# Replace with RPi.GPIO if using Raspberry PI instead of Orange PI
import OPi.GPIO as GPIO

# Camera ID (0 = default camera)
CAMERA_ID = 0
# Orange PI board (for OPi.GPIO library)
ORANGE_PI_BOARD = GPIO.ZERO
# Hardware ports
MOTOR_1_DIR_PORT = 13    # PA0
MOTOR_2_DIR_PORT = 11    # PA1
MOTORS_ENABLE_PORT = 15  # PA3

app = Flask(__name__)
frame = None
opencv_working = False


@app.route('/')
def index():
    """
    Main server page
    """
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """
    Video from camera as JPEG image
    """
    global frame, opencv_working

    # Start new OpenCV thread
    if not opencv_working:
        print('Starting new OpenCV thread...')
        opencv_working = True
        threading.Thread(target=opencv_thread).start()
        while frame is None:
            pass
        print('OpenCV stream started successfully')

    if frame is not None:
        # Make response with encoded frame as JPEG image
        new_response = Response(gen(),
                                mimetype="multipart/x-mixed-replace; boundary=frame")
        new_response.headers.add('Connection', 'close')
        new_response.headers.add('Max-Age', '0')
        new_response.headers.add('Expires', '0')
        new_response.headers.add('Cache-Control',
                                 'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')
        new_response.headers.add('Pragma', 'no-cache')
        new_response.headers.add('Access-Control-Allow-Origin', '*')
        return new_response
    else:
        # Clear flag to reconnect to camera
        opencv_working = False
        return '', 204


@app.route('/move/<string:direction>')
def move(direction):
    """
    Called from a GET request
    """
    print('New HTTP GET request! Moving', direction)

    # TODO: Put your motor control code here
    if direction == 'forward':
        GPIO.output(MOTOR_1_DIR_PORT, 1)
        GPIO.output(MOTOR_2_DIR_PORT, 1)
        GPIO.output(MOTORS_ENABLE_PORT, 1)
    elif direction == 'left':
        GPIO.output(MOTOR_1_DIR_PORT, 0)
        GPIO.output(MOTOR_2_DIR_PORT, 1)
        GPIO.output(MOTORS_ENABLE_PORT, 1)
    elif direction == 'backward':
        GPIO.output(MOTOR_1_DIR_PORT, 0)
        GPIO.output(MOTOR_2_DIR_PORT, 0)
        GPIO.output(MOTORS_ENABLE_PORT, 1)
    elif direction == 'right':
        GPIO.output(MOTOR_1_DIR_PORT, 1)
        GPIO.output(MOTOR_2_DIR_PORT, 0)
        GPIO.output(MOTORS_ENABLE_PORT, 1)
    elif direction == 'stop':
        GPIO.output(MOTOR_1_DIR_PORT, 0)
        GPIO.output(MOTOR_2_DIR_PORT, 0)
        GPIO.output(MOTORS_ENABLE_PORT, 0)

    return direction, 200


def opencv_thread():
    """
    Just reads the image from the camera into the frame
    """
    global frame, opencv_working
    try:
        # Start the camera
        capture = cv2.VideoCapture(CAMERA_ID)
        while opencv_working:
            # Read the frame
            ret, frame = capture.read()
            if not ret:
                print('Frame is empty!')
    except Exception as e:
        print('Error during openCV video thread!', e)

    # Clear flag
    opencv_working = False


def gen():
    """
    Encodes the camera image to JPG
    """
    global frame
    while True:
        if frame is not None:
            (flag, encoded_image) = cv2.imencode('.jpg', frame)
            if not flag:
                continue
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
                   bytearray(encoded_image) + b'\r\n')
        else:
            break


def setup_ports():
    """
    Configures physical ports as digital outputs
    """
    # BOARD BCM numbering
    GPIO.setboard(ORANGE_PI_BOARD)

    # Orange Pi board
    GPIO.setmode(GPIO.BOARD)

    # Configure ports as output
    GPIO.setup(MOTOR_1_DIR_PORT, GPIO.OUT)
    GPIO.setup(MOTOR_2_DIR_PORT, GPIO.OUT)
    GPIO.setup(MOTORS_ENABLE_PORT, GPIO.OUT)


if __name__ == '__main__':
    # Configure ports
    setup_ports()

    # Find local IP
    local_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    local_socket.connect(('8.8.8.8', 80))
    local_ip = local_socket.getsockname()[0]

    # Start the server
    app.run(host=local_ip, port='80', debug=False)
