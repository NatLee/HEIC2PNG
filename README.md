# HEIC2PNG

[![Test](https://github.com/NatLee/HEIC2PNG/actions/workflows/test.yml/badge.svg)](https://github.com/NatLee/HEIC2PNG/actions/workflows/test.yml)
[![Release](https://github.com/NatLee/HEIC2PNG/actions/workflows/release.yml/badge.svg)](https://github.com/NatLee/HEIC2PNG/actions/workflows/release.yml)

This is a tool for converting the format of HEIC images to PNG using Python. It now supports quality adjustment and has an option to overwrite existing files, enhancing the flexibility and usability of the tool.

## Installation

```bash
pip install heic2png
```

Visit [HEIC2PNG on PyPI](https://pypi.org/project/HEIC2PNG/) for more details.

## Usage

### As a Library

You can use HEIC2PNG in your Python code as shown below:

```python
from heic2png import HEIC2PNG

if __name__ == '__main__':
    heic_img = HEIC2PNG('test.heic', quality=90)  # Specify the quality of the converted image
    heic_img.save()  # The converted image will be saved as `test.png`
```

### Command Line Interface

HEIC2PNG also provides a CLI for easy conversion of HEIC images to PNG. Here are some examples:

Convert a HEIC image to PNG with a specified output path:

```bash
heic2png -i test.heic -o test.png -q 90  # -q is used to specify the quality
```

If you want to keep the original name, use the command below. It will generate `test.png` for you:

```bash
heic2png -i test.heic -q 90
```

To overwrite an existing PNG file, use the `-w`` flag:

```bash
heic2png -i test.heic -o test.png -q 90 -w
```
## References

- [Example PyPi Package](https://github.com/tomchen/example_pypi_package)
- [Pillow HEIF](https://github.com/bigcat88/pillow_heif)
- [pngquant](https://pngquant.org/)