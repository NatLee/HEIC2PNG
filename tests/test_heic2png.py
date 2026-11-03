"""Tests for the HEIC2PNG converter class."""
import io
import sys

import pytest
from PIL import Image

from heic2png import HEIC2PNG
from heic2png.heic2png import JPEG_MODES

from .images import noise, transparent_noise


@pytest.fixture
def rgb_png(tmp_path):
    """A 64x64 PNG with random colors."""
    path = tmp_path / "noise.png"
    noise("RGB").save(path)
    return path


# --- input -------------------------------------------------------------------

@pytest.mark.parametrize("quality", [0, 101, -5])
def test_rejects_quality_outside_1_to_100(rgb_png, quality):
    with pytest.raises(ValueError, match="between 1 and 100"):
        HEIC2PNG(str(rgb_png), quality=quality)


@pytest.mark.parametrize("quality", [None, 1, 100])
def test_accepts_quality_none_and_the_range_ends(rgb_png, quality):
    assert HEIC2PNG(str(rgb_png), quality=quality).quality == quality


def test_missing_input_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="Input file not found"):
        HEIC2PNG(str(tmp_path / "missing.heic"))


def test_unsupported_input_file_type(tmp_path):
    src = tmp_path / "picture.gif"
    noise("RGB").save(src)
    with pytest.raises(ValueError, match=r"Unsupported input file type: .*picture\.gif \(supported: "):
        HEIC2PNG(str(src))


def test_damaged_input_file(tmp_path):
    src = tmp_path / "broken.heic"
    src.write_bytes(b"this is not an image")
    with pytest.raises(IOError, match=r"Failed to open image: .*broken\.heic is damaged or not a supported image"):
        HEIC2PNG(str(src))


def test_other_open_errors_are_reported_as_io_errors(tmp_path):
    folder = tmp_path / "folder.heic"
    folder.mkdir()
    with pytest.raises(IOError, match="Failed to open image: "):
        HEIC2PNG(str(folder))


def test_damaged_input_stream():
    with pytest.raises(IOError, match="Failed to open image: the input stream is damaged"):
        HEIC2PNG(io.BytesIO(b"this is not an image"))


def test_accepts_path_objects_and_file_objects(rgb_png, tmp_path):
    from_path = HEIC2PNG(rgb_png).save(tmp_path / "a.png")
    with open(rgb_png, "rb") as f:
        from_file = HEIC2PNG(f).save(tmp_path / "b.png")
    assert from_path.read_bytes() == from_file.read_bytes()


def test_reads_stdin_and_writes_stdout(sample_heic, tmp_path, monkeypatch):
    out = tmp_path / "out.png"
    with open(sample_heic, "rb") as stdin, open(out, "wb") as stdout, monkeypatch.context() as m:
        m.setattr(sys, "stdin", stdin)
        m.setattr(sys, "stdout", stdout)
        HEIC2PNG("").save()

    with Image.open(out) as img:
        assert img.format == "PNG"
        assert img.size == (4032, 3024)


def test_uses_the_binary_layer_of_text_stdin_and_stdout(rgb_png, monkeypatch, capsysbinary):
    # The real sys.stdin/sys.stdout are text streams; the image data must go through .buffer.
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(rgb_png.read_bytes())))

    result = HEIC2PNG("").save()

    assert result is sys.stdout.buffer
    assert capsysbinary.readouterr().out.startswith(b"\x89PNG\r\n\x1a\n")


def test_file_object_without_output_path_writes_stdout(rgb_png, capsysbinary):
    with open(rgb_png, "rb") as f:
        HEIC2PNG(f).save()
    assert capsysbinary.readouterr().out.startswith(b"\x89PNG")


# --- output ------------------------------------------------------------------

def test_save_without_path_writes_next_to_the_input_with_the_new_extension(tmp_path):
    src = tmp_path / "photo.heic"
    noise("RGB").save(src)

    assert HEIC2PNG(str(src)).save() == tmp_path / "photo.png"
    assert HEIC2PNG(str(src)).save(extension=".jpg") == tmp_path / "photo.jpg"


@pytest.mark.parametrize("extension, suffix, image_format", [
    ("png", ".png", "PNG"),
    ("jpg", ".jpg", "JPEG"),
    (".PNG", ".PNG", "PNG"),
    (".JPEG", ".JPEG", "JPEG"),
])
def test_extension_dot_is_optional_and_case_is_kept(tmp_path, extension, suffix, image_format):
    src = tmp_path / "photo.heic"
    noise("RGB").save(src)

    out = HEIC2PNG(str(src)).save(extension=extension)

    assert out.name == "photo" + suffix
    with Image.open(out) as img:
        assert img.format == image_format


@pytest.mark.parametrize("extension", [".gif", ".heic", "webp"])
def test_unsupported_output_format(rgb_png, tmp_path, extension):
    with pytest.raises(ValueError, match="Unsupported output format"):
        HEIC2PNG(str(rgb_png)).save(tmp_path / "out", extension=extension)
    assert list(tmp_path.iterdir()) == [rgb_png]


