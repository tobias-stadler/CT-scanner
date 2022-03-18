from tkinter import *

from tkinter import simpledialog, filedialog, messagebox, font

from core import scandata, fs
from device import ctserver

from gui.scanning import ScanFrame
from gui.reconstruction import ReconstructionFrame
from gui.processing import ProcessingFrame

from pathlib import Path

import logging
import re

class MainFrame:
    """
    Main GUI window
    """
    def __init__(self):
        self.root = Tk()
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=12)
        self.root.title("GymCT")
        self.logger = logging.Logger("MainFrame")

        self.scan_ctx = scandata.CTScanContext()
        self.dev_xrayserver = None
        self.dev_photoserver = None
        self.device_setup()

        self.root.geometry("500x300")
        self.root['padx'] = 10
        self.root['pady'] = 10
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)

        self.root.wm_iconbitmap('res/GymCT-Logo.ico')

        self.frame_actions = None
        self.create_frame_actions()
        self.frame_status = None
        self.create_frame_status()
        self.frame_fs = None
        self.create_frame_fs()

        self.wnd_scan = None
        self.wnd_reconstruct = None
        self.wnd_processing = None

        self.update_connectionstat()

    def device_setup(self):
        """
        Initializes all hardware devices
        """
        self.dev_xrayserver = ctserver.XRayCTServer()
        self.dev_photoserver = ctserver.PhotoCTServer()
        self.scan_ctx.dev_xray = self.dev_xrayserver
        self.scan_ctx.dev_detector = self.dev_photoserver

    def start(self):
        """
        Starts device servers and passes execution to tkinter
        """
        self.dev_photoserver.update_callback = self.update_connectionstat
        self.dev_xrayserver.update_callback = self.update_connectionstat
        self.root.mainloop()

    def create_frame_fs(self):
        """
        Creates filesystem frame
        """
        self.frame_fs = LabelFrame(self.root, text="Filesystem", relief=RIDGE)
        self.frame_fs.grid(row=0, column=2, sticky=NSEW, padx=10)

        self.button_loadscan = Button(self.frame_fs, text="Load Scan", command=self.but_loadscan)
        self.button_closescan = Button(self.frame_fs, text="Close Scan", command=self.but_closescan)
        self.button_savescan = Button(self.frame_fs, text="Save Scan", command=self.but_savescan)
        self.button_createscan = Button(self.frame_fs, text="Create New Scan", command=self.but_createscan)
        self.label_currscan = Label(self.frame_fs, text="No Scan open")

        self.frame_fs['padx'] = 5
        self.frame_fs['pady'] = 5

        self.button_loadscan.pack(side=TOP, fill=BOTH, expand=True, pady=5)
        self.button_closescan.pack(side=TOP, fill=BOTH, expand=True, pady=5)
        self.button_savescan.pack(side=TOP, fill=BOTH, expand=True, pady=5)
        self.button_createscan.pack(side=TOP, fill=BOTH, expand=True, pady=5)
        self.label_currscan.pack(side=TOP, fill=X, expand=True, pady=5)

    def create_frame_status(self):
        """
        Creates device control and status frame
        """
        self.frame_status = LabelFrame(self.root, text="Status", relief=RIDGE)
        self.frame_status.grid(row=0, column=0, sticky=NSEW, padx=5)

        self.frame_status_xray = LabelFrame(self.frame_status, text="X-Ray Controller")
        self.frame_status_photo = LabelFrame(self.frame_status, text="Photo Controller")

        self.frame_status.grid_rowconfigure(0, weight=1)
        self.frame_status.grid_rowconfigure(1, weight=1)
        self.frame_status.grid_columnconfigure(0, weight=1)

        self.frame_status_xray.grid(row=0, column=0, sticky=NSEW, padx=5)
        self.frame_status_photo.grid(row=1, column=0, sticky=NSEW, padx=5)

        self.frame_status['padx'] = 5
        self.frame_status['pady'] = 5

        self.label_xraystatus = Label(self.frame_status_xray, text="N/A")
        self.label_photostatus = Label(self.frame_status_photo, text="N/A")
        self.label_xrayserver = Label(self.frame_status_xray, text="Server")
        self.label_photoserver = Label(self.frame_status_photo, text="Server")
        self.button_xrayserver = Button(self.frame_status_xray, text="Toggle", command=self.but_xserver)
        self.button_photoserver = Button(self.frame_status_photo, text="Toggle", command=self.but_pserver)

        self.label_xraystatus.grid(row=0, column=2, padx=3)
        self.label_photostatus.grid(row=1, column=2, padx=3)
        self.label_xrayserver.grid(row=0, column=0, padx=3)
        self.label_photoserver.grid(row=1, column=0, padx=3)
        self.button_xrayserver.grid(row=0, column=1, padx=3)
        self.button_photoserver.grid(row=1, column=1, padx=3)

    def create_frame_actions(self):
        """
        Creates frame with buttons to open other windows
        """
        self.frame_actions = LabelFrame(self.root, text="Actions", relief=RIDGE)
        self.frame_actions.grid(row=0, column=1, sticky=NSEW, padx=10)

        self.button_processing = Button(self.frame_actions, text="(Batch) Processing", command=self.but_processing)
        self.button_scan = Button(self.frame_actions, text="Scanning", command=self.but_scan)
        self.button_reconstruct = Button(self.frame_actions, text="Reconstruction", command=self.but_reconstruct)

        self.frame_actions['padx'] = 5
        self.frame_actions['pady'] = 5

        self.button_scan.pack(side=TOP, fill=BOTH, expand=True, pady=5)
        self.button_processing.pack(side=TOP, fill=BOTH, expand=True, pady=5)
        self.button_reconstruct.pack(side=TOP, fill=BOTH, expand=True, pady=5)

    def update_connectionstat(self):
        """
        Refresh connection status viewer
        """
        if(self.dev_xrayserver.client_connected):
            self.label_xraystatus['text'] = "Connected"
            self.label_xraystatus['background'] = 'green'
        elif(self.dev_xrayserver.running):
            self.label_xraystatus['text'] = "Running"
            self.label_xraystatus['background'] = 'yellow'
        else:
            self.label_xraystatus['text'] = "Stopped"
            self.label_xraystatus['background'] = 'red'

        if (self.dev_photoserver.client_connected):
            self.label_photostatus['text'] = "Connected"
            self.label_photostatus['background'] = 'green'
        elif (self.dev_photoserver.running):
            self.label_photostatus['text'] = "Running"
            self.label_photostatus['background'] = 'yellow'
        else:
            self.label_photostatus['text'] = "Stopped"
            self.label_photostatus['background'] = 'red'

    def but_processing(self):
        """
        Button event handler: Create and open processing window
        """
        if self.wnd_processing is None:
            self.wnd_processing = ProcessingFrame(self, self.scan_ctx)
            self.wnd_processing.root.protocol("WM_DELETE_WINDOW", self.wnd_processing.root.withdraw)
        else:
            self.wnd_processing.root.update()
            self.wnd_processing.root.deiconify()
            self.wnd_processing.root.lift(aboveThis=self.root)

        self.wnd_processing.root.focus()

    def but_scan(self):
        """
        Button event handler: Create and open scan control window
        """
        if self.wnd_scan is None:
            self.wnd_scan = ScanFrame(self, self.scan_ctx)
            self.wnd_scan.root.protocol("WM_DELETE_WINDOW", self.wnd_scan.root.withdraw)
        else:
            self.wnd_scan.root.update()
            self.wnd_scan.root.deiconify()
            self.wnd_scan.root.lift(aboveThis=self.root)

        self.wnd_scan.root.focus()

    def but_reconstruct(self):
        """
        Button event handler: Create and open reconstruction window
        """
        if self.wnd_reconstruct is None:
            self.wnd_reconstruct = ReconstructionFrame(self, self.scan_ctx)
            self.wnd_reconstruct.root.protocol("WM_DELETE_WINDOW", self.wnd_reconstruct_close)
        else:
            self.wnd_reconstruct.root.lift(aboveThis=self.root)

        self.wnd_reconstruct.root.focus()

    def but_loadscan(self):
        """
        Button event handler: Load scan
        """
        self.but_closescan()
        if self.scan_ctx.curr_scan is not None:
            return
        try:
            dirname = filedialog.askdirectory()#initialdir=Path.cwd()
            if dirname is None or len(dirname)==0:
                return
            self.scan_ctx.curr_scan = fs.load_ctscan(dirname)
            self.label_currscan['text'] = "Loaded Scan: " + str(self.scan_ctx.curr_scan.name)
        except EnvironmentError as e:
            print(e)
            messagebox.showinfo(title="Error", message="File not valid!")


    def but_closescan(self):
        """
        Button event handler: Close scan
        """
        if self.scan_ctx.locked:
            messagebox.showinfo(title="File action blocked", message="Scan context locked!")
            return
        if self.scan_ctx.curr_scan is None:
            return
        self.scan_ctx.curr_scan = None
        self.label_currscan['text'] = "No scan open"

    def but_savescan(self):
        """
        Button event handler: Save scan
        """

        if self.scan_ctx.curr_scan is None:
            return
        try:
            if self.scan_ctx.curr_scan.path is None:
                spath = Path(filedialog.askdirectory(initialdir=Path.cwd()))
            else:
                spath = self.scan_ctx.curr_scan.path.parents[1]

            fs.save_ctscan(self.scan_ctx.curr_scan, spath)

            self.label_currscan['text'] = "Saved Scan: " + str(self.scan_ctx.curr_scan.name)
        except EnvironmentError as e:
            print(e)
            messagebox.showinfo(title="Error", message="Failed to save scan!")

    def but_createscan(self):
        """
        Button event handler: Create new scan
        """
        self.but_closescan()
        if self.scan_ctx.curr_scan is not None:
            return
        while True:
            newname = simpledialog.askstring(title="Create new scan", prompt="Name for new scan: ")
            if newname is None:
                return
            m = re.search(r'[\w-]+', newname) # extract valid characters and ignore the rest
            if m:
                break
        self.logger.info("Created Scan %s", str(m.group()))
        self.scan_ctx.curr_scan = scandata.CTScan(m.group())
        self.label_currscan['text'] = "Created Scan: " + str(m.group())


    def wnd_scan_close(self):
        if self.wnd_scan is None:
            return
        self.wnd_scan.root.destroy()
        self.wnd_scan = None

    def wnd_reconstruct_close(self):
        if self.wnd_reconstruct is None:
            return
        self.wnd_reconstruct.root.destroy()
        self.wnd_reconstruct = None


    def but_pserver(self):
        """
        Button event handler: Toggle detector server state
        """
        if self.dev_photoserver.running:
            self.dev_photoserver.stop()
        else:
            self.dev_photoserver.start()

    def but_xserver(self):
        """
        Button event handler: Toggle xray server state
        """
        if self.dev_xrayserver.running:
            self.dev_xrayserver.stop()
        else:
            self.dev_xrayserver.start()
