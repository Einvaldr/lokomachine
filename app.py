import os
import sys
import time
import datetime
import json
import serial
import random
import subprocess

from LokoConstants import GAME_DURATION, SERIAL_PORT, BAUDRATE, SERVER_IP, SERVER_PORT, GOALS_PER_DISCOUNT, HTML_PATH, QUESTIONS_PATH, SOUND_PATH

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QUrl
from PyQt4.QtWebKit import QWebView
from PyQt4.QtGui import QGridLayout

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

files = os.listdir(HTML_PATH + QUESTIONS_PATH)
pages = filter(lambda x: x.endswith('.html'), files)
l = list(pages)
question = l.pop(random.randrange(0, len(l), 1))
correctAnswer = question[-6]

date = datetime.datetime.now() + datetime.timedelta(minutes=GAME_DURATION, seconds=2)
score = 0
discount = int(score / GOALS_PER_DISCOUNT)

# intro
# counter
# playing
# result
# correct
# incorrect

status = 'intro'

mutex = QtCore.QMutex()


class HttpProcessor(BaseHTTPRequestHandler):
    def do_GET(self):
        global server, status, date, score, discount, question

        if status == 'intro':
            status = 'counter'
            server.page_updated.emit("countdown.html", None)
        elif status == 'counter':
            status = 'playing'
            mutex.lock()
            score = 0
            discount = 0
            date = datetime.datetime.now() + datetime.timedelta(minutes=GAME_DURATION, seconds=2)
            url = '%s%s?date=%s&score=%d&discount=%d' % (QUESTIONS_PATH, question, date, score, discount)
            mutex.unlock()
            server.page_updated.emit(url, "playing.wav")
        elif (status == 'playing') and (date <= datetime.datetime.now()):
            status = 'result'
            server.page_updated.emit('gift.html', "result.wav")
        elif status == 'result':
            status = 'intro'
            server.page_updated.emit('start.html', "intro.wav")

        mutex.lock()
        dictionary = {"score": score, "discount": discount, "finish": status == 'result'}
        mutex.unlock()

        response = json.dumps(dictionary, sort_keys=True)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(response)
        return


class ServerThread(QtCore.QThread):
    page_updated = QtCore.pyqtSignal(object, object)

    def __init__(self):
        QtCore.QThread.__init__(self)

    def run(self):
        server = HTTPServer((SERVER_IP, SERVER_PORT), HttpProcessor)
        server.serve_forever()


class ArduinoThread(QtCore.QThread):
    page_updated = QtCore.pyqtSignal(object, object)

    def __init__(self):
        QtCore.QThread.__init__(self)

    def run(self):
        global question, date, score, discount, correctAnswer, l, pages
        self.port = None
        while True:
            if self.port == None:
                for i in range(256):
                    try:
                        self.port = serial.Serial((SERIAL_PORT % i), BAUDRATE)
                        self.port.flushInput()
                        self.port.flushOutput()
                        print "Serial opened: ", self.port
                        break
                    except:
                        self.port = None

            if self.port == None:
                print "Serial could not be initialized"
                time.sleep(1)
                continue

            try:
                # Block forever until we got 1 or 2 line
                # it is buffering. required to get the data out*now*
                # sio.flush()
                #goal = self.port.readline(1)
                goal = self.port.read(1)
                print "Score hit " + goal
            except Exception, e:
                self.port = None
                print "Serial exception" + str(e)
                continue

            if goal != '1' and goal != '2' and goal != '3':
                continue

            mutex.lock()

            if status != 'playing':
               mutex.unlock()
               continue

            if correctAnswer == goal or goal == '3':
                url = 'correct.html'
                self.page_updated.emit(url, "correct.wav")

                if not l:
                    l = list(pages)
                self.port.write("7")
                score += 1
                discount = int(score / GOALS_PER_DISCOUNT)
                question = l.pop(random.randrange(0, len(l), 1))
                correctAnswer = question[-6]

                #audio = subprocess.Popen("exec aplay " + SOUND_PATH + "correct.wav", stdout=subprocess.PIPE, shell=True)

                time.sleep(1.5)
                # URL in the form of 1_1.html?date=2016-12-15 18:06:00&score=1&discount=1
                url = '%s%s?date=%s&score=%d&discount=%d' % (QUESTIONS_PATH, question, date, score, discount)
                self.page_updated.emit(url, None)
            else:
                url = 'incorrect.html'
                self.page_updated.emit(url, "incorrect.wav")

                if not l:
                    l = list(pages)
                self.port.write("8")
                question = l.pop(random.randrange(0, len(l), 1))
                correctAnswer = question[-6]

                #audio = subprocess.Popen("exec aplay " + SOUND_PATH + "incorrect.wav", stdout=subprocess.PIPE, shell=True)
                #subprocess.call(["aplay", SOUND_PATH + 'incorrect.wav'])

                time.sleep(1.5)
                # URL in the form of 1_1.html?date=2016-12-15 18:06:00&score=1&discount=1
                url = '%s%s?date=%s&score=%d&discount=%d' % (QUESTIONS_PATH, question, date, score, discount)
                self.page_updated.emit(url, None)

            mutex.unlock()

            time.sleep(1)


class MainWindow(QtGui.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        self.browser = QWebView()
        grid.addWidget(self.browser, 1, 0)
        self.setLayout(grid)
        self.showFullScreen()
        self.browser.load(QUrl(HTML_PATH + 'start.html'))

    def on_page_updated(self, data, sound = None):
        global audio, status, video
        subprocess.call(["killall", "omxplayer.bin"])
        # subprocess.call(["kill", "-9", audio.pid])
        if status == 'intro':
            video = subprocess.Popen("exec omxplayer --loop /home/pi/loko/lokomachine_video.mp4",
                                     stdout=subprocess.PIPE, shell=True)
            audio = subprocess.Popen("exec aplay /home/pi/loko/sound/intro.wav", stdout=subprocess.PIPE, shell=True)
        if status != 'playing':
          subprocess.call(["killall", "aplay"])
        if sound != None:
          audio = subprocess.Popen("exec aplay " + SOUND_PATH + sound, stdout=subprocess.PIPE, shell=True)

        print data
        url = QUrl(HTML_PATH + data)
        self.browser.load(url)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()

    arduino = ArduinoThread()
    arduino.page_updated.connect(window.on_page_updated)
    arduino.start()

    server = ServerThread()
    server.page_updated.connect(window.on_page_updated)
    server.start()

    # video = subprocess.Popen(["omxplayer", "--loop", "/home/pi/loko/lokomachine_video.mp4"], stdout=subprocess.PIPE)
    # audio = subprocess.Popen(["aplay", "/home/pi/loko/waiting_mode.wav"], stdout=subprocess.PIPE)
    # video = subprocess.Popen("exec omxplayer --loop /home/pi/loko/lokomachine_video.mp4", stdout=subprocess.PIPE, shell=True)
    # audio = subprocess.Popen("exec aplay /home/pi/loko/sound/intro.wav", stdout=subprocess.PIPE, shell=True)
    # audio = subprocess.Popen("exec /home/pi/loko/waiting_mode.sh", stdout=subprocess.PIPE, shell=True)

    sys.exit(app.exec_()) 