def test_unsupported_output_format_lists_the_formats(rgb_png, tmp_path):
    with pytest.raises(ValueError, match=r"\(use \.png, \.jpg or \.jpeg\)$"):
        HEIC2PNG(str(rgb_png)).save(tmp_path / "out", extension=".gif")


def test_jpeg_modes_are_modes_pillow_writes_as_jpeg():
    # These modes go to Pillow unchanged, so Pillow must be able to write each one as JPEG
    for mode in JPEG_MODES:
        Image.new(mode, (4, 4)).save(io.BytesIO(), "JPEG")


# Every image mode Pillow can turn into RGB (only "La" cannot be converted at all)
ALL_MODES = ["1", "L", "LA", "P", "PA", "I", "I;16", "I;16B", "I;16L", "F",
             "RGB", "RGBA", "RGBa", "RGBX", "CMYK", "YCbCr", "LAB", "HSV"]


@pytest.mark.parametrize("mode", ALL_MODES)
def test_png_output_keeps_modes_png_can_store_and_turns_the_rest_into_rgb(rgb_png, tmp_path, mode):
    # Which modes PNG can store depends on the Pillow version (Pillow 13 dropped mode I), so the
    # expected bytes come from Pillow itself: its own PNG of the image, or of the RGB version.
    converter = HEIC2PNG(str(rgb_png))  # quality None: no color reduction
    converter.image = Image.new(mode, (4, 4))

    out = converter.save(tmp_path / "out.png")

    expected = io.BytesIO()
    try:
        converter.image.save(expected, "PNG", optimize=True)
    except OSError:  # PNG cannot store this mode
        expected = io.BytesIO()
        converter.image.convert("RGB").save(expected, "PNG", optimize=True)
    assert out.read_bytes() == expected.getvalue()


def test_existing_output_needs_overwrite(rgb_png, tmp_path):
    out = tmp_path / "out.png"
    out.write_bytes(b"keep me")

    with pytest.raises(FileExistsError, match="Output file already exists"):
        HEIC2PNG(str(rgb_png)).save(out)
    assert out.read_bytes() == b"keep me"

    HEIC2PNG(str(rgb_png), overwrite=True).save(out)
    assert out.read_bytes().startswith(b"\x89PNG")


def test_write_errors_are_reported_as_io_errors(rgb_png, tmp_path):
    with pytest.raises(IOError, match="Failed to save image"):
        HEIC2PNG(str(rgb_png)).save(tmp_path / "no-such-dir" / "out.png")


def test_jpeg_quality_defaults_to_95(rgb_png, tmp_path):
    out = HEIC2PNG(str(rgb_png)).save(tmp_path / "out.jpg", extension=".jpg")

    expected = io.BytesIO()
    with Image.open(rgb_png) as original:
        original.save(expected, "JPEG", quality=95, optimize=True)
    assert out.read_bytes() == expected.getvalue()


def test_jpeg_quality_is_passed_through(rgb_png, tmp_path):
    high = HEIC2PNG(str(rgb_png)).save(tmp_path / "high.jpg", extension=".jpg")
    low = HEIC2PNG(str(rgb_png), quality=30).save(tmp_path / "low.jpg", extension=".jpg")
    assert low.stat().st_size < high.stat().st_size


# --- quality and colors ------------------------------------------------------

def test_lower_quality_gives_a_smaller_png(tmp_path):
    src = tmp_path / "noise.heic"
    noise("RGB", (200, 200)).save(src)

    full = HEIC2PNG(str(src), quality=None).save(tmp_path / "full.png")
    reduced = HEIC2PNG(str(src), quality=10).save(tmp_path / "reduced.png")

    assert reduced.stat().st_size < full.stat().st_size


@pytest.mark.parametrize("quality", [None, 100])
def test_quality_none_and_100_keep_every_pixel(rgb_png, tmp_path, quality):
    out = HEIC2PNG(str(rgb_png), quality=quality).save(tmp_path / "out.png")

    with Image.open(out) as result, Image.open(rgb_png) as original:
        assert result.mode == "RGB"
        assert result.tobytes() == original.tobytes()


# max_colors is int(quality x 2.56), as the README says
@pytest.mark.parametrize("quality, max_colors", [(1, 2), (50, 128), (80, 204), (99, 253)])
def test_quality_below_100_limits_the_palette(rgb_png, tmp_path, quality, max_colors):
    out = HEIC2PNG(str(rgb_png), quality=quality).save(tmp_path / "out.png")

    with Image.open(out) as img:
        assert img.mode == "P"
        assert 2 <= len(img.getcolors()) <= max_colors


def test_palette_input_is_reduced_further_only_when_needed(tmp_path):
    src = tmp_path / "palette.png"
    noise("RGB").quantize(64).save(src)

    reduced = HEIC2PNG(str(src), quality=10).save(tmp_path / "reduced.png")  # at most 25 colors
    kept = HEIC2PNG(str(src), quality=50).save(tmp_path / "kept.png")  # 128 allowed, 64 used

    with Image.open(reduced) as img:
        assert len(img.getcolors()) <= 25
    with Image.open(kept) as img, Image.open(src) as original:
        assert img.convert("RGB").tobytes() == original.convert("RGB").tobytes()


