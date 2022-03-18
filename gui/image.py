import PIL
from PIL import ImageTk
from tkinter import *
import math
import time

class ImageFrame(LabelFrame):
    """
    GUI element for creating a movable and zoomable image viewer

    """
    def __init__(self, parent):
        super().__init__(parent, text="Image Viewer")

        #Settings
        self.scale = 1.0
        self.__delta = 1.3
        self.__filter = PIL.Image.ANTIALIAS  # NEAREST, BILINEAR, BICUBIC and ANTIALIAS
        self.__map_factor = 2
        self.__min_map_size = 256
        self.__max_freq = 60
        self.__last_render = 0

        #Scrollbars
        hbar = Scrollbar(self, orient='horizontal')
        vbar = Scrollbar(self, orient='vertical')
        hbar.grid(row=1, column=0, sticky='we')
        vbar.grid(row=0, column=1, sticky='ns')

        #Canvas
        self.canvas = Canvas(self, xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvas.grid(row=0, column=0, sticky=NSEW)
        self.canvas.update()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        hbar.configure(command=self.__scroll_x)
        vbar.configure(command=self.__scroll_y)

        # Bind events to canvas
        self.canvas.bind('<Configure>', lambda event: self.render_image())
        self.canvas.bind('<ButtonPress-1>', lambda event: self.canvas.scan_mark(event.x, event.y))
        self.canvas.bind('<B1-Motion>', self.event_mousedrag)
        self.canvas.bind('<MouseWheel>', self.event_mousewheel)
        self.canvas.bind('<Button-5>', self.event_mousewheel)
        self.canvas.bind('<Button-4>', self.event_mousewheel)

        self.mipmaps = None
        self.tkimg = None
        self.cimg = None
        self.img_w, self.img_h = 200, 200
        self.__min_side = 200
        self.img_dummy = self.canvas.create_rectangle((0, 0, self.img_w, self.img_h), width=0) #, fill='gray'
        self.canvas.focus_set()


    def __scroll_x(self, *args, **kwargs):
        self.canvas.xview(*args)  
        self.render_image()  

    def __scroll_y(self, *args, **kwargs):
        self.canvas.yview(*args) 
        self.render_image() 

    def render_image(self):
        """
        Recalculate image position and rerender canvas
        """

        if self.mipmaps is None:
            return

        curr = time.time() * 1000
        img_coords = self.canvas.coords(self.img_dummy)  # get image coords (canvas coords)
        visible_coords = (self.canvas.canvasx(0), self.canvas.canvasy(0), self.canvas.canvasx(self.canvas.winfo_width()), self.canvas.canvasy(self.canvas.winfo_height())) # get visible area of the canvas (canvas coords)
        img_coords_int = tuple(map(int, img_coords))

        #print("Int: " + str(img_coords_int))
        # Get scroll region
        scroll_coords = [min(img_coords_int[0], visible_coords[0]), min(img_coords_int[1], visible_coords[1]),
                      max(img_coords_int[2], visible_coords[2]), max(img_coords_int[3], visible_coords[3])]

        #print("Scroll: " + str(scroll_coords))

        self.canvas.configure(scrollregion=tuple(map(int, scroll_coords)))  # set scroll region

        # Calculate visible region of image dummy
        region_coords = [0, 0, 0, 0]

        region_coords[0] = max(visible_coords[0] - img_coords[0], 0)
        region_coords[1] = max(visible_coords[1] - img_coords[1], 0)

        region_coords[2] = min(visible_coords[2], img_coords[2]) - img_coords[0]
        region_coords[3] = min(visible_coords[3], img_coords[3]) - img_coords[1]

        #print("Region: " + str(region_coords))

        region_w = int(region_coords[2] - region_coords[0])
        region_h = int(region_coords[3] - region_coords[1])
        if region_w <= 0 or region_h <= 0:
            #print("OFR")
            return

        # Convert to pixel coords of full image
        tile_coords = [int(val / self.scale) for val in region_coords]
        #print("Tile: " + str(tile_coords))

        # Find most suitable mip map
        map_num = max(min(len(self.mipmaps) - 1, int((-1) * math.log(self.scale, self.__map_factor))), 0)
        map_scale_fac = self.__map_factor ** map_num
        #print("Scale: " + str(self.scale) + "; Mip: " + str(map_num) + "; Mip Fac: " + str(map_scale_fac))

        # Convert to pixel coords of mip map
        mip_coords = [int(val / map_scale_fac) for val in tile_coords]
        #print("Mipped: " + str(mip_coords))

        # Crop and resize image to fit visible area
        cropimg = self.mipmaps[map_num].crop(mip_coords)
        #print("Crop + Calc: " + str(time.time() * 1000 - curr))

        curr = time.time() * 1000
        rimg = cropimg.resize((region_w, region_h), self.__filter)
        #print("Resize: " + str(time.time() * 1000 - curr))

        curr = time.time() * 1000

        self.tkimg = ImageTk.PhotoImage(rimg)

        if self.cimg is None:
            self.canvas.delete(self.cimg)
            self.cimg = self.canvas.create_image(max(visible_coords[0], img_coords_int[0]), max(visible_coords[1], img_coords_int[1]), image=self.tkimg, anchor='nw')
        else:
            self.canvas.itemconfig(self.cimg, image=self.tkimg, anchor=NW)
            self.canvas.coords(self.cimg, max(visible_coords[0], img_coords_int[0]), max(visible_coords[1], img_coords_int[1]))

        #print("Update: " + str(time.time() * 1000 - curr))
        #self.canvas.lower(self.cimg)

    def event_mousedrag(self, event):
        """
        Event handler for mouse moves
        """
        self.canvas.focus_set()
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        #curr = time.time()
        #if curr - self.__last_render > (1/self.__max_freq):
        #   self.__last_render = curr

        self.render_image()


    def check_outside(self, x, y):
        """
        :param x:
        :param y:
        :return: True if point (x,y) is not inside the image
        """
        bbox = self.canvas.coords(self.img_dummy) 
        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
            return False 
        else:
            return True 

    def set_image(self, img: PIL.Image, reset=True):
        """
        Set image to be displayed
        :param img: PIL image
        :param reset: bool if image position needs to be reset. Needs to be true if image size changes
        :return:
        """
        if self.mipmaps is not None:
            for mip in self.mipmaps:
                mip.close()

        self.mipmaps = [img]
        if img is None:
            return

        needs_reset = (self.img_w, self.img_h) != self.mipmaps[0].size

        if reset or needs_reset:
            self.img_w, self.img_h = self.mipmaps[0].size
            self.__min_side = min(self.img_w, self.img_h)

            self.scale = 1.0
            self.canvas.coords(self.img_dummy, 0, 0, self.img_w, self.img_h)

        self.create_mipmaps()
        self.render_image()


    def event_mousewheel(self, event):
        """
        Mousewheel event handler
        """
        x = self.canvas.canvasx(event.x) 
        y = self.canvas.canvasy(event.y)
        cscale = 1.0
        if event.num == 5 or event.delta == -120: 
            if round(self.__min_side * self.scale) < 30: return 
            self.scale /= self.__delta
            cscale        /= self.__delta
        if event.num == 4 or event.delta == 120:
            i = min(self.canvas.winfo_width(), self.canvas.winfo_height()) >> 1
            if i < self.scale: return
            self.scale *= self.__delta
            cscale        *= self.__delta

        self.canvas.scale('all', x, y, cscale, cscale)  # rescale all objects
        self.render_image()


    def create_mipmaps(self):
        """
        Create multiple downscaled images
        """
        w = self.img_w
        h = self.img_h

        while w > self.__min_map_size or h > self.__min_map_size:
            w /= self.__map_factor
            h /= self.__map_factor
            #print("Mip: " + str(w) + ", " + str(h))
            self.mipmaps.append(self.mipmaps[0].resize(map(int, (w, h)), PIL.Image.ANTIALIAS))


    def destroy(self):
        """
        Free memory
        """
        self.set_image(None)
        self.canvas.destroy()
        super().destroy()