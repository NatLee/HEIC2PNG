import subprocess
from pathlib import Path
from typing import Optional
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

class HEIC2PNG:
    def __init__(self, image_file_path: str, quality: Optional[int] = None, overwrite: bool = False):
        """
        Initializes the HEIC2PNG converter.

        :param image_file_path: Path to the HEIC image file.
        :param quality: Quality of the converted PNG image (1-100).
        :param overwrite: Whether to overwrite the file if it already exists.
        """
        self.image_file_path: Path = Path(image_file_path)
        self.quality: Optional[int] = quality
        self.overwrite: bool = overwrite

        if not self.image_file_path.is_file():
            raise FileNotFoundError(f"The file {image_file_path} does not exist.")

        if self.image_file_path.suffix.lower() != '.heic':
            raise ValueError("The provided file is not a HEIC image.")

        self.image: Image.Image = Image.open(self.image_file_path)

    def save(self, output_image_file_path: Optional[str] = None, extension: str = '.png') -> Path:
        """
        Converts and saves the HEIC image to PNG format.

        :param output_image_file_path: Path to save the converted PNG image.
        :param extension: The file extension of the converted image.
        :return: Path where the converted image is saved.
        """
        if output_image_file_path:
            output_path: Path = Path(output_image_file_path)
            if output_path.suffix.lower() != extension:
                raise ValueError("The output file extension does not match the specified extension.")
        else:
            output_path: Path = self.image_file_path.with_suffix(extension)

        if not self.overwrite and output_path.exists():
            raise FileExistsError(f"The file {output_path} already exists.")

        self.image.save(output_path)

        # Optimize PNG with pngquant if quality is specified
        if self.quality and self.quality != 100:
            quality_str: str = f'{self.quality}-{self.quality}'
            subprocess.run(['pngquant', '--quality', quality_str, '-f', '-o', str(output_path), str(output_path)])

        return output_path
