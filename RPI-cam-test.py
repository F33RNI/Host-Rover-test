import threading

import cv2
from flask import Flask, render_template, Response, redirect, request
import socket
app = Flask(__name__)

frame = None


def opencv_video():
    print('Starting openCV video')
    global frame
    capture = cv2.VideoCapture(1)
    while True:
        ret, frame = capture.read()
        if not ret:
            break


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    if frame is not None:
        new_response = Response(gen(),
                                mimetype='multipart/x-mixed-replace; boundary=frame')
        new_response.headers.add('Access-Control-Allow-Origin', '*')
        new_response.headers.add('Cache-Control', 'no-cache')
        return new_response
    else:
        return '', 204


def gen():
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


if __name__ == '__main__':
    thread = threading.Thread(target=opencv_video)
    thread.start()

    local_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    local_socket.connect(("8.8.8.8", 80))
    local_ip = local_socket.getsockname()[0]
    # socket.gethostbyname(socket.gethostname())
    app.run(host=local_ip, port='5000', debug=False)
