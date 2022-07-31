#!/usr/bin/env python3
# vuquangtrong.github.io

from base64 import decode
import io
import time
import socket
from http.server import SimpleHTTPRequestHandler, HTTPServer
from threading import Condition
import threading
import numpy

"""
FrameBuffer is a synchronized buffer which gets each frame and notifies to all waiting clients.
It implements write() method to be used in picamera.start_recording()
"""


class FrameBuffer(object):

    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()
        self.clientNum = 0

    def getClientNum(self):
        return self.clientNum

    def write(self, buf):
        # if buf.startswith(b'\xff\xd8'):
        # New frame
        with self.condition:
            # write to buffer
            self.buffer.seek(0)
            self.buffer.write(buf)
            # crop buffer to exact size
            self.buffer.truncate()
            # save the frame
            self.frame = self.buffer.getvalue()
            # notify all other threads
            self.condition.notify_all()


"""
StreamingHandler extent http.server.SimpleHTTPRequestHandler class to handle mjpg file for live stream
"""


class StreamingHandler(SimpleHTTPRequestHandler):
    def __init__(self, frames_buffer, *args):
        self.frames_buffer = frames_buffer
        print("New StreamingHandler, using frames_buffer=", frames_buffer)
        super().__init__(*args)

    def __del__(self):
        print("Remove StreamingHandler")

    def do_GET(self):
        if self.path == '/stream.mjpg':
            frame_buffer.clientNum += 1
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header(
                'Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                # tracking serving time
                start_time = time.time()
                frame_count = 0
                # endless stream
                while True:
                    with self.frames_buffer.condition:
                        # wait for a new frame
                        self.frames_buffer.condition.wait()
                        # it's available, pick it up
                        frame = self.frames_buffer.frame
                        # send it
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', len(frame))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                        # count frames
                        frame_count += 1
                        # calculate FPS every 5s
                        if (time.time() - start_time) > 5:
                            print("FPS: ", frame_count /
                                  (time.time() - start_time))
                            frame_count = 0
                            start_time = time.time()
            except Exception as e:
                frame_buffer.clientNum -= 1
                #print(f'Removed streaming client {self.client_address}, {str(e)}')
        else:
            self.send_error(404)


def recvall(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf:
            return None
        buf += newbuf
        count -= len(newbuf)
    return buf


def tcp_server(frame_buffer):
    TCP_IP = '0.0.0.0'
    TCP_PORT = 61234

    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.bind((TCP_IP, TCP_PORT))
    tcp_server.listen(True)

    while(True):
        conn, addr = tcp_server.accept()
        conn.settimeout(2.0)
        print('connection from', addr)
        try:
            cntr = 0

            # Start streaming command or kill connection
            if frame_buffer.getClientNum() > 0:
                cmd = "s"
            else:
                cmd = "q"

            conn.send(cmd.encode('utf-8'))

            while(True):
                length = recvall(conn, 4)
                if not length:
                    break

                length = int.from_bytes(length, 'little')
                stringData = recvall(conn, int(length))
                data = numpy.frombuffer(stringData, dtype='uint8')
                frame_buffer.write(data)

                if frame_buffer.getClientNum() == 0:
                    conn.send('q'.encode('utf-8'))

        except socket.timeout:
            print("Connection timeout")

        print("Connection closed")
        conn.close()
    # TODO: clean this up properly
    s.close()


def stream(frame_buffer):
    # run server
    try:
        address = ('', 8888)
        httpd = HTTPServer(
            address, lambda *args: StreamingHandler(frame_buffer, *args))
        httpd.serve_forever()
    finally:
        # camera.stop_recording()
        pass


if __name__ == "__main__":
    frame_buffer = FrameBuffer()
    threads = list()

    tcpThread = threading.Thread(target=tcp_server, args=(frame_buffer,))
    threads.append(tcpThread)
    tcpThread.start()

    httpThread = threading.Thread(target=stream, args=(frame_buffer,))
    threads.append(httpThread)
    httpThread.start()

    for index, thread in enumerate(threads):
        thread.join()
