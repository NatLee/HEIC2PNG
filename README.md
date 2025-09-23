# HEIC2PNG

[![Test](https://github.com/NatLee/HEIC2PNG/actions/workflows/test.yml/badge.svg)](https://github.com/NatLee/HEIC2PNG/actions/workflows/test.yml)
[![Release](https://github.com/NatLee/HEIC2PNG/actions/workflows/release.yml/badge.svg)](https://github.com/NatLee/HEIC2PNG/actions/workflows/release.yml)

This is a tool for converting the format of HEIC images to PNG using Python. It now supports quality adjustment and has an option to overwrite existing files, enhancing the flexibility and usability of the tool.

## Features

- **HEIC to PNG conversion** with high quality output
- **Quality control** (1-100) for file size optimization
- **Pure Python implementation** using PIL (Pillow) built-in optimization
- **Cross-platform compatibility** - works on all platforms

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

### Stream Processing (stdin/stdout)

HEIC2PNG supports reading from stdin and writing to stdout, making it perfect for shell pipelines and automated processing:

#### Basic Stream Processing
```bash
# Read from stdin, write to stdout
cat image.heic | heic2png > output.png

# Read from stdin, write to file
cat image.heic | heic2png -o output.png

# Read from file, write to stdout
heic2png -i image.heic > output.png
```

#### Quality Optimization in Streams
```bash
# Low quality (smaller file size)
cat image.heic | heic2png --quality 30 > optimized.png

# High quality (larger file size)
cat image.heic | heic2png --quality 90 > high_quality.png
```

#### Format Conversion in Streams
```bash
# Convert to JPEG
cat image.heic | heic2png --format jpg > output.jpg

# Convert to PNG (default)
cat image.heic | heic2png > output.png
```

#### Advanced Pipeline Examples
```bash
# Batch processing with quality optimization
for file in *.heic; do
    cat "$file" | heic2png --quality 50 > "${file%.heic}_optimized.png"
done

# Process and compress in one pipeline
cat image.heic | heic2png --quality 40 | gzip > compressed.png.gz

# Convert and resize (requires additional tools)
cat image.heic | heic2png | convert - -resize 50% resized.png
```

#### Stream Processing Notes
- **Input**: If no `-i` parameter is specified, input is read from stdin
- **Output**: If no `-o` parameter is specified, output is written to stdout
- **Quality**: Works with all quality settings (1-100)
- **Formats**: Supports PNG, JPG, and JPEG output formats
- **Transparency**: Fully preserved in stream processing

## References

- [Example PyPi Package](https://github.com/tomchen/example_pypi_package)
- [Pillow HEIF](https://github.com/bigcat88/pillow_heif)
- [PIL Image.quantize()](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.quantize)