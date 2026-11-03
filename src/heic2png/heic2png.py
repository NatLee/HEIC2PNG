"""Convert HEIC images (and PNG/JPEG) to PNG or JPEG with Pillow."""
import functools
import io
import sys
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, Sequence, Union

from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()

ImageSource = Union[str, Path, BinaryIO]
ImageDestination = Union[Path, BinaryIO]

JPEG_EXTENSIONS = ('.jpg', '.jpeg')
#: Output extension -> Pillow format name. This table decides what save() can write; the input
#: types, the error messages and the command's -f choices all come from it. Pillow knows JPEG
#: only as "JPEG" ("JPG" raises KeyError).
OUTPUT_FORMATS = {'.png': 'PNG', **dict.fromkeys(JPEG_EXTENSIONS, 'JPEG')}
OUTPUT_EXTENSIONS = tuple(OUTPUT_FORMATS)
# Modes saved as JPEG as they are; anything else is flattened onto white, because JPEG has no
# transparency. (PNG output asks Pillow instead, see _pillow_writes.)
JPEG_MODES = ('L', 'RGB', 'CMYK')
DEFAULT_JPEG_QUALITY = 95
#: What save() writes when neither its extension argument nor the output file name says
DEFAULT_EXTENSION = '.png'
#: Quality goes from MIN_QUALITY to MAX_QUALITY. Below MAX_QUALITY, PNG output becomes a palette of
#: quality / MAX_QUALITY of MAX_PALETTE_COLORS colors (quality x 2.56); PNG palettes hold at most 256.
MIN_QUALITY, MAX_QUALITY = 1, 100
MAX_PALETTE_COLORS = 256


@functools.lru_cache(maxsize=None)
def _pillow_writes(image_format: str, mode: str) -> bool:
    """Whether Pillow can save images of this mode in this format as they are.

    Asks Pillow, with a 1x1 image, instead of keeping a copy of its tables: they change between
    versions (Pillow 10.4 writes mode I as PNG, Pillow 13 does not).
    """
    try:
        Image.new(mode, (1, 1)).save(io.BytesIO(), image_format)
    except (OSError, ValueError):
        return False
    return True


def _join_or(items: Sequence[str]) -> str:
    """'.png, .jpg or .jpeg' from ('.png', '.jpg', '.jpeg'), for messages."""
    return ', '.join(items[:-1]) + ' or ' + items[-1]


def _normalize_extension(extension: str) -> str:
    """Add the leading dot if missing and check that the output format is supported."""
    if not extension.startswith('.'):
        extension = f'.{extension}'
    if extension.lower() not in OUTPUT_FORMATS:
        raise ValueError(f"Unsupported output format: {extension} (use {_join_or(OUTPUT_EXTENSIONS)})")
    return extension


def output_extension(
    extension: Optional[str] = None,
    output_path: Union[str, Path, None] = None,
) -> str:
    """
    Decide what format to write, and return its extension. This is heic2png's one rule:

    1. ``extension`` (the command's -f) picks the format when it is given.
    2. Otherwise the extension of ``output_path`` (the command's -o) does.
    3. Otherwise the output is PNG.

    ``output_path`` may have no extension, or one of the chosen format. Any other extension
    (.heic, .webp, .txt, or .jpg while PNG was asked for) raises ValueError, so heic2png never
    writes a file whose name claims another format than its content, and never writes HEIC.
    """
    requested = _normalize_extension(extension) if extension else None
    suffix = Path(output_path).suffix if output_path is not None else ''
    if suffix and suffix.lower() not in OUTPUT_FORMATS:
        formats = _join_or(tuple(dict.fromkeys(OUTPUT_FORMATS.values())))
        raise ValueError(f"Cannot write {suffix} files: heic2png writes {formats} ({_join_or(OUTPUT_EXTENSIONS)})")
    if requested and suffix and OUTPUT_FORMATS[requested.lower()] != OUTPUT_FORMATS[suffix.lower()]:
        raise ValueError(
            f"{Path(str(output_path)).name} is a {OUTPUT_FORMATS[suffix.lower()]} file name, "
            f"but the output format asked for is {OUTPUT_FORMATS[requested.lower()]}"
        )
    return requested or suffix or DEFAULT_EXTENSION