def test_grayscale_is_not_turned_into_a_palette(tmp_path):
    src = tmp_path / "gray.png"
    noise("L").save(src)

    out = HEIC2PNG(str(src), quality=50).save(tmp_path / "out.png")

    with Image.open(out) as img:
        assert img.mode == "L"


# --- transparency ------------------------------------------------------------

def test_reduced_png_keeps_transparency(tmp_path):
    src = tmp_path / "transparent.png"
    transparent_noise().save(src)

    full = HEIC2PNG(str(src), quality=None).save(tmp_path / "full.png")
    reduced = HEIC2PNG(str(src), quality=30).save(tmp_path / "reduced.png")

    with Image.open(full) as img:
        assert img.mode == "RGBA"
    with Image.open(reduced) as img:
        assert img.mode == "P"
        assert img.info.get("transparency") is not None
        assert 2 <= len(img.getpalette()) // 3 <= 256
    # at least 10% smaller than the input
    assert reduced.stat().st_size <= 0.9 * src.stat().st_size


def _rows_with_alpha(*alphas):
    """A gray 100x100 image whose alpha changes in horizontal bands."""
    img = Image.new("RGBA", (100, 100), (128, 128, 128, 255))
    alpha = Image.new("L", img.size)
    band = 100 // len(alphas) + 1
    for i, value in enumerate(alphas):
        alpha.paste(value, (0, i * band, 100, min(100, (i + 1) * band)))
    img.putalpha(alpha)
    return img


@pytest.mark.parametrize("image, quality, expected_alpha", [
    pytest.param(Image.new("RGBA", (100, 100), (0, 0, 0, 0)), 50, {50: 0}, id="fully-transparent"),
    pytest.param(noise("RGB", (100, 100)).convert("RGBA"), 50, {50: 255}, id="fully-opaque"),
    pytest.param(_rows_with_alpha(0, 128, 255), 30, {10: 0, 50: 128, 90: 255}, id="mixed"),
])
def test_reduced_png_keeps_alpha_values(tmp_path, image, quality, expected_alpha):
    src = tmp_path / "in.png"
    image.save(src)

    out = HEIC2PNG(str(src), quality=quality).save(tmp_path / "out.png")

    with Image.open(out) as img:
        assert img.mode in ("RGBA", "P")
        rgba = img.convert("RGBA")
    # Exact: a few alpha levels fit easily into the palette (checked with Pillow 10.4 and 13.0)
    for y, alpha in expected_alpha.items():
        assert rgba.getpixel((50, y))[3] == alpha


# --- which format save() writes ------------------------------------------------
# One rule, shared with the command: the extension argument (-f) picks the format; without it,
# the output file name's extension does; without either, PNG. A file name may have no extension
# or one of the same format; anything else is refused, so a file never claims another format.

@pytest.mark.parametrize("name, extension, image_format", [
    ("out.png", None, "PNG"),
    ("out.jpg", None, "JPEG"),
    ("out.jpeg", None, "JPEG"),
    ("OUT.JPG", None, "JPEG"),
    ("out", None, "PNG"),
    ("out", ".jpg", "JPEG"),
    ("out.jpeg", "jpg", "JPEG"),
    ("out.jpg", ".jpeg", "JPEG"),
    ("out.png", ".png", "PNG"),
])
def test_output_format_follows_the_rule(rgb_png, tmp_path, name, extension, image_format):
    out = HEIC2PNG(str(rgb_png)).save(tmp_path / name, extension=extension)
    assert out == tmp_path / name
    with Image.open(out) as img:
        assert img.format == image_format


@pytest.mark.parametrize("name, extension, message", [
    ("out.heic", None, r"Cannot write \.heic files"),
    ("out.HEIF", None, r"Cannot write \.HEIF files"),
    ("out.webp", None, r"Cannot write \.webp files"),
    ("out.txt", ".png", r"Cannot write \.txt files"),
    ("out.jpg", ".png", r"out\.jpg is a JPEG file name, but the output format asked for is PNG"),
    ("out.png", "jpeg", r"out\.png is a PNG file name, but the output format asked for is JPEG"),
])
def test_output_names_that_do_not_match_are_refused(rgb_png, tmp_path, name, extension, message):
    with pytest.raises(ValueError, match=message):
        HEIC2PNG(str(rgb_png)).save(tmp_path / name, extension=extension)
    assert list(tmp_path.iterdir()) == [rgb_png]  # nothing written


def test_refused_output_names_list_what_can_be_written(rgb_png, tmp_path):
    with pytest.raises(ValueError, match=r"heic2png writes PNG or JPEG \(\.png, \.jpg or \.jpeg\)"):
        HEIC2PNG(str(rgb_png)).save(tmp_path / "out.heic")
