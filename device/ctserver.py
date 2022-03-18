import threading
import logging
import socket
import struct

from device import detector, xray

#SEND_MSG_SIZE = 33

RECV_MAX = 8192
#XRAY_RECV_MSG_SIZE = 4*8 + 1 #33
#PHOTO_RECV_HDR_SIZE = 4 * 5 + 1 # 21
MSG_SIZE = 33


class CTServer:

    """
    Base class for servers that implement the custom, message based protocol used for communicating with hardware devices of the CT scanner
    """

    def __init__(self, name):
        self.logger = logging.getLogger(name + "-CTServer")
        self.logger.info("created")

        self.update_callback = None
        self.server_thread = None

        self.client_connected = False
        self.running = False
        self.recent_conn = None
        self.server = None

        self.host = ''
        self.port = 25511


    def run(self):
        """
        Server execution code that is running in separate thread and automatically restarts when an error occurs
        """
        serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = serv
        self.logger.info("Thread initialized")
        serv.bind((self.host, self.port))
        serv.listen(3)

        while self.running:
            try:
                #serv.settimeout(5)
                conn, addr = serv.accept()
                self.recent_conn = conn
                self.client_connected = True
                self.logger.info("%s connected", addr)
                self.alert_update()

                try:
                    self.recv_loop()
                except Exception as e:
                    self.logger.error("Error occurred while receiving. Connection closed")
                    self.logger.error(e)
                finally:
                    conn.close()
                    self.logger.info("%s disconnected", addr)
                    self.client_connected = False
                    self.recent_conn = None
                    if self.running:
                        self.alert_update()

            except Exception:
                self.logger.warning("timeout")

        serv.close()

    def reset_state(self):
        self.client_connected = False
        self.running = False
        self.recent_conn = None
        self.server = None

    def start(self):
        """
        Create new thread and start server
        """
        if self.running:
            self.logger.warning("already running")
            return
        self.reset_state()

        self.running = True

        self.server_thread = threading.Thread(target=self.run)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.logger.info("started")

        self.alert_update()

    def stop(self):
        """
        Close open connections and stop the server thread
        """
        if not self.running:
            self.logger.warning("not running")
            return

        self.running = False

        if self.recent_conn is not None:
            self.recent_conn.close()

        if self.server is not None:
            self.server.close()

        self.logger.info("stopped")
        self.server_thread.join()
        self.logger.info("Thread finalized")
        self.reset_state()
        self.alert_update()

    def alert_update(self):
        """
        Notify state update callback
        """
        if self.update_callback is not None:
            self.update_callback()

    def read_fully(self, num):
        """
        Helper method that waits for :param num: amount of bytes to be received from the socket
        :return: received data
        """
        chunks = []
        chunksize_total = 0
        waiting = 0

        while chunksize_total < num:
            waiting = num-chunksize_total
            if waiting > RECV_MAX:
                waiting = RECV_MAX
            chunk = self.recent_conn.recv(waiting)
            if chunk == b'':
                self.logger.info("recv empty")
                raise Exception("recv empty")
            chunksize_total += len(chunk)
            chunks.append(chunk)

        data = bytearray(b''.join(chunks))
        return data

    def send_cmd(self, cmd):
        """
        Send message frame
        :param cmd: op code byte
        """
        if self.recent_conn is not None:
            self.recent_conn.sendall(bytes(cmd).ljust(MSG_SIZE, b'\x00'))

    def send_cmd_is(self, op, vals):
        """
        Send message containing a list of additional integers
        :param op: op code byte
        :param vals: list of additional integers to be included in the message
        """
        cmd = [bytes(op)]
        for val in vals:
            valbytes = struct.pack('!I', val)
            cmd.append(bytes(valbytes))

        cmdbytes = b''.join(cmd)
        if len(bytes(cmdbytes)) > MSG_SIZE:
            self.logger.error("Can't send %d bytes", len(bytes(cmdbytes)))
            return
        self.send_cmd(cmdbytes)

    def recv_loop(self):
        """
        Data unpacking and handling loop to be implemented in subclasses
        """
        self.logger.warning("stub")


class PhotoCTServer(CTServer, detector.CTDetector):

    def __init__(self):
        CTServer.__init__(self, "Photo")
        detector.CTDetector.__init__(self)
        self.port = 25588

    def recv_loop(self):
        while self.running:
            # Receive header

            data = self.read_fully(MSG_SIZE) # PHOTO_RECV_HDR_SIZE

            self.logger.info("Header received %d", len(data))
            opcode = data[0]
            unpacked = struct.unpack('!IIIII', data[1:21])
            par1 = unpacked[1]
            par2 = unpacked[2]
            par3 = unpacked[3]
            recv_len = unpacked[4]
            token = unpacked[0]

            # Receive variable length image data
            if recv_len > 0:
                data = self.read_fully(recv_len)
                self.logger.info("IMG data received %d", len(data))
            else:
                data = None
                self.logger.info("No extra data received")

            # Parse op code
            if opcode == 0xBA:
                # Unimplemented
                for listener in self.listeners:
                    listener.on_detector_test(data, token)
            elif opcode == 0xBB:
                self.logger.info("pars: %d, %d, %d, %d", par1, par2, par3, token)

                for listener in self.listeners:
                    listener.on_detector_raw(data, par1, par2, par3, token)

    def capture_raw(self, shutterlen, exposure, focuslen, token):
        vals = [token, shutterlen, exposure, focuslen]
        self.send_cmd_is(b'\x1B', vals)

    # Would have only been used with Android
    # def capture_test(self, shutterlen, exposure, focuslen, token):
    #     vals = [token, shutterlen, exposure, focuslen]
    #     self.send_cmd_is(b'\x1A', vals)

    def is_ready(self):
        return self.client_connected


class XRayCTServer(CTServer, xray.CTXRay):

    def __init__(self):
        CTServer.__init__(self, "XRay")
        xray.CTXRay.__init__(self)

        self.port = 25599

    def recv_loop(self):
        while self.running:
            # Read one full packet
            data = self.read_fully(MSG_SIZE)
            self.parse_frame(data)

    def parse_frame(self, cmd):
        #self.logger.info("Frame received")

        cmd_arr = bytearray(cmd)
        op = cmd_arr[0]
        unpacked = struct.unpack('!II', cmd_arr[1:9])

        angle = float(unpacked[1]) / 100.0
        token = unpacked[0]

        # Parse op code
        if op == 0xAA:
            for listener in self.listeners:
                listener.on_xray_position_done(angle, token)
        elif op == 0xAF:
            for listener in self.listeners:
                listener.on_xray_status(angle)

    def set_position(self, angle, token):
        self.send_cmd_is(b'\x0A', [token, int(angle*100)])
        pass

    # Would have only been used with Android
    # def request_position(self):
    #    self.send_cmd(b'\x0F')
    #    pass

    def is_ready(self):
        return self.client_connected