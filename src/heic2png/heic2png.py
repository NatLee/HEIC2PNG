"""Convert HEIC images (and PNG/JPEG) to PNG or JPEG with Pillow."""
import sys
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, Union

from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()

ImageSource = Union[str, Path, BinaryIO]
ImageDestination = Union[Path, BinaryIO]

JPEG_EXTENSIONS = ('.jpg', '.jpeg')
OUTPUT_EXTENSIONS = ('.png',) + JPEG_EXTENSIONS
# Modes Pillow can write as PNG; anything else (e.g. CMYK from a JPEG) is converted to RGB first.
PNG_MODES = ('1', 'L', 'LA', 'I', 'I;16', 'I;16B', 'P', 'RGB', 'RGBA')
DEFAULT_JPEG_QUALITY = 95


class HEIC2PNG:
    """
    Convert a HEIC image to PNG (or JPEG).

    The input can be a file path, a binary file-like object or stdin; the output
    a file path or stdout.

    Example:
        >>> HEIC2PNG('photo.heic', quality=100).save()  # writes photo.png
    """

    SUPPORTED_EXTENSIONS = {'.heic', '.png', '.jpg', '.jpeg'}

    def __init__(
        self,
        image_file_path: ImageSource = "",
        quality: Optional[int] = None,
        overwrite: bool = False,
    ) -> None:
        """
        Open the image to convert.

        Args:
            image_file_path: Path to the image file, or a binary file-like object.
                If empty, the image is read from stdin.
            quality: 1-100, or None to keep every color. For PNG output, anything
                below 100 reduces the image to a palette of at most 256 colors
                (quality x 2.56). For JPEG output it is the JPEG quality
                (None means 95).
            overwrite: Whether save() may replace an existing file.

        Raises:
            ValueError: If quality is not in 1-100 or the file extension is not supported.
            FileNotFoundError: If the input file does not exist.
            IOError: If the input is not an image Pillow can read.
        """
        self._validate_quality(quality)
        self.quality = quality
        self.overwrite = overwrite

        # input_path is only set for file paths; save() derives the default output name from it.
        self.input_path: Optional[Path] = None
        if not image_file_path:
            self.image_file_path: Union[Path, BinaryIO] = self._binary_stream(sys.stdin)
        elif isinstance(image_file_path, (str, Path)):
            self.input_path = self._validate_input_path(Path(image_file_path))
            self.image_file_path = self.input_path
        else:
            self.image_file_path = image_file_path

        try:
            self.image: Image.Image = Image.open(self.image_file_path)
        except UnidentifiedImageError as e:
            raise IOError(
                f"Failed to open image: {self._describe_input()} is damaged or not a supported image"
            ) from e
        except Exception as e:
            raise IOError(f"Failed to open image: {e}") from e

    def save(
        self,
        output_image_file_path: Union[str, Path, None] = None,
        extension: str = '.png',
    ) -> ImageDestination:
        """
        Convert the image and save it.

        Args:
            output_image_file_path: Where to save the converted image. If None and the
                input was a file path, saves next to the input with the new extension
                (photo.heic -> photo.png). If None and the input was stdin or a
                file-like object, writes to stdout.
            extension: Output format: '.png' (default), '.jpg' or '.jpeg'. The leading
                dot is optional.

        Returns:
            The path that was written, or the binary stdout stream.

        Raises:
            ValueError: If the output format is not supported.
            FileExistsError: If the output file exists and overwrite is False.
            IOError: If converting or writing the image fails.
        """
        extension = self._normalize_extension(extension)
        output_path = self._output_path(output_image_file_path, extension)
        if output_path is not None and output_path.exists() and not self.overwrite:
            raise FileExistsError(f"Output file already exists: {output_path}")
        destination = output_path if output_path is not None else self._binary_stream(sys.stdout)

        try:
            image = self._prepare_image(extension)
            image.save(destination, **self._get_save_parameters(extension))
        except Exception as e:
            raise IOError(f"Failed to save image: {e}") from e
        return destination

    @property
    def _palette_size(self) -> Optional[int]:
        """How many colors PNG output is reduced to, or None to keep every color (quality None or 100)."""
        if self.quality is None or self.quality >= 100:
            return None
        return max(2, int(self.quality * 2.56))

    def _output_path(
        self,
        output_image_file_path: Union[str, Path, None],
        extension: str,
    ) -> Optional[Path]:
        """The file save() writes to, or None when it writes to stdout."""
        if output_image_file_path is not None:
            return Path(output_image_file_path)
        if self.input_path is not None:
            return self.input_path.with_suffix(extension)
        return None

    def _prepare_image(self, extension: str) -> Image.Image:
        """Return the image in a mode the target format can store, with colors reduced if asked."""
        image = self.image
        if extension.lower() in JPEG_EXTENSIONS:
            return self._flatten_for_jpeg(image)
        if image.mode not in PNG_MODES:
            image = image.convert('RGB')
        if self._palette_size is not None:
            image = self._reduce_colors(image, self._palette_size)
        return image

    @staticmethod
    def _reduce_colors(image: Image.Image, max_colors: int) -> Image.Image:
        """Quantize to at most max_colors colors, keeping transparency."""
        if image.mode == 'LA':
            image = image.convert('RGBA')  # Pillow cannot quantize LA directly
        if image.mode == 'RGBA':
            # Fast octree is the method Pillow supports for images with an alpha channel.
            return image.quantize(colors=max_colors, method=Image.Quantize.FASTOCTREE)
        if image.mode == 'RGB':
            return image.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
        if image.mode == 'P' and len(image.getcolors()) > max_colors:
            return image.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
        return image

    def _get_save_parameters(self, extension: str) -> Dict[str, Any]:
        """Keyword arguments for Image.save() for the given output extension."""
        if extension.lower() in JPEG_EXTENSIONS:
            # Pillow knows the format only as "JPEG"; "JPG" raises KeyError.
            quality = self.quality if self.quality is not None else DEFAULT_JPEG_QUALITY
            return {'format': 'JPEG', 'quality': quality, 'optimize': True}
        # With optimize=True Pillow always uses the strongest zlib compression,
        # so there is no compression level to pass.
        return {'format': 'PNG', 'optimize': True}

    def _describe_input(self) -> str:
        """A readable name for the input, for error messages."""
        if self.input_path is not None:
            return str(self.input_path)
        name = getattr(self.image_file_path, 'name', None)  # "<stdin>" for stdin, a path for open files
        return name if isinstance(name, str) else 'the input stream'

    @staticmethod
    def _flatten_for_jpeg(image: Image.Image) -> Image.Image:
        """
        JPEG has no alpha channel, so Pillow refuses to save RGBA/LA/P images as JPEG.
        Composite such images onto a white background; RGB/L/CMYK pass through.
        """
        if image.mode in ('RGB', 'L', 'CMYK'):
            return image
        rgba = image.convert('RGBA')
        background = Image.new('RGB', rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel('A'))
        return background

    @staticmethod
    def _normalize_extension(extension: str) -> str:
        """Add the leading dot if missing and check that the output format is supported."""
        if not extension.startswith('.'):
            extension = f'.{extension}'
        if extension.lower() not in OUTPUT_EXTENSIONS:
            raise ValueError(f"Unsupported output format: {extension} (use .png, .jpg or .jpeg)")
        return extension

    @staticmethod
    def _validate_quality(quality: Optional[int]) -> None:
        if quality is not None and not 1 <= quality <= 100:
            raise ValueError(f"Quality must be between 1 and 100, got {quality}")

    @staticmethod
    def _validate_input_path(path: Path) -> Path:
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        if path.suffix.lower() not in HEIC2PNG.SUPPORTED_EXTENSIONS:
            supported = ', '.join(sorted(HEIC2PNG.SUPPORTED_EXTENSIONS))
            raise ValueError(f"Unsupported input file type: {path} (supported: {supported})")
        return path

    @staticmethod
    def _binary_stream(stream: Any) -> BinaryIO:
        """The binary layer of a text stream such as sys.stdin; binary streams pass through."""
        return getattr(stream, 'buffer', stream)
