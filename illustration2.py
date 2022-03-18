#Based on https://scikit-image.org/docs/dev/auto_examples/transform/plot_radon_transform.html (accessed on 05.11.2020)

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as anim

from skimage.data import shepp_logan_phantom
from skimage.transform import radon, rescale, frt2, radon_transform, iradon
from skimage import io
from scipy import fft
from matplotlib.colors import LogNorm
from matplotlib import cm
from matplotlib.transforms import Bbox
#image = shepp_logan_phantom()
image = io.imread("phantom.png")
image = image[:,:,1]

theta = np.linspace(0, 180, 180, endpoint=False)
filt = np.linspace(-1, 1, 100)
fimage = fft.fft2(image)
fimage = fft.fftshift(fimage)
sinogram = radon(image, theta=theta, circle=False)
proj = sinogram[:, 45]

intens = np.exp(proj*(-0.00001))

fproj = fft.fft(proj)


proj_abs = np.abs(proj).reshape(-1, 1)
intens_abs = np.abs(intens).reshape(-1, 1)

fig1, ax = plt.subplots(2, 6)
#colm = LinearSegmentedColormap.from_list("asdfs", [,])

cm.register_cmap(name='alpha_gradient',
                 data={'red':   [(0.,0,0),
                                 (1.,0,0)],

                       'green': [(0.,0.0,0.3),
                                 (1.,1,0)],

                       'blue':  [(0.,0,0),
                                 (1.,0,0)]})

ax[0, 0].imshow(image, cmap=plt.cm.Greys_r)
ax[0, 0].set_title("Schnittbild")

aaa = ax[0, 1].imshow(intens_abs, extent=(0, 100, 0, intens_abs.shape[0]), cmap='alpha_gradient')
ax[0, 1].set_title("Intensität")
fig1.colorbar(aaa)

ax[0, 2].plot(proj)
ax[1, 2].set_title("Projektion")

ax[0, 3].plot(intens)
ax[0, 3].set_title("Intensität")

ax[0, 4].plot(np.abs(filt))
ax[0, 4].set_title("Filter")

ax[0, 5].imshow(proj_abs, extent=(0, 100, 0, proj_abs.shape[0]), cmap=plt.cm.Greys_r)
ax[0, 5].set_title("Projektion")


plt.show()
