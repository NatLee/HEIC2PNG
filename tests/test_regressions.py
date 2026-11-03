"""Regression tests for behaviour that broke between 1.1.x and 1.2.0."""
import subprocess
import sys

import pytest
from PIL import Image

from heic2png import HEIC2PNG
from heic2png.cli import setup_parser


@pytest.mark.parametrize("fmt", ["jpg", "jpeg"])
@pytest.mark.parametrize("mode", ["RGB", "RGBA"])
def test_jpeg_output(tmp_path, fmt, mode):
    # 1.2.0 passed "JPG" to Pillow (unknown format) and could not save transparent images as JPEG.
    src = tmp_path / "in.png"
    color = (255, 0, 0) if mode == "RGB" else (255, 0, 0, 0)  # RGBA: fully transparent red
    Image.new(mode, (8, 8), color).save(src)
    out = tmp_path / f"out.{fmt}"

    HEIC2PNG(str(src), quality=None).save(out, extension=f".{fmt}")

    with Image.open(out) as result:
        assert result.format == "JPEG"
        assert result.mode == "RGB"
        if mode == "RGBA":  # transparent pixels become white, not black
            assert result.getpixel((4, 4)) == pytest.approx((255, 255, 255), abs=3)


def test_save_without_path_writes_next_to_input(tmp_path):
    # README and 1.1.x: HEIC2PNG('test.heic').save() creates test.png; 1.2.0 wrote PNG bytes to stdout.
    src = tmp_path / "photo.jpg"
    Image.new("RGB", (8, 8), (0, 128, 255)).save(src)

    result = HEIC2PNG(str(src)).save()

    assert result == tmp_path / "photo.png"
    with Image.open(result) as img:
        assert img.format == "PNG"


def test_save_without_path_respects_overwrite(tmp_path):
    src = tmp_path / "photo.jpg"
    Image.new("RGB", (8, 8)).save(src)
    (tmp_path / "photo.png").write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        HEIC2PNG(str(src)).save()
    assert HEIC2PNG(str(src), overwrite=True).save() == tmp_path / "photo.png"


def test_import_does_not_configure_logging():
    # 1.2.0 called logging.basicConfig() at import time, adding a handler to the caller's root logger.
    code = "import logging, heic2png; print(len(logging.getLogger().handlers))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "0"


def test_cli_still_prints_progress(tmp_path):
    src = tmp_path / "photo.jpg"
    Image.new("RGB", (8, 8)).save(src)
    out = subprocess.run([sys.executable, "-m", "heic2png.cli", "-i", str(src), "-q", "100"],
                         capture_output=True, text=True)
    assert out.returncode == 0
    assert "Successfully saved converted image" in out.stderr


def test_stdin_with_output_path_writes_the_file(tmp_path):
    # README: `cat image.heic | heic2png -o output.png`; 1.2.0 ignored -o and wrote to stdout.
    src = tmp_path / "photo.png"
    Image.new("RGB", (8, 8), (10, 20, 30)).save(src)
    out = tmp_path / "out.png"
    with open(src, "rb") as stdin:
        result = subprocess.run([sys.executable, "-m", "heic2png.cli", "-o", str(out), "-q", "100"],
                                stdin=stdin, capture_output=True)
    assert result.returncode == 0
    assert result.stdout == b""
    with Image.open(out) as img:
        assert img.format == "PNG"


def test_short_q_sets_quality():
    # 1.1.x and the README use `-q 90` for quality; 1.2.0 had turned -q into --quiet.
    args = setup_parser().parse_args(["-i", "photo.heic", "-q", "90"])
    assert args.quality == 90
    assert args.quiet is False


def test_quiet_is_still_available_as_long_option():
    args = setup_parser().parse_args(["-i", "photo.heic", "--quiet"])
    assert args.quiet is True
    assert args.quality == 80  # default unchanged (user decision, 2026-11-03)
