"""
Module to visualize a textured sphere with orientation from a quaternion.
"""
import numpy as np
from vispy import scene
from vispy.geometry import create_sphere
from vispy.io import imread
from vispy.visuals.filters import TextureFilter
from utils.quaternion import Quaternion

# Size of the rendered earth image visualization
IMAGE_SIZE = 400

class SphereOrientation:
    """Class to visualize sphere orientation using a quaternion.

    Parameters
    ----------
    render : bool, default True
        If True, open a window and render the sphere live.
        If False, keep an offscreen canvas for programmatic rendering
        (e.g., via `to_bytes`).
    """
    def __init__(self, render: bool = True):
        self.canvas = scene.SceneCanvas(
            keys='interactive', size=(IMAGE_SIZE, IMAGE_SIZE), show=render
        )
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'turntable'
        self.view.camera.distance = 4.0

        # Textured Earth sphere
        meshdata = create_sphere(radius=1.0, rows=24, cols=48)
        earth_image = imread("assets/earth_texture.jpg")
        self.sphere = scene.visuals.Mesh(
            meshdata=meshdata,
            shading='smooth',
            color='white',
            parent=self.view.scene
        )

        # Compute UVs (equirectangular mapping) for unit sphere
        verts = meshdata.get_vertices()
        norms = np.linalg.norm(verts, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vunit = verts / norms
        x, y, z = vunit[:, 0], vunit[:, 1], vunit[:, 2]
        lon = np.arctan2(y, x)
        u = (lon + np.pi) / (2 * np.pi)
        v = np.arccos(np.clip(z, -1.0, 1.0)) / np.pi
        texcoords = np.stack([u, v], axis=1).astype(np.float32)

        tex_filter = TextureFilter(earth_image, texcoords)
        self.sphere.attach(tex_filter)

        # Axes
        self.axes = scene.visuals.XYZAxis(
            parent=self.view.scene
        )

        # Transform (updated every frame)
        self.transform = scene.transforms.MatrixTransform()
        self.sphere.transform = self.transform
        self.axes.transform = self.transform

        if render:
            self.canvas.show()

    def update(self, quat: Quaternion):
        """Update sphere orientation from quaternion."""
        self.transform.matrix = quat.to_matrix4()
        self.canvas.update()

    def to_bytes(self, n_pixels: int = 200) -> bytes:
        """
        Render the current scene to an offscreen buffer and return raw
        RGB bitmap bytes.

        Parameters
        ----------
        n_pixels : int
            Total number of pixels (width*height). If provided,
            this function renders a square image with side
            ``sqrt(n_pixels)`` and returns ``n_pixels*3`` RGB bytes.

        Returns
        -------
        bytes 
            Row-major RGB bytes (R,G,B per pixel).
        """
        if n_pixels <= 0:
            raise ValueError("n_pixels must be > 0")
        dim = int(np.sqrt(n_pixels))
        if dim * dim != n_pixels:
            raise ValueError("n_pixels must be a perfect square (width*height)")
        render_size = (dim, dim)

        # Render to an offscreen framebuffer at the requested resolution
        img = self.canvas.render(size=render_size, alpha=False)
        # Ensure contiguous C-order before conversion to bytes
        if not img.flags['C_CONTIGUOUS']:
            img = np.ascontiguousarray(img)
        return img.tobytes(order='C')
