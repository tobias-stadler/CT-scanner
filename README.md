This repository contains all the software for my DIY computed tomography scanner. 

To perform a CT scan, one needs repeatable motion control and imaging hardware to create multiple X-ray images from different angles. These images can then be reconstructed into a 3D volume. The goal for this project was to build a working CT scanner on a budget. It was developed in 2020-2021 while I was in my final years of high school, where I had access to the fully-shielded educational X-ray machine pictured below. This X-ray machine has no digital X-ray detector, but a (somewhat degraded and super dim) phosphorescent screen for viewing the X-ray images. To digitize the images, I therefore use a normal camera to take pictures of the phosporescent screen. This requires very long exposure times (~20s per image) at low sensitivity (ISO100) to achieve a somewhat acceptable noise floor. The camera is controlled by an ESP32 microcontroller, which also controls a stepper motor for positioning the object inside the X-ray beam. The bulk of the work for this project was developing a piece software to control the recording of the images and process the crude X-ray photos into something usable that can be fed into a reconstruction algorithm. The software controls the imaging hardware via WiFi.

Main components:
- `core/`: image processing and reconstruction code
- `device/`: networking code to communciate with the motion control and camera hardware
- `gui/`: user interface for capturing, importing, processing and reconstructing CT scans
- `esp32-firmware/`: firmware for the ESP32 microcontroller used for motion control and image capture
# Example scans
![](images/figur3.jpg)
![](images/figur2.jpg)
![](images/figur.jpg)

![](images/pneumatik.jpg)
![](images/pneumatik2.jpg)

# Processing steps
The GUI is used to import and perform batch processing on the camera images.
Most important processing steps:
- Alignment Compensation: Crosshairs in the built-in image viewer can be used to visually annotate the photos to compensate for off-center placement of the camera and rotation axis. This is very important, because it is practically impossible to perfectly align the camera and motion control stage by hand. Misaligned images completely destroy the reconstruction result.
- Logarithm: X-ray intensity drops off exponentially with a rate dependent on the density of the materials it passes through. To compensate for this, the natural logarithm is computed for every pixel.

For reconstruction, I experimented with a few reconstruction libraries and settled on ASTRA Toolbox's CUDA-based SIRT3D algorithm, which provided the best results for my noisy data. The Simultaneous Iterative Reconstruction Technique (SIRT) generally performs significantly better on noisy data compared to the usual (filtered) backprojection based approaches.
In my setup, the arrangement of X-ray tube, motion control table and phosphorescent screen form what is commonly called a Cone Beam CT setup. For this setup, the relative distances and alignment of X-ray tube focus point, rotation axis and screen are important parameters for correct reconstruction. A combination of real life measurements and the visual alignment tools in the GUI are used to compute the correct scanner geometry for the reconstruction algorithm.
The reconstructed 3D volume is saved as a series of tiff-images, which can e.g. be viewed using 3D Slicer.
## Raw images
![](images/raw-compressed.gif)
## After preprocessing
![](images/proj-compressed.gif)
## After reconstruction
![](images/recon-compressed.gif)

# GUI
![](images/Main.PNG)
![](images/scanning.PNG)
![](images/processing.PNG)
![](images/recon.PNG)

# Setup
![](images/overview.png)
![](images/chamber.jpg)

# Stepper controller schematic
![](images/schaltplan.png)

# Installation
Word of caution: the code only supports the specific hardware I used and it might not be trivial to support other setups.

For the Python software: see `installation.txt`.

For the ESP32-firmware: Note that this code is NOT Arduino-based. It uses Espressif's esp-idf directly, so you need to be familiar with their development environment to build and flash this code.
