from pathlib import Path

from PIL import Image

from pillow_heif import register_heif_opener
register_heif_opener()

class HEIC2PNG:
    def __init__(self, image_file_path:str):
        self.image_file_path = Path(image_file_path)
        if self.image_file_path.suffix.lower() != '.heic':
            raise ValueError
        
        self.image = Image.open(self.image_file_path)

    def save(self, output_image_file_path=None, extension='.png') -> Path:
        if output_image_file_path:
            output_path = Path(output_image_file_path)
            if output_path.suffix.lower() != extension:
                raise ValueError
        else:
            output_path = self.image_file_path.with_name(f"{self.image_file_path.stem}{extension}")
        if output_path.exists():
            raise FileExistsError
        self.image.save(output_path)
        return output_path
