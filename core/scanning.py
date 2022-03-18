from device import detector, xray
from core.scandata import CTScanContext
import logging
import random

class CTScanRunner(detector.CTDetectorListener, xray.CTXRayListener):

    """
    State machine for capturing a sequence of projection images. It asynchronously sends the requests to hardware and progresses in the scan
    once the corresponding device response is received

    Typical state sequence: standby -> wait for move to requested angle -> wait for detector to finish capturing  |-------> done
                                     ^                                                                            |
                                     next                                                                         |
                                     |----------------------------------------------------------------- ----------|

    Additional states: waiting to pause, paused, resuming
    """

    def __init__(self):
        self.logger = logging.getLogger("CTScanRunner")
        self.scan_ctx = None
        self.update_callback = None
        self.req_pause = False
        self.pic_idx = 0
        self.state = 'standby' #wait_detector, wait_move, paused, done, resume, next, wait_pause
        self.move_token = -1
        self.detector_token = -1

    def __del__(self):
        self.release()
        self.scan_ctx.locked = False


    def set_scan_ctx(self, nscanctx: CTScanContext):
        """
        Supply handle to scan context (scan data, positioning device and detector)
        :param nscanctx: Context handle
        """
        if self.state != 'standby':
            self.logger.error('Failed to set scan context because scan is running')
            return
        self.scan_ctx = nscanctx

    def set_cb(self, fun):
        """
        Set callback function that is called when an internal state change occurs
        :param fun: reference to callback function
        """
        self.update_callback = fun

    def start(self):
        """
        Run the scan
        """
        if self.state != 'standby':
            self.logger.warning("Already running!")
            return

        if self.scan_ctx is None:
            self.logger.error("Scan context is none!")
            return

        if (self.scan_ctx.curr_scan is None) or (self.scan_ctx.dev_xray is None) or (self.scan_ctx.dev_detector is None):
            self.logger.error("Scan/Detector/XRay is none!")
            return

        if not self.scan_ctx.dev_xray.is_ready() or not self.scan_ctx.dev_detector.is_ready():
            self.logger.warning("Detector/XRay is not ready!")
            return

        self.scan_ctx.curr_scan.scan_prepare()
        self.scan_ctx.locked = True
        self.hook()
        self.pic_idx = 0
        self.__update_state('wait_move')
        self.logger.info("Starting scan with resolution %d", self.scan_ctx.curr_scan.get_resolution())

        self.move_token = random.randint(1, 0xFFFFFF)
        self.scan_ctx.dev_xray.set_position(self.scan_ctx.curr_scan.target_angles[self.pic_idx], self.move_token)

    def stop(self):
        """
        Abort the scan
        """
        self.release()
        self.req_pause = False
        self.__update_state('standby')
        self.scan_ctx.locked = False

    def pause(self):
        """
        Pause the scan
        """
        self.req_pause = True
        self.update_callback('wait_pause')

    def resume(self):
        """
        Resume the scan
        """
        if self.state == 'paused':
            self.__update_state('resume')
            self.next_step()

    def __update_state(self, newstate, notify=True):
        """
        Updates internal state
        :param newstate: new state
        :param notify: bool if callback should be notified about state change
        :return:
        """
        self.state = newstate
        if notify and self.update_callback is not None and not self.req_pause:
            self.update_callback(newstate)

    def next_step(self):
        """
        Capture next image
        """
        if self.req_pause:
            self.req_pause = False
            self.__update_state('paused')

        if self.state == 'paused':
            return

        if self.pic_idx < (len(self.scan_ctx.curr_scan.target_angles)-1):
            self.pic_idx += 1
            self.__update_state('wait_move')
            self.move_token = random.randint(1, 0xFFFFFF)
            self.scan_ctx.dev_xray.set_position(self.scan_ctx.curr_scan.target_angles[self.pic_idx], self.move_token)
        else:
            self.scan_ctx.locked = False
            self.__update_state('done')
            self.release()

    def hook(self):
        """
        Start listening for received data from the hardware devices
        """
        if self.scan_ctx.dev_detector is None or self.scan_ctx.dev_xray is None:
            raise RuntimeError("Detector or XRay uninitialized")
        self.scan_ctx.dev_detector.add_listener(self)
        self.scan_ctx.dev_xray.add_listener(self)

    def release(self):
        """
        Stop listening for data from the hardware devices
        """
        if self.scan_ctx is None or self.scan_ctx.dev_detector is None or self.scan_ctx.dev_xray is None:
            raise RuntimeError("Detector or XRay uninitialized")
        self.scan_ctx.dev_detector.remove_listener(self)
        self.scan_ctx.dev_xray.remove_listener(self)


    def on_xray_position_done(self, angle, token):
        """
        Internal handler that is called when positioning is done
        """
        if self.state == 'wait_move':
            if token != self.move_token:
                self.logger.error("Move: Wrong token")
                return

            self.scan_ctx.curr_scan.reached_angles.append(angle)
            self.__update_state('wait_detector')
            self.detector_token = random.randint(1, 0xFFFFFF)
            self.scan_ctx.dev_detector.capture_raw(self.scan_ctx.curr_scan.scan_parameters.shutterlen, self.scan_ctx.curr_scan.scan_parameters.exposure, self.scan_ctx.curr_scan.scan_parameters.focuslen, self.detector_token)

    def on_detector_raw(self, data, stride_pixel, stride_row, sensor, token):
        """
        Internal handler that is called when raw image capture is complete
        """
        self.logger.info("Detector: Receiving...")

        if token != self.detector_token:
            self.logger.error("Detector: Wrong token")
            return

        if self.state == 'wait_detector':
            # Unimplemented: saving image to disk when using android device instead of DSLM
            if data is not None:
                self.logger.info("Saving raw data")

            self.logger.info("Captured angle %d", self.scan_ctx.curr_scan.target_angles[self.pic_idx])
            self.__update_state('next')
            self.next_step() # Repeat the whole process

    # Debugging purpose
    def on_detector_test(self, data, token):
        self.logger.info("JPEG recvd")

