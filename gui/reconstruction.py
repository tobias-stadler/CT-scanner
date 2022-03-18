from tkinter import *
from tkinter import messagebox
import threading
import re

from core import scandata
from core import reconstruction

class ReconstructionFrame:
    """
    GUI window for setting up reconstruction
    """

    def __init__(self, parent_frame, scan_ctx: scandata.CTScanContext):
        self.scan_ctx = scan_ctx
        self.parent = parent_frame
        self.root = Toplevel(self.parent.root)
        self.root.wm_iconbitmap('res/GymCT-Logo.ico')
        self.root.geometry("300x400")
        self.root.title("Reconstruction")


        self.root['padx'] = 5
        self.root['pady'] = 5

        self.button_iterate = Button(self.root, text="Reconstruct", command=self.but_reconstruct)
        self.button_iterate.grid(row=6, columnspan=2, rowspan=2, sticky=NSEW, padx=5, pady=5)

        self.button_emulate = Button(self.root, text="Simulate angles (forgot to save scan)", command=self.but_emulate)
        self.button_emulate.grid(row=5, columnspan=2, rowspan=1, sticky=NSEW, padx=5, pady=5)

        self.label_rotadj = Label(self.root, text="Roation-Axis adjustment")
        self.label_src_org = Label(self.root, text="Distance: Source <-> Origin")
        self.label_org_det = Label(self.root, text="Distance: Origin <-> Detector")
        self.label_in = Label(self.root, text="Input name")
        self.label_out = Label(self.root, text="Export name")
        self.label_alg = Label(self.root, text="Algorithm")
        self.label_alg_setting = Label(self.root, text="Iterations")

        self.entry_rotadj = Entry(self.root)
        self.entry_src_org = Entry(self.root)
        self.entry_org_det = Entry(self.root)
        self.entry_in = Entry(self.root)
        self.entry_out = Entry(self.root)
        self.entry_alg = Entry(self.root)
        self.entry_alg_setting = Entry(self.root)
        self.entry_downscale = Scale(self.root, from_=1, to=10, resolution=1, orient=HORIZONTAL, label="Downsample:")
        self.__bind_wheel(self.entry_downscale, 1)
        self.entry_post_high = Scale(self.root, from_=0, to=1, resolution=0.01, orient=HORIZONTAL, label="Maximum output value:")
        self.__bind_wheel(self.entry_post_high, 0.01)


        if self.scan_ctx.curr_scan is not None:
            curr = self.scan_ctx.curr_scan
            self.entry_post_high.set(curr.reconstruction_parameters.high_output)
            self.entry_rotadj.insert(0, str(curr.reconstruction_parameters.axis_adj))
            self.entry_src_org.insert(0, str(curr.reconstruction_parameters.dist_source_origin))
            self.entry_org_det.insert(0, str(curr.reconstruction_parameters.dist_origin_detector))
            self.entry_in.insert(0, str(curr.reconstruction_parameters.in_name))
            self.entry_out.insert(0, str(curr.reconstruction_parameters.out_name))
            self.entry_alg.insert(0, str(curr.reconstruction_parameters.algorithm))
            self.entry_alg_setting.insert(0, str(curr.reconstruction_parameters.alg_iterations))
            self.entry_downscale.set(curr.processing_parameters.downsample)
        else:
            self.entry_post_high.set(1)
            self.entry_rotadj.insert(0, "0")
            self.entry_src_org.insert(0, "100000")
            self.entry_org_det.insert(0, "0")
            self.entry_in.insert(0, "full")
            self.entry_out.insert(0, "recon")
            self.entry_alg.insert(0, "SIRT3D_CUDA")
            self.entry_alg_setting.insert(0, "100")
            self.entry_downscale.set(4)



        self.label_rotadj.grid(row=0, column=0, sticky=E + W)
        self.entry_rotadj.grid(row=0, column=1, sticky=E + W)
        self.label_src_org.grid(row=1, column=0, sticky=E + W)
        self.entry_src_org.grid(row=1, column=1, sticky=E + W)
        self.label_org_det.grid(row=2, column=0, sticky=E + W)
        self.entry_org_det.grid(row=2, column=1, sticky=E + W)
        self.label_in.grid(row=3, column=0, sticky=E + W)
        self.entry_in.grid(row=3, column=1, sticky=E + W)
        self.label_out.grid(row=4, column=0, sticky=E + W)
        self.entry_out.grid(row=4, column=1, sticky=E + W)
        self.entry_downscale.grid(row=8, column=0, columnspan=2, sticky=E + W)
        self.entry_post_high.grid(row=9, column=0, columnspan=2, sticky=E + W)

        self.entry_alg.grid(row=10, column=1, sticky=E + W)
        self.entry_alg_setting.grid(row=11, column=1, sticky=E + W)
        self.label_alg.grid(row=10, column=0, sticky=E + W)
        self.label_alg_setting.grid(row=11, column=0, sticky=E + W)

        self.root.grid_rowconfigure(6, weight=2)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.provider = None

    def but_reconstruct(self):
        """
        Button event handler: Set up reconstruction parameters and create reconstruction thread
        """
        if self.scan_ctx.curr_scan is None:
            messagebox.showerror(title="Reconstruction error", message="No scan loaded")
            return

        # Set reconstruction parameters
        try:
            self.scan_ctx.curr_scan.processing_parameters.downsample = self.entry_downscale.get()
            self.scan_ctx.curr_scan.reconstruction_parameters.high_output = self.entry_post_high.get()

            self.scan_ctx.curr_scan.reconstruction_parameters.dist_origin_detector = float(self.entry_org_det.get())
            self.scan_ctx.curr_scan.reconstruction_parameters.dist_source_origin = float(self.entry_src_org.get())
            self.scan_ctx.curr_scan.reconstruction_parameters.axis_adj = float(self.entry_rotadj.get())
            self.scan_ctx.curr_scan.reconstruction_parameters.algorithm = self.entry_alg.get()
            self.scan_ctx.curr_scan.reconstruction_parameters.alg_iterations = int(self.entry_alg_setting.get())

            out_name = self.entry_out.get()
            m = re.search(r'[A-Za-z]+', out_name)
            if not m:
                raise ValueError()
            self.scan_ctx.curr_scan.reconstruction_parameters.out_name = m.group()

            in_name = self.entry_in.get()
            m = re.search(r'[A-Za-z]+', in_name)
            if not m:
                raise ValueError()
            self.scan_ctx.curr_scan.reconstruction_parameters.in_name = m.group()

        except ValueError as e:
            messagebox.showerror(title="Reconstruction error", message="Invalid input value")
            return

        # Create reconstruction thread
        self.provider = reconstruction.ReconAstra3DCone(self.scan_ctx.curr_scan)

        recon_thread = threading.Thread(target=self.__run_worker())
        recon_thread.start()

        messagebox.showinfo(title="Reconstruction finished", message="Done!")

    def but_emulate(self):
        if self.scan_ctx.curr_scan is None:
            messagebox.showerror(title="Reconstruction error", message="No scan loaded")
            return

        self.scan_ctx.curr_scan.reached_angles = []

        max = self.scan_ctx.curr_scan.scan_max_angle
        img = self.scan_ctx.curr_scan.num_projections
        stepsPerRev = 800

        for i in range(img):
            res_deg = max/img
            angle = res_deg * i

            angle = round(angle*100)/100

            step_abs = round((angle/360.0)*stepsPerRev)

            angle_abs = (step_abs/stepsPerRev)*360.0
            #angle_resp = round(angle_abs*100.0)/100
            self.scan_ctx.curr_scan.reached_angles.append(angle_abs)

            # print("Angle: %f, Steps: %f, Angle reached: %f, Repsonse: %f" %(angle, step_abs, angle_abs, angle_resp))


    def __bind_wheel(self, entry, step):
        """
        Bind Scale to scroll wheel
        """
        entry.bind("<MouseWheel>", lambda event: entry.set(entry.get() + event.delta / abs(event.delta) * step))


    def __run_worker(self):
        """
        Code that gets run in reconstruction thread
        """

        if self.provider is None:
            return

        print("------------------ Reconstruction Start --------------------")
        self.provider.reconstruct()
        print("------------------ Reconstruction End ----------------------")



