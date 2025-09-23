import os
import sys
import subprocess
from pathlib import Path

import pytest
import numpy as np
from PIL import Image
from pillow_heif import register_heif_opener

from heic2png.heic2png import HEIC2PNG

# Paths for test files
TEST_INPUT_FILENAME = './test.heic'
TEST_LOW_QUALITY_OUTPUT_FILENAME = './test_low_quality.png'
TEST_HIGH_QUALITY_OUTPUT_FILENAME = './test_high_quality.png'

# Register HEIF opener before running tests
register_heif_opener()

@pytest.fixture
def cleanup():
    # Cleanup files before and after tests
    yield  # This allows the test to run in between the setup and teardown

    for path in [TEST_INPUT_FILENAME, TEST_LOW_QUALITY_OUTPUT_FILENAME, TEST_HIGH_QUALITY_OUTPUT_FILENAME]:
        file = Path(path)
        if file.exists():
            file.unlink()

def test_quality(cleanup):
    # Create a random image for accurate testing
    data = np.random.random((200,200,3)) * 255
    img = Image.fromarray(data.astype('uint8'))
    img.save(TEST_INPUT_FILENAME)

    # Convert to PNG
    heic2png_obj = HEIC2PNG(TEST_INPUT_FILENAME)
    heic2png_obj.save(output_image_file_path=TEST_HIGH_QUALITY_OUTPUT_FILENAME)

    # Optimize PNG with pngquant
    subprocess.run(['pngquant', '--quality=10-10', '-o', TEST_LOW_QUALITY_OUTPUT_FILENAME, TEST_HIGH_QUALITY_OUTPUT_FILENAME])

    # Check if both files exist
    assert Path(TEST_LOW_QUALITY_OUTPUT_FILENAME).exists()
    assert Path(TEST_HIGH_QUALITY_OUTPUT_FILENAME).exists()

    # Compare file sizes to check if quality setting is effective
    low_quality_size = Path(TEST_LOW_QUALITY_OUTPUT_FILENAME).stat().st_size
    high_quality_size = Path(TEST_HIGH_QUALITY_OUTPUT_FILENAME).stat().st_size

    assert low_quality_size < high_quality_size, "High quality image should be larger in size"

def test_stdin_stdout():
    inputfile = "tests/calder-flamingo.heic"
    outputfile = "tests/calder-flamingo.png"
    try:
        save_stdin, save_stdout = (sys.stdin, sys.stdout)
        if os.path.exists(outputfile):
            os.unlink(outputfile)
        with (open(inputfile, "rb") as sys.stdin,
              open(outputfile, "wb") as sys.stdout):
            converter = HEIC2PNG()
            converter.save()
    finally:
        sys.stdin, sys.stdout = save_stdin, save_stdout
        with (open(inputfile, "rb") as inp,
              open(outputfile, "rb") as outp):
            assert len(outp.read()) > len(inp.read())
        os.unlink(outputfile)
