# HEIC2PNG

This is a tool for converting format of HEIC image to PNG by using Python.

And, I used the pypi package template to generate this repo, you can check it in the [references](#References).

## Installation

```bash
pip install heic2png
```

## Usage

```python
from heic2png import HEIC2PNG

if __name__ == '__main__':
    heic_img = HEIC2PNG('test.heic')
    heic_img.save() # it'll show as `test.png`

```

## References

- [Example PyPi Package](https://github.com/tomchen/example_pypi_package)
- [Pillow HEIF](https://github.com/bigcat88/pillow_heif)
