import os
import sys
from pathlib import Path
from typing import Union, Optional, BinaryIO

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

class HEIC2PNG:
    """
    A converter class for converting HEIC images to PNG format.
    
    Supports reading from file path or file-like objects and can output to
    file path or stdout.
    """
    
    SUPPORTED_EXTENSIONS = {'.heic', '.png', '.jpg', '.jpeg'}

    def __init__(
        self,
        image_file_path: Union[str, Path, BinaryIO] = "",
        quality: Optional[int] = None,
        overwrite: bool = False
    ) -> None:
        """
        Initialize the HEIC2PNG converter.

        Args:
            image_file_path: Path to the HEIC image file, or a file-like object.
                           If empty, reads from stdin.
            quality: Quality of the converted PNG image (1-100).
                    None means no optimization.
            overwrite: Whether to overwrite existing output files.

        Raises:
            ValueError: If quality is not in range 1-100 or file extension is not supported.
            FileNotFoundError: If the input file doesn't exist.
        """
        self._validate_quality(quality)
        self.quality = quality
        self.overwrite = overwrite
        
        # Handle input source
        if not image_file_path:
            self.image_file_path = self._get_binary_stdin()
        elif isinstance(image_file_path, (str, Path)):
            self.image_file_path = self._validate_input_path(Path(image_file_path))
        else:
            # Assume it's a file-like object
            self.image_file_path = image_file_path

        try:
            self.image: Image.Image = Image.open(self.image_file_path)
        except Exception as e:
            raise IOError(f"Failed to open image: {str(e)}") from e

    def save(
        self,
        output_image_file_path: Union[str, Path, None] = None,
        extension: str = '.png'
    ) -> Path:
        """
        Convert and save the input image to another format.

        Args:
            output_image_file_path: Path to save the converted image.
                                  If None, writes to stdout.
            extension: The target file extension (default: '.png')

        Returns:
            Path: The path where the converted image was saved.

        Raises:
            ValueError: If the output extension is not supported.
            IOError: If saving the image fails.
        """
        if not extension.startswith('.'):
            extension = f'.{extension}'
        
        if extension.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported output format: {extension}")

        # Handle output destination
        if output_image_file_path is None:
            output_path = self._get_binary_stdout()
        else:
            output_path = Path(output_image_file_path)
            if output_path.exists() and not self.overwrite:
                raise FileExistsError(f"Output file already exists: {output_path}")

        try:
            # Optimize image if quality is specified
            image_to_save = self.image
            if self.quality and self.quality < 100:
                image_to_save = self._optimize_image_with_pil(self.image, extension)
            
            # Prepare save parameters based on format and quality
            save_params = self._get_save_parameters(extension)
            
            # Save the image in the target format
            image_to_save.save(output_path, **save_params)

            return output_path

        except Exception as e:
            raise IOError(f"Failed to save image: {str(e)}") from e

    @staticmethod
    def _validate_quality(quality: Optional[int]) -> None:
        """Validate the quality parameter."""
        if quality is not None and not (1 <= quality <= 100):
            raise ValueError("Quality must be between 1 and 100")

    @staticmethod
    def _validate_input_path(path: Path) -> Path:
        """Validate the input file path."""
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        if path.suffix.lower() not in HEIC2PNG.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Input file must be a supported image format: {path}")
        return path

    @staticmethod
    def _get_binary_stdin() -> BinaryIO:
        """Get binary stdin handle."""
        return (os.fdopen(sys.stdin.fileno(), "rb")
                if "b" not in sys.stdin.mode else sys.stdin)

    @staticmethod
    def _get_binary_stdout() -> BinaryIO:
        """Get binary stdout handle."""
        return (os.fdopen(sys.stdout.fileno(), "wb")
                if "b" not in sys.stdout.mode else sys.stdout)

    def _get_save_parameters(self, extension: str) -> dict:
        """
        Get save parameters based on format and quality settings.
        
        Args:
            extension: File extension (e.g., '.png', '.jpg')
            
        Returns:
            dict: Parameters for PIL Image.save()
        """
        format_name = extension[1:].upper()
        params = {'format': format_name}
        
        if extension.lower() == '.png':
            # PNG optimization using PIL's built-in features
            if self.quality and self.quality < 100:
                # Convert quality to optimize level (0-9, where 9 is best compression)
                optimize_level = max(0, min(9, int((100 - self.quality) / 10)))
                params['optimize'] = True
                params['compress_level'] = optimize_level
            else:
                # Default PNG settings for best quality
                params['optimize'] = True
                params['compress_level'] = 6
                
        elif extension.lower() in ['.jpg', '.jpeg']:
            # JPEG quality setting
            if self.quality:
                params['quality'] = self.quality
            else:
                params['quality'] = 95  # Default high quality
            params['optimize'] = True
            
        return params

    def _optimize_image_with_pil(self, image: Image.Image, extension: str) -> Image.Image:
        """
        Optimize image using PIL's built-in features while preserving transparency.
        
        Args:
            image: PIL Image object
            extension: Target file extension
            
        Returns:
            Image.Image: Optimized image
        """
        if extension.lower() == '.png':
            # For PNG, we can reduce colors if quality is specified
            if self.quality and self.quality < 100:
                # Calculate target colors based on quality
                max_colors = max(2, int(self.quality * 2.56))  # Scale 1-100 to 2-256
                
                # Handle different image modes while preserving transparency
                if image.mode in ['RGBA', 'LA']:
                    # For images with transparency, use Fast Octree method which supports RGBA
                    # This preserves transparency while reducing colors
                    image = image.quantize(colors=max_colors, method=Image.Quantize.FASTOCTREE)
                    # Keep the quantized image in P mode with transparency
                    
                elif image.mode == 'RGB':
                    # For RGB images without transparency, convert to palette
                    image = image.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
                    
                elif image.mode == 'P':
                    # Already a palette image, just reduce colors further if needed
                    if len(image.getcolors()) > max_colors:
                        image = image.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
                
        return image