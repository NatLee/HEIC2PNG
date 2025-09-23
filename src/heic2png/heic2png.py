import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

class HEIC2PNG:
    def __init__(self, image_file_path: Optional[str] = "",
                 quality: Optional[int] = None,
                 overwrite: bool = False):
        """
        Initializes the HEIC2PNG converter.

        :param image_file_path: Path to the HEIC image file.
        :param quality: Quality of the converted PNG image (1-100).
        :param overwrite: Whether to overwrite the file if it already exists.
        """
        if not image_file_path:
            stdin = (os.fdopen(sys.stdin.fileno(), "rb")
                if "b" not in sys.stdin.mode else sys.stdin)
            self.image_file_path = stdin
        # TODO: I'm not a Python type hints maven. The image_file_path type
        # needs to reflect that an open file object is also acceptable.
        elif hasattr("fileno", image_file_path):
            pass                        # already open file
        else:
            self.image_file_path: Path = Path(image_file_path)
            if self.image_file_path.suffix.lower() != '.heic':
                raise ValueError("The provided file is not a HEIC image.")
        self.quality: Optional[int] = quality
        self.overwrite: bool = overwrite

        self.image: Image.Image = Image.open(self.image_file_path)

    def save(self, output_image_file_path: Optional[str] = "",
             extension: str = '.png') -> Path:
        """
        Converts and saves the input image to another format.

        The default output format is PNG.

        :param output_image_file_path: Path to save the converted PNG image.
        :param extension: The file extension of the converted image.
        :return: Path where the converted image is saved.
        """
        if not output_image_file_path:
            stdout = (os.fdopen(sys.stdout.fileno(), "wb")
                if "b" not in sys.stdout.mode else sys.stdout)
            output_path = stdout
        else:
            output_path: Path = Path(output_image_file_path)

        # TODO: Not sure this is correct, there's probably a better mapping
        # between image file extensions and file formats. For example, see the
        # output of `python -m PIL`.
        self.image.save(output_path, format=extension.replace(".", "").upper())

        # TODO: Skip this step if the output format isn't PNG or pngquant can't
        # be found?
        # Optimize PNG with pngquant if quality is specified
        if self.quality and self.quality != 100:
            quality_str: str = f'{self.quality}-{self.quality}'
            subprocess.run(['pngquant', '--quality', quality_str, '-f', '-o', str(output_path), str(output_path)])

        return output_path
