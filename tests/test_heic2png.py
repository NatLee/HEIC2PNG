"""Tests for the HEIC2PNG converter class."""
import sys

import pytest
from PIL import Image

from heic2png import HEIC2PNG

from .images import noise, transparent_noise


def test_lower_quality_gives_a_smaller_png(tmp_path):
    src = tmp_path / "noise.heic"
    noise("RGB", (200, 200)).save(src)

    full = HEIC2PNG(str(src), quality=None).save(tmp_path / "full.png")
    reduced = HEIC2PNG(str(src), quality=10).save(tmp_path / "reduced.png")

    assert reduced.stat().st_size < full.stat().st_size


def test_reads_stdin_and_writes_stdout(sample_heic, tmp_path, monkeypatch):
    out = tmp_path / "out.png"
    with open(sample_heic, "rb") as stdin, open(out, "wb") as stdout, monkeypatch.context() as m:
        m.setattr(sys, "stdin", stdin)
        m.setattr(sys, "stdout", stdout)
        HEIC2PNG("").save()

    with Image.open(out) as img:
        assert img.format == "PNG"
        assert img.size == (4032, 3024)


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
    for y, alpha in expected_alpha.items():
        assert rgba.getpixel((50, y))[3] == pytest.approx(alpha, abs=8)
