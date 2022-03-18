from tkinter import *
from tkinter import messagebox

from core import scandata, scanning
from device import detector
import logging


class ScanFrame(detector.CTDetectorListener):
    """
    GUI window for controlling CT scans
    """

    def __init__(self, parent_frame, scan_ctx: scandata.CTScanContext):
        self.parent = parent_frame
        self.scan_ctx = scan_ctx
        self.root = Toplevel(self.parent.root)
        self.root.wm_iconbitmap('res/GymCT-Logo.ico')
        self.root.geometry("500x300")
        self.root.title("Scanning")

        self.logger = logging.getLogger("ScanFrame")

        self.root['padx'] = 5
        self.root['pady'] = 5

        self.root.grid_rowconfigure(0, weight=20)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=5)

        self.frame_actions = LabelFrame(self.root, text="Control", relief=RIDGE)
        self.frame_actions.grid(row=0, column=0, sticky=NSEW, padx=10)

        self.frame_settings = LabelFrame(self.root, text="Settings")
        self.frame_settings.grid(row=0, column=1, sticky=NSEW, padx=10)



        self.button_start = Button(self.frame_actions, text="Start Scan", command=self.but_start)
        self.button_abort = Button(self.frame_actions, text="Abort Scan", command=self.but_abort)
        self.button_pause = Button(self.frame_actions, text="Pause Scan", command=self.but_pause)
        self.button_resume = Button(self.frame_actions, text="Resume Scan", command=self.but_resume)
        self.label_stat = Label(self.frame_actions, text="Scan not running")

        self.label_shutterlen = Label(self.frame_settings, text="Button Hold Time")#shutterlen
        self.label_exposure = Label(self.frame_settings, text="Exposure Time")
        self.label_focus = Label(self.frame_settings, text="Focusing Time")#Focus
        self.label_num = Label(self.frame_settings, text="Image Count")
        self.label_max = Label(self.frame_settings, text="Max Angle")
        self.entry_shutterlen = Entry(self.frame_settings)
        self.entry_exposure = Entry(self.frame_settings)
        self.entry_focus = Entry(self.frame_settings)
        self.entry_num = Entry(self.frame_settings)
        self.entry_max = Entry(self.frame_settings)
        self.button_testcapture = Button(self.frame_settings, text="Test Capture", command=self.but_testcapture)
        self.button_testzero = Button(self.frame_settings, text="0°", command=self.but_testzero)
        self.button_testhalf = Button(self.frame_settings, text="180°", command=self.but_testhalf)
        self.button_testfull = Button(self.frame_settings, text="360°", command=self.but_testfull)
        self.button_updateparams = Button(self.frame_settings, text="Save Parameters", command=self.update_scan_options)
        self.entry_shutterlen.insert(0, "500")
        self.entry_exposure.insert(0, "41000")
        self.entry_focus.insert(0, "500")
        self.entry_num.insert(0, "60")
        self.entry_max.insert(0, "360")


        # self.entry_shutterlen.bind("<MouseWheel>", lambda event: self.entry_shutterlen.set(self.entry_shutterlen.get()+event.delta/abs(event.delta)*50))
        # self.entry_focus.bind("<MouseWheel>", lambda event: self.entry_focus.set(self.entry_focus.get()+event.delta/abs(event.delta)*50))
        # self.entry_exposure.bind("<MouseWheel>", lambda event: self.entry_exposure.set(self.entry_exposure.get()+event.delta/abs(event.delta)*500))

        self.button_start.pack(side=TOP, fill=BOTH, expand=True, pady=5)
        self.button_abort.pack(side=TOP, fill=BOTH, expand=True, pady=5)
        self.button_pause.pack(side=TOP, fill=BOTH, expand=True, pady=5)
        self.button_resume.pack(side=TOP, fill=BOTH, expand=True, pady=5)
        self.label_stat.pack(side=TOP, fill=BOTH, expand=True, pady=5)

        self.label_shutterlen.grid(row=0, column=0, sticky=E+W)
        self.entry_shutterlen.grid(row=0, column=1, sticky=E+W)
        self.label_exposure.grid(row=1, column=0, sticky=E+W)
        self.entry_exposure.grid(row=1, column=1, sticky=E+W)
        self.label_focus.grid(row=2, column=0, sticky=E+W)
        self.entry_focus.grid(row=2, column=1, sticky=E+W)
        self.label_num.grid(row=3, column=0, sticky=E+W)
        self.entry_num.grid(row=3, column=1, sticky=E+W)
        self.label_max.grid(row=4, column=0, sticky=E+W)
        self.entry_max.grid(row=4, column=1, sticky=E+W)
        self.button_testcapture.grid(row=5, column=0, columnspan=2, sticky=NSEW)
        self.button_testzero.grid(row=6, column=0, columnspan=2, sticky=NSEW)
        self.button_testhalf.grid(row=7, column=0, columnspan=2, sticky=NSEW)
        self.button_testfull.grid(row=8, column=0, columnspan=2, sticky=NSEW)
        self.button_updateparams.grid(row=9, column=0, columnspan=2, sticky=NSEW)

        self.frame_settings.grid_columnconfigure(0, weight=1)
        self.frame_settings.grid_columnconfigure(1, weight=30)
        self.frame_settings.grid_rowconfigure(5, weight=1)
        self.frame_settings.grid_rowconfigure(6, weight=1)
        self.frame_settings.grid_rowconfigure(7, weight=1)
        self.frame_settings.grid_rowconfigure(8, weight=1)

        self.scanrun = scanning.CTScanRunner()
        self.scanrun.set_cb(self.update_state)
        self.update_state('standby')



    def update_state(self, newstate):
        """
        State change callback
        :param newstate: updated state
        """

        if self.scan_ctx.curr_scan is not None and self.scanrun.pic_idx<len(self.scan_ctx.curr_scan.reached_angles):
            self.label_stat['text'] = str(self.scan_ctx.curr_scan.reached_angles[self.scanrun.pic_idx]) + "/" + str(self.scan_ctx.curr_scan.scan_max_angle) + "°"

        if newstate == 'standby':
            self.button_start['state'] = 'normal'
            self.button_abort['state'] = 'disabled'
            self.button_pause['state'] = 'disabled'
            self.button_resume['state'] = 'disabled'
        elif newstate == 'wait_pause':
            self.button_start['state'] = 'disabled'
            self.button_abort['state'] = 'normal'
            self.button_pause['state'] = 'disabled'
            self.button_resume['state'] = 'disabled'
            self.label_stat['text'] = "Pausing..."
        elif newstate == 'wait_detector' or newstate == 'wait_move':
            self.button_start['state'] = 'disabled'
            self.button_abort['state'] = 'normal'
            self.button_pause['state'] = 'normal'
            self.button_resume['state'] = 'disabled'
        elif newstate == 'paused':
            self.button_start['state'] = 'disabled'
            self.button_abort['state'] = 'normal'
            self.button_pause['state'] = 'disabled'
            self.button_resume['state'] = 'normal'
            self.label_stat['text'] = "Scan paused"
        elif newstate == 'resume':
            self.button_start['state'] = 'disabled'
            self.button_abort['state'] = 'normal'
            self.button_pause['state'] = 'disabled'
            self.button_resume['state'] = 'disabled'
            self.label_stat['text'] = "Resuming..."

        elif newstate == 'done':
            self.done_callback()

    def done_callback(self):
        """
        Scan done callback
        """
        messagebox.showinfo("Scanning", "Done")
        self.scan_reset()

    def but_testcapture(self):
        """
        Button event handler: Record a test capture to confirm everything working
        """
        self.scan_ctx.dev_detector.capture_raw(int(self.entry_shutterlen.get()), int(self.entry_exposure.get()), int(self.entry_focus.get()), 0)

    def but_testzero(self):
        """
        Button event handler: Move axis to home position
        """
        self.scan_ctx.dev_xray.set_position(0, 0)

    def but_testhalf(self):
        """
        Button event handler: Move axis to 180°
        """
        self.scan_ctx.dev_xray.set_position(180, 0)

    def but_testfull(self):
        """
        Button event handler: Move axis to 360°
        """
        self.scan_ctx.dev_xray.set_position(360, 0)

    def update_scan_options(self):
        """
        Update scan object with chosen parameters
        """
        self.scan_ctx.curr_scan.scan_parameters.shutterlen = int(self.entry_shutterlen.get())
        self.scan_ctx.curr_scan.scan_parameters.exposure = int(self.entry_exposure.get())
        self.scan_ctx.curr_scan.scan_parameters.focuslen = int(self.entry_focus.get())
        self.scan_ctx.curr_scan.num_projections = int(self.entry_num.get())
        self.scan_ctx.curr_scan.scan_max_angle = int(self.entry_max.get())

    def but_start(self):
        """
        Button event handler: Start scan
        """
        if self.scan_ctx.curr_scan is None:
            messagebox.showinfo(title="Scan failed", message="No scan loaded in context")
            return

        try:
            self.update_scan_options()
        except ValueError as e:
            messagebox.showerror(title="Scan failed", message="Invalid parameters!")

        self.scanrun.set_scan_ctx(self.scan_ctx)
        self.scanrun.start()

    def but_abort(self):
        """
        Button event handler: Abort scan
        """
        self.scan_reset()

    def scan_reset(self):
        """
        Aborts scan and resets GUI to default
        """
        if self.scanrun is not None:
            self.scanrun.stop()

        self.label_stat['text'] = "Scan aborted"

    def but_pause(self):
        """
        Button event handler: Abort scan
        """
        self.scanrun.pause()

    def but_resume(self):
        """
        Button event handler: Resume scan
        """
        self.scanrun.resume()