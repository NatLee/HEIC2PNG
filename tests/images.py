"""Small synthetic test images, built with Pillow only."""
import random
from typing import Tuple

from PIL import Image

Size = Tuple[int, int]


def noise(mode: str, size: Size = (64, 64), seed: int = 0) -> Image.Image:
    """Random pixels, so nearly every pixel has its own color and color reduction is visible."""
    n = size[0] * size[1] * Image.getmodebands(mode)
    data = random.Random(seed).getrandbits(8 * n).to_bytes(n, "little")
    return Image.frombytes(mode, size, data)


def transparent_noise(size: int = 200) -> Image.Image:
    """Random colors that are semi-transparent, with an opaque centre and a fully transparent corner."""
    img = noise("RGB", (size, size)).convert("RGBA")
    alpha = Image.new("L", img.size, 200)
    alpha.paste(255, (size // 4, size // 4, size * 3 // 4, size * 3 // 4))
    alpha.paste(0, (0, 0, size // 4, size // 4))
    img.putalpha(alpha)
    return img