class HEIC2PNG:
    """
    Convert a HEIC image to PNG (or JPEG).

    The input can be a file path, a binary file-like object or stdin; the output
    a file path or stdout.

    Example:
        >>> HEIC2PNG('photo.heic', quality=100).save()  # writes photo.png
    """

    # Input types: HEIC, and every format heic2png can write
    SUPPORTED_EXTENSIONS = {'.heic', *OUTPUT_EXTENSIONS}

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
        extension: Optional[str] = None,
    ) -> ImageDestination:
        """
        Convert the image and save it.

        Args:
            output_image_file_path: Where to save the converted image. If None and the
                input was a file path, saves next to the input with the new extension
                (photo.heic -> photo.png). If None and the input was stdin or a
                file-like object, writes to stdout.
            extension: Output format: '.png', '.jpg' or '.jpeg' (the leading dot is
                optional). If None, the extension of output_image_file_path decides,
                and PNG when that has none. See output_extension() for the rule.

        Returns:
            The path that was written, or the binary stdout stream.

        Raises:
            ValueError: If the output format is not supported, or the output file name
                has another extension than the format (for example .heic or .webp).
            FileExistsError: If the output file exists and overwrite is False.
            IOError: If converting or writing the image fails.
        """
        extension = output_extension(extension, output_image_file_path)
        image_format = OUTPUT_FORMATS[extension.lower()]
        output_path = self._output_path(output_image_file_path, extension)
        if output_path is not None and output_path.exists() and not self.overwrite:
            raise FileExistsError(f"Output file already exists: {output_path}")
        destination = output_path if output_path is not None else self._binary_stream(sys.stdout)

        try:
            image = self._prepare_image(image_format)
            image.save(destination, **self._get_save_parameters(image_format))
        except Exception as e:
            raise IOError(f"Failed to save image: {e}") from e
        return destination

    @property
    def _palette_size(self) -> Optional[int]:
        """How many colors PNG output is reduced to, or None to keep every color (quality None or 100)."""
        if self.quality is None or self.quality >= MAX_QUALITY:
            return None
        # MIN_QUALITY (1) gives 2 colors, the smallest useful palette
        return int(self.quality * (MAX_PALETTE_COLORS / MAX_QUALITY))

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

    def _prepare_image(self, image_format: str) -> Image.Image:
        """Return the image in a mode the target format can store, with colors reduced if asked."""
        image = self.image
        if image_format == 'JPEG':
            return self._flatten_for_jpeg(image)
        if not _pillow_writes(image_format, image.mode):
            image = image.convert('RGB')  # e.g. CMYK from a JPEG
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
        # getcolors() returns None only above 256 colors, which a palette image cannot have.
        if image.mode == 'P' and len(image.getcolors() or ()) > max_colors:
            return image.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
        return image

    def _get_save_parameters(self, image_format: str) -> Dict[str, Any]:
        """Keyword arguments for Image.save() for the given Pillow format name."""
        if image_format == 'JPEG':
            quality = self.quality if self.quality is not None else DEFAULT_JPEG_QUALITY
            return {'format': image_format, 'quality': quality, 'optimize': True}
        # With optimize=True Pillow always uses the strongest zlib compression,
        # so there is no compression level to pass.
        return {'format': image_format, 'optimize': True}

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
        Composite such images onto a white background; JPEG_MODES pass through.
        """
        if image.mode in JPEG_MODES:
            return image
        rgba = image.convert('RGBA')
        background = Image.new('RGB', rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel('A'))
        return background

    @staticmethod
    def _validate_quality(quality: Optional[int]) -> None:
        if quality is not None and not MIN_QUALITY <= quality <= MAX_QUALITY:
            raise ValueError(f"Quality must be between {MIN_QUALITY} and {MAX_QUALITY}, got {quality}")

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
