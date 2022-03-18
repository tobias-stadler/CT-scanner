import copy
import traceback
from tkinter import *
from tkinter import filedialog, messagebox

import numpy as np
from PIL import Image

from core import scandata, processing, fsimage
from gui import image


class ProcessingFrame:
    """
    GUI window for setting up the image processing
    """
    proc_prev: processing.ProcessingStack

    def __init__(self, parent_frame, scan_ctx: scandata.CTScanContext):
        self.scan_ctx = scan_ctx
        self.parent = parent_frame
        self.root = Toplevel(self.parent.root)
        self.root.wm_iconbitmap('res/GymCT-Logo.ico')
        self.root.geometry("1200x800")
        self.root.title("(Batch) Processing")


        self.__selected_control = 'circle' # circle, axis, crop

        self.__move_slow = 1
        self.__move_fast = 64

        self.frame_align = LabelFrame(self.root, text="Alignment")
        self.frame_align.grid(row=2, column=0, sticky=NSEW)

        self.frame_fs = LabelFrame(self.root, text="Images")
        self.frame_fs.grid(row=0, column=0, sticky=NSEW)

        self.frame_proc = LabelFrame(self.root, text="Preprocessing")
        self.frame_proc.grid(row=1, column=0, sticky=NSEW)

        self.mode_options = ["Raw", "Exposure", "Log", "Full"]
        self.mode_var = StringVar(self.frame_proc)
        self.mode_var.set(self.mode_options[0])

        self.mode_colorize = False

        self.dropdown_mode = OptionMenu(self.frame_proc, self.mode_var, *self.mode_options, command=self.but_changemode)
        self.dropdown_mode.pack(expand="YES", fill=X)

        self.button_proc_pre = Button(self.frame_proc, text="Preview", command=self.but_proc_preview)
        self.button_proc_pre.pack(expand="YES", fill=BOTH)

        self.button_proc_all = Button(self.frame_proc, text="Process All", command=self.but_proc_all)
        self.button_proc_all.pack(expand="YES", fill=BOTH)


        self.label_out = Label(self.frame_proc, text="Output name:")
        self.label_out.pack()
        self.entry_out = Entry(self.frame_proc)
        self.entry_out.pack(expand="YES", fill=X)



        self.entry_pre_low = Scale(self.frame_proc, from_=0, to=1, resolution=0.01, orient=HORIZONTAL, label="Pre Low:")
        self.entry_pre_low.pack(expand="YES", fill=X)

        self.entry_pre_high = Scale(self.frame_proc, from_=0, to=1, resolution=0.01, orient=HORIZONTAL, label="Pre High:")
        self.entry_pre_high.pack(expand="YES", fill=X)

        self.entry_post_low = Scale(self.frame_proc, from_=0, to=5, resolution=0.01, orient=HORIZONTAL, label="Post Low:")
        self.entry_post_low.pack(expand="YES", fill=X)

        self.entry_post_high = Scale(self.frame_proc, from_=0, to=5, resolution=0.01, orient=HORIZONTAL, label="Post High:")
        self.entry_post_high.pack(expand="YES", fill=X)


        self.button_import = Button(self.frame_fs, text="Import", command=self.but_import)
        self.button_import.pack(expand="YES", fill=BOTH)

        self.button_load = Button(self.frame_fs, text="Load", command=self.but_load)
        self.button_load.pack(expand="YES", fill=BOTH, pady=10)

        self.__pic_valcmd = self.root.register(self.__validate_picnum)

        self.label_picnum = Label(self.frame_fs, text="Picture index:")
        self.label_picnum.pack()

        self.entry_picnum = Entry(self.frame_fs, validate="all", validatecommand=(self.__pic_valcmd, '%P'))
        self.entry_picnum.pack(expand="YES", fill=X)


        self.button_apply = Button(self.frame_align, text="Apply to open scan", command=self.but_apply)
        self.button_apply.pack(expand="YES", fill=BOTH)

        self.button_circle = Button(self.frame_align, text="Circle", command=self.but_circle)
        self.button_circle.pack(expand="YES", fill=BOTH)

        self.button_axis = Button(self.frame_align, text="Rotation Axis", command=self.but_axis)
        self.button_axis.pack(expand="YES", fill=BOTH)

        self.button_crop = Button(self.frame_align, text="Crop", command=self.but_crop)
        self.button_crop.pack(expand="YES", fill=BOTH)

        self.__bind_wheel(self.entry_pre_low, 0.01)
        self.__bind_wheel(self.entry_pre_high, 0.01)
        self.__bind_wheel(self.entry_post_low, 0.01)
        self.__bind_wheel(self.entry_post_high, 0.01)

        self.entry_pre_high.set(1)
        self.entry_post_high.set(1)

        self.label_tutorial = Label(self.root, text="Use the ARROW KEYS to position the rotation axis and the calibration circle correctly. \n Use the buttons on the left to switch between 'Circle' and 'Rotation Axis'. \n No Function Key = slow movement; Hold CTRL = fast movement; \n Hold Shift = scale, Up/Down = slow, Left/Right = fast" )
        self.label_tutorial.grid(row=2, column=1, sticky=NSEW)

        self.but_circle()

        self.imgcanvas = image.ImageFrame(self.root)
        self.imgcanvas.grid(column=1, row=0, rowspan=2, sticky=NSEW)

        self.circle = self.imgcanvas.canvas.create_oval(0, 0, 0, 0, outline='red')
        self.cross_horiz = self.imgcanvas.canvas.create_line(0, 0, 0, 0, fill='red')
        self.cross_vert = self.imgcanvas.canvas.create_line(0, 0, 0, 0, fill='red')
        self.rotaxis = self.imgcanvas.canvas.create_line(0, 0, 0, 0, fill='orange')
        self.rotaxis_rect = self.imgcanvas.canvas.create_rectangle(0, 0, 0, 0, outline='orange')
        self.crop_rect =  self.imgcanvas.canvas.create_rectangle(0, 0, 0, 0, outline='blue')

        # Init overlay coords
        self.circle_coords = [0, 0, 500] # top left (x, y, diameter)
        self.axis_coords = [260, 300, 50, 50] # top left (x, y, width, height)
        self.crop_coords = [256, 128] # (width, height)

        self.imgcanvas.canvas.bind('<Shift-Key>', lambda event: self.imgcanvas.canvas.after_idle(self.event_key_shift, event))
        self.imgcanvas.canvas.bind('<Control-Key>', lambda event: self.imgcanvas.canvas.after_idle(self.event_key_ctrl, event))
        self.imgcanvas.canvas.bind('<Key>', lambda event: self.imgcanvas.canvas.after_idle(self.event_key, event))

        self.imgcanvas.canvas.tag_raise(self.circle)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=20)

        self.projection = None
        self.curr_img = None
        self.proc_prev = None
        self.update_overlay()

    def __low_limit(self, arr, lim, skip=()):
        """
        Cut off all values below the specified limit
        :param arr: list of values to be limited
        :param lim: lowest allowed value
        :param skip: list of indices to be skipped
        :return:
        """
        for i in range(len(arr)):
            if i in skip:
                continue
            if arr[i] < lim:
                arr[i] = lim

    def __validate_picnum(self, val):
        """
        Validation if input string is a valid picture index
        :param val: input string
        :return: bool if valid
        """
        if val.isnumeric() and self.scan_ctx.curr_scan is not None:
            return True
        return False

    def __bind_wheel(self, entry, step):
        """
        Bind Scale to scroll wheel
        """
        entry.bind("<MouseWheel>", lambda event: entry.set(entry.get() + event.delta / abs(event.delta) * step))


    def but_proc_preview(self):
        """
        Button event handler: Pass selected values to processing stack and preview loaded image
        """
        if self.projection is None or self.proc_prev is None:
            return

        print(self.entry_post_low.get())
        self.proc_prev.get_processor("limit_post").low_limit = self.entry_post_low.get()
        self.proc_prev.get_processor("limit_post").high_limit = self.entry_post_high.get()
        self.proc_prev.get_processor("limit_pre").low_limit = self.entry_pre_low.get()
        self.proc_prev.get_processor("limit_pre").high_limit = self.entry_pre_high.get()

        arr = self.proc_prev.execute(self.projection, auto=True)
        arr *= 255
        arr = np.uint8(arr)

        if self.mode_colorize:
            red = np.array(arr)
            green = np.array(arr)
            blue = np.array(arr)

            # Black => red
            red[arr<=0] = 255

            # Green
            red[arr>=255] = 0
            green[arr>=255] = 255
            blue[arr>=255] = 0

            img = np.stack([red, green, blue], axis=2)
            self.curr_img = Image.fromarray(img, 'RGB')
        else:
            self.curr_img = Image.fromarray(arr)

        self.imgcanvas.set_image(self.curr_img, reset=False)

        self.update_overlay()

    def but_proc_all(self):
        """
        Button event handler: process all images
        """
        if self.scan_ctx.curr_scan is None:
            return 

        out_name = self.entry_out.get()
        m = re.search(r'[A-Za-z]+', out_name)
        if not m:
            messagebox.showerror(title="Processing error", message="Invalid output name")
            return
        self.scan_ctx.curr_scan.processing_parameters.out_name = m.group()
        self.scan_ctx.curr_scan.process_all()


    def but_changemode(self, val):
        """
        Drop down menu selection event handler: change viewer mode
        """
        if self.proc_prev is None:
            return

        self.proc_prev.disable_all()
        self.mode_colorize = False

        if val == "Raw":
            self.proc_prev.enable_list(range(0, 1))
        elif val == "Exposure":
            self.proc_prev.enable_list(range(0, 3))
            self.mode_colorize = True
        elif val == "Log":
            self.proc_prev.enable_all()
            self.mode_colorize = True
            pass
        elif val == "Full":
            self.proc_prev.enable_all()


        self.but_proc_preview()

    def  update_overlay(self):
        """
        Recalculates coordinates for overlay polygons and rerenders them
        """

        self.__low_limit(self.crop_coords, 0)
        self.__low_limit(self.circle_coords, 0, (0, 1))
        self.__low_limit(self.axis_coords, 0)

        img_coords = self.imgcanvas.canvas.coords(self.imgcanvas.img_dummy)
        scl = self.imgcanvas.scale

        # Recalculate coords
        circle_corr = [self.circle_coords[0] * scl + img_coords[0], self.circle_coords[1] * scl + img_coords[1], self.circle_coords[2] * scl]
        crop_corr = [self.crop_coords[0] * scl, self.crop_coords[1] * scl]
        axis_corr = [self.axis_coords[0] * scl + img_coords[0], self.axis_coords[1] * scl + img_coords[1], self.axis_coords[2] * scl, self.axis_coords[3] * scl]

        #print(img_coords, scl)
        #print(self.circle_coords)
        #print(corrected_coords)
        center_x = circle_corr[0] + circle_corr[2] / 2
        center_y = circle_corr[1] + circle_corr[2] / 2

        # Rerender circle and cross
        self.imgcanvas.canvas.coords(self.circle, circle_corr[0], circle_corr[1], circle_corr[0]+circle_corr[2], circle_corr[1]+circle_corr[2])
        self.imgcanvas.canvas.coords(self.cross_horiz, circle_corr[0], center_y, circle_corr[0]+circle_corr[2], center_y)
        self.imgcanvas.canvas.coords(self.cross_vert, center_x, circle_corr[1], center_x, circle_corr[1] + circle_corr[2])

        # Rerender crop rectangle
        self.imgcanvas.canvas.coords(self.crop_rect, center_x - crop_corr[0]/2, center_y - crop_corr[1]/2, center_x + crop_corr[0]/2, center_y + crop_corr[1]/2)

        # Rerender rotation axis
        self.imgcanvas.canvas.coords(self.rotaxis_rect, axis_corr[0], axis_corr[1], axis_corr[0] + axis_corr[2], axis_corr[1] + axis_corr[3])
        axis_x = axis_corr[0] + axis_corr[2]/2
        self.imgcanvas.canvas.coords(self.rotaxis, axis_x, circle_corr[1], axis_x, circle_corr[1] + circle_corr[2])

        # Move overlay elements over the image
        self.imgcanvas.canvas.tag_raise(self.circle)
        self.imgcanvas.canvas.tag_raise(self.cross_vert)
        self.imgcanvas.canvas.tag_raise(self.cross_horiz)
        self.imgcanvas.canvas.tag_raise(self.rotaxis)
        self.imgcanvas.canvas.tag_raise(self.rotaxis_rect)
        self.imgcanvas.canvas.tag_raise(self.crop_rect)

    # Button event handlers for selecting which overlay is controlled by the arrow keys
    def but_circle(self):
        self.button_circle['state'] = 'disabled'
        self.button_axis['state'] = 'normal'
        self.button_crop['state'] = 'normal'
        self.__selected_control = 'circle'

    def but_axis(self):
        self.button_circle['state'] = 'normal'
        self.button_axis['state'] = 'disabled'
        self.button_crop['state'] = 'normal'
        self.__selected_control = 'axis'

    def but_crop(self):
        self.button_circle['state'] = 'normal'
        self.button_axis['state'] = 'normal'
        self.button_crop['state'] = 'disabled'
        self.__selected_control = 'crop'


    def but_apply(self):
        """
        Button event handler: Save geometry in scan object
        """
        self.update_overlay()
        if self.scan_ctx.curr_scan is not None:
            self.scan_ctx.curr_scan.processing_parameters.coords_align = list(self.circle_coords)
            self.scan_ctx.curr_scan.processing_parameters.coords_axis = list(self.axis_coords)
            self.scan_ctx.curr_scan.processing_parameters.coords_crop = list(self.crop_coords)



    def but_load(self):
        """
        Button event handler: Load specified projection
        """
        if self.scan_ctx.curr_scan is None:
            messagebox.showerror(title="Processing error", message="No scan loaded")
            return

        self.proc_prev = copy.copy(self.scan_ctx.curr_scan.processing_stack) #Shallow copy ProcessingStack -> references the same processors as CTSCan.processing_stack but allows independent control over enabling/disabling

        try:
            num = int(self.entry_picnum.get()) - 1
            if num not in range(self.scan_ctx.curr_scan.num_projections):
                raise Exception("")
        except Exception as e:
            messagebox.showerror(title="Processing error", message="Invalid projection number")
            traceback.print_exc()
            return


        if self.scan_ctx.curr_scan.processing_parameters.coords_align:
            self.circle_coords = list(self.scan_ctx.curr_scan.processing_parameters.coords_align)

        if self.scan_ctx.curr_scan.processing_parameters.coords_axis:
            self.axis_coords = list(self.scan_ctx.curr_scan.processing_parameters.coords_axis)

        if self.scan_ctx.curr_scan.processing_parameters.coords_crop:
            self.crop_coords = list(self.scan_ctx.curr_scan.processing_parameters.coords_crop)


        if self.proc_prev.get_processor("limit_post").low_limit is not None:
            self.entry_post_low.set(self.proc_prev.get_processor("limit_post").low_limit)

        if self.proc_prev.get_processor("limit_post").high_limit is not None:
            self.entry_post_high.set(self.proc_prev.get_processor("limit_post").high_limit)

        if self.proc_prev.get_processor("limit_pre").low_limit is not None:
            self.entry_pre_low.set(self.proc_prev.get_processor("limit_pre").low_limit)

        if self.proc_prev.get_processor("limit_pre").high_limit is not None:
            self.entry_pre_high.set(self.proc_prev.get_processor("limit_pre").high_limit)


        try:
            self.projection = fsimage.load_projection_raw_pana(self.scan_ctx.curr_scan.path.parent, num)
        except Exception as e:
            messagebox.showerror(title="Processing error", message=str(e))
            traceback.print_exc()

        self.update_overlay()
        self.but_changemode("Raw")


    def but_import(self):
        """
        Button event handler: Import images from SD-card to scan folder
        """
        if self.scan_ctx.curr_scan is None:
            messagebox.showerror(title="Processing error", message="No Scan loaded")
            return

        fpath = filedialog.askopenfilename()
        if fpath is None:
            return

        try:
            if self.scan_ctx.curr_scan.path is None:
                raise FileNotFoundError("Scan has no location on disk. It needs to be saved at least once")
            fsimage.import_images(self.scan_ctx.curr_scan.path.parent, fpath, self.scan_ctx.curr_scan.num_projections)

        except Exception as e:
            messagebox.showerror(title="Processing error", message=str(e))
            traceback.print_exc()


    def event_key(self, event):
        #print("Normal")
        """
        Event handler for keyboard input while no function key is pressed
        """
        if event.keysym == "s" and self.curr_img is not None:
            print("Screenshot!")
            self.curr_img.save("screenshot.jpeg")


        if self.__selected_control == 'circle':
            if event.keycode == 39:  # right arrow
                self.circle_coords[0] += self.__move_slow
            elif event.keycode == 37:  # left arrow
                self.circle_coords[0] -= self.__move_slow
            elif event.keycode == 38:  # up arrow
                self.circle_coords[1] -= self.__move_slow
            elif event.keycode == 40:  # down arrow
                self.circle_coords[1] += self.__move_slow

        elif self.__selected_control == 'axis':
            if event.keycode == 39:  # right arrow
                self.axis_coords[0] += self.__move_slow
            elif event.keycode == 37:  # left arrow
                self.axis_coords[0] -= self.__move_slow
            elif event.keycode == 38:  # up arrow
                self.axis_coords[1] -= self.__move_slow
            elif event.keycode == 40:  # down arrow
                self.axis_coords[1] += self.__move_slow

        elif self.__selected_control == 'crop':
            if event.keycode == 39:  # right arrow
                self.crop_coords[0] += self.__move_slow
            elif event.keycode == 37:  # left arrow
                self.crop_coords[0] -= self.__move_slow
            elif event.keycode == 38:  # up arrow
                self.crop_coords[1] += self.__move_slow
            elif event.keycode == 40:  # down arrow
                self.crop_coords[1] -= self.__move_slow

        self.update_overlay()

    def event_key_ctrl(self, event):
        #print("Ctrl")
        """
        Event handler for keyboard input while Ctrl-key is pressed
        """
        if self.__selected_control == 'circle':
            if event.keycode == 39:  # right arrow
                self.circle_coords[0] += self.__move_fast
            elif event.keycode == 37:  # left arrow
                self.circle_coords[0] -= self.__move_fast
            elif event.keycode == 38:  # up arrow
                self.circle_coords[1] -= self.__move_fast
            elif event.keycode == 40:  # down arrow
                self.circle_coords[1] += self.__move_fast

        if self.__selected_control == 'axis':
            if event.keycode == 39:  # right arrow
                self.axis_coords[0] += self.__move_fast
            elif event.keycode == 37:  # left arrow
                self.axis_coords[0] -= self.__move_fast
            elif event.keycode == 38:  # up arrow
                self.axis_coords[1] -= self.__move_fast
            elif event.keycode == 40:  # down arrow
                self.axis_coords[1] += self.__move_fast

        elif self.__selected_control == 'crop':
            if event.keycode == 39:  # right arrow
                self.crop_coords[0] += self.__move_fast
            elif event.keycode == 37:  # left arrow
                self.crop_coords[0] -= self.__move_fast
            elif event.keycode == 38:  # up arrow
                self.crop_coords[1] += self.__move_fast
            elif event.keycode == 40:  # down arrow
                self.crop_coords[1] -= self.__move_fast

        self.update_overlay()

    def event_key_shift(self, event):
        #print("Shift")
        """
        Event handler for keyboard input while Shift-key is pressed
        """
        if self.__selected_control == 'circle':
            if event.keycode == 39:  # right arrow
                self.circle_coords[2] += self.__move_fast
                self.circle_coords[1] -= self.__move_fast/2
            elif event.keycode == 37:  # left arrow
                self.circle_coords[2] -= self.__move_fast
                self.circle_coords[1] += self.__move_fast/2
            elif event.keycode == 38:  # up arrow
                self.circle_coords[2] += self.__move_slow
                self.circle_coords[1] -= self.__move_slow/2
            elif event.keycode == 40:  # down arrow
                self.circle_coords[2] -= self.__move_slow
                self.circle_coords[1] += self.__move_slow/2

        elif self.__selected_control == 'axis':
            if event.keycode == 39:  # right arrow
                self.axis_coords[2] += self.__move_fast
            elif event.keycode == 37:  # left arrow
                self.axis_coords[2] -= self.__move_fast
            elif event.keycode == 38:  # up arrow
                self.axis_coords[2] += self.__move_slow
            elif event.keycode == 40:  # down arrow
                self.axis_coords[2] -= self.__move_slow

        self.update_overlay()