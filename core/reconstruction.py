from pathlib import Path

import astra
import numpy as np

from core import fsutil, scandata


class ReconstructionProvider:
    """
    Interface for implementing different reconstruction algorithms
    """
    def __init__(self, scan : scandata.CTScan):
        self.scan = scan

    def reconstruct(self):
        pass

class ReconAstra3DCone(ReconstructionProvider):

    """
    Implementation of 3D cone beam reconstruction using ASTRA toolbox
    """

    def __init__(self, scan : scandata.CTScan):
        super().__init__(scan)

    def reconstruct(self):
        recon_params = self.scan.reconstruction_parameters
        geo_scan = self.scan.processing_parameters

        angles = self.scan.get_reached_angles_rad()
        print(angles)

        # Load projections into numpy array
        projections_raw = fsutil.load_img_as_np(str(self.scan.path.parent / Path("proj/" + recon_params.in_name + ".tiff")), stackaxis=1, downsample=geo_scan.downsample)


        h, num, w = projections_raw.shape
        print(w, num, h)
        print()

        # Calculate misalignment of rotation axis

        centerx = geo_scan.get_center()[0]
        rotaxis = geo_scan.get_rotaxis_x()
        #shift = (rotaxis-centerx+recon_params.axis_adj)/float(self.scan.downsample)
        shift = geo_scan.get_shift_x()+(recon_params.axis_adj/geo_scan.downsample)
        print("Axis Shift: %f" % shift)

        # Calculate reconstruction geometry

        # Magnification
        det_spacing = geo_scan.get_detector_spacing()

        print("Downsample: %f; Detector Spacing: %f; " % (geo_scan.downsample, det_spacing))
        #projection_geometry = astra.create_proj_geom('cone', det_spacing*recon_params.axis_adj, det_spacing*recon_params.axis_adj, h, w, angles, recon_params.dist_source_origin, recon_params.dist_origin_detector) # 2800 10
        projection_geometry = astra.create_proj_geom('cone', 1, 1, h, w, angles, (recon_params.dist_source_origin+recon_params.dist_origin_detector)/det_spacing, 0) # 2800 10
        #projection_geometry_vec = astra.geom_2vec(projection_geometry)
        projection_geometry_corrected = astra.geom_postalignment(projection_geometry, [-shift, 0])
        volume_geometry = astra.create_vol_geom(w, w, h)

        # Allocate memory

        projections_id = astra.data3d.create('-proj3d', projection_geometry_corrected, projections_raw)
        reconstruction_id = astra.data3d.create('-vol', volume_geometry, data=0)

        # Configure algorithm

        algorithm_cfg = astra.astra_dict(recon_params.algorithm)
        algorithm_cfg['ProjectionDataId'] = projections_id
        algorithm_cfg['ReconstructionDataId'] = reconstruction_id
        algorithm_id = astra.algorithm.create(algorithm_cfg)

        astra.algorithm.run(algorithm_id, recon_params.alg_iterations)

        # Export to disk

        reconstructed = astra.data3d.get(reconstruction_id)
        reconstructed[reconstructed < 0] = 0
        #reconstructed = reconstructed[:,: :]

        if recon_params.high_output != 1:
            reconstructed /= (np.max(reconstructed)*recon_params.high_output)
            reconstructed[reconstructed > 1] = 1
            print("Rescaling!")
        else:
            reconstructed /= np.max(reconstructed)
        #reconstructed = np.round(reconstructed * 255).astype(np.uint8)

        fsutil.save_np_as_img(reconstructed, str(self.scan.path.parent / Path("recon/" + recon_params.out_name + ".tiff")), cutaxis=0)

        # Free memory

        astra.algorithm.delete(algorithm_id)
        astra.data3d.delete(reconstruction_id)
        astra.data3d.delete(projections_id)
