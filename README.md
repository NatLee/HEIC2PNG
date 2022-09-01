# HEIC2PNG

[![Test](https://github.com/NatLee/HEIC2PNG/actions/workflows/test.yml/badge.svg)](https://github.com/NatLee/HEIC2PNG/actions/workflows/test.yml)[![Release](https://github.com/NatLee/HEIC2PNG/actions/workflows/release.yml/badge.svg)](https://github.com/NatLee/HEIC2PNG/actions/workflows/release.yml)

This is a tool for converting format of HEIC image to PNG by using Python.

And it can be used with python simple CLI.

I used the pypi package template to generate this repo, you can check it in the [references](#References).

## Installation

```bash
pip install heic2png
```

## Usage

Common use with code below.

```python
from heic2png import HEIC2PNG

if __name__ == '__main__':
    heic_img = HEIC2PNG('test.heic')
    heic_img.save() # it'll show as `test.png`

```

And, you can try simple CLI with this.

```bash
python -m heic2png --input_path test.heic --output_path test.png
```

Or, you want to keep original name, just use this.

```bash
python -m heic2png --input_path test.heic
```

It'll generate `test.png` for you.

## References

- [Example PyPi Package](https://github.com/tomchen/example_pypi_package)
- [Pillow HEIF](https://github.com/bigcat88/pillow_heif)
