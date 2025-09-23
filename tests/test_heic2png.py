import os
import sys
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

# Transparency test files
TEST_TRANSPARENT_INPUT_FILENAME = './test_transparent.png'
TEST_TRANSPARENT_OUTPUT_FILENAME = './test_transparent_output.png'
TEST_TRANSPARENT_OPTIMIZED_FILENAME = './test_transparent_optimized.png'

# Register HEIF opener before running tests
register_heif_opener()

@pytest.fixture
def cleanup():
    # Cleanup files before and after tests
    yield  # This allows the test to run in between the setup and teardown

    all_test_files = [
        TEST_INPUT_FILENAME, 
        TEST_LOW_QUALITY_OUTPUT_FILENAME, 
        TEST_HIGH_QUALITY_OUTPUT_FILENAME,
        TEST_TRANSPARENT_INPUT_FILENAME,
        TEST_TRANSPARENT_OUTPUT_FILENAME,
        TEST_TRANSPARENT_OPTIMIZED_FILENAME
    ]
    
    for path in all_test_files:
        file = Path(path)
        if file.exists():
            file.unlink()

def test_quality(cleanup):
    # Create a random image for accurate testing
    data = np.random.random((200,200,3)) * 255
    img = Image.fromarray(data.astype('uint8'))
    img.save(TEST_INPUT_FILENAME)

    # Convert to PNG with high quality (no optimization)
    heic2png_obj_high = HEIC2PNG(TEST_INPUT_FILENAME, quality=None)
    heic2png_obj_high.save(output_image_file_path=TEST_HIGH_QUALITY_OUTPUT_FILENAME)

    # Convert to PNG with low quality (with optimization)
    heic2png_obj_low = HEIC2PNG(TEST_INPUT_FILENAME, quality=10)
    heic2png_obj_low.save(output_image_file_path=TEST_LOW_QUALITY_OUTPUT_FILENAME)

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
        with open(inputfile, "rb") as sys.stdin, \
             open(outputfile, "wb") as sys.stdout:
            converter = HEIC2PNG("")  # Pass empty string to read from stdin
            converter.save()
    finally:
        sys.stdin, sys.stdout = save_stdin, save_stdout
        with open(inputfile, "rb") as inp, \
             open(outputfile, "rb") as outp:
            assert len(outp.read()) > len(inp.read())
        os.unlink(outputfile)

def test_transparency_preservation(cleanup):
    """Test that transparency is preserved during PNG optimization."""
    # Create a complex transparent image
    data = np.zeros((200, 200, 4), dtype=np.uint8)
    
    # Create gradient background with transparency
    for i in range(200):
        for j in range(200):
            data[i, j, 0] = int(i * 255 / 200)  # Red gradient
            data[i, j, 1] = int(j * 255 / 200)  # Green gradient
            data[i, j, 2] = int((i + j) * 255 / 400)  # Blue gradient
            data[i, j, 3] = 200  # Semi-transparent
    
    # Add fully opaque region
    data[50:150, 50:150, 3] = 255
    
    # Add fully transparent region
    data[0:50, 0:50, 3] = 0
    
    # Save original transparent image
    img = Image.fromarray(data)
    img.save(TEST_TRANSPARENT_INPUT_FILENAME)
    
    # Test conversion without optimization
    converter_no_opt = HEIC2PNG(TEST_TRANSPARENT_INPUT_FILENAME, quality=None)
    converter_no_opt.save(output_image_file_path=TEST_TRANSPARENT_OUTPUT_FILENAME)
    
    # Test conversion with optimization
    converter_opt = HEIC2PNG(TEST_TRANSPARENT_INPUT_FILENAME, quality=30)
    converter_opt.save(output_image_file_path=TEST_TRANSPARENT_OPTIMIZED_FILENAME)
    
    # Check that files exist
    assert Path(TEST_TRANSPARENT_OUTPUT_FILENAME).exists()
    assert Path(TEST_TRANSPARENT_OPTIMIZED_FILENAME).exists()
    
    # Load and check the optimized image
    optimized_img = Image.open(TEST_TRANSPARENT_OPTIMIZED_FILENAME)
    
    # Check that transparency is preserved
    assert optimized_img.mode in ['RGBA', 'LA', 'P'], f"Expected transparent mode, got {optimized_img.mode}"
    
    # If it's palette mode, check for transparency information
    if optimized_img.mode == 'P':
        assert optimized_img.info.get('transparency') is not None, "Palette image should have transparency information"
        
        # Check that palette has reasonable number of colors
        palette = optimized_img.getpalette()
        assert palette is not None, "Palette image should have a palette"
        num_colors = len(palette) // 3
        assert 2 <= num_colors <= 256, f"Expected 2-256 colors, got {num_colors}"
    
    # Check file size reduction
    original_size = Path(TEST_TRANSPARENT_INPUT_FILENAME).stat().st_size
    optimized_size = Path(TEST_TRANSPARENT_OPTIMIZED_FILENAME).stat().st_size
    
    # Optimized image should be smaller
    assert optimized_size < original_size, f"Optimized image should be smaller: {optimized_size} >= {original_size}"
    
    # Should achieve reasonable compression (at least 10% reduction)
    reduction_percent = (original_size - optimized_size) / original_size * 100
    assert reduction_percent >= 10, f"Expected at least 10% reduction, got {reduction_percent:.1f}%"

def test_transparency_edge_cases(cleanup):
    """Test edge cases for transparency handling."""
    # Test 1: Fully transparent image
    data = np.zeros((100, 100, 4), dtype=np.uint8)
    data[:, :, 3] = 0  # Fully transparent
    img = Image.fromarray(data)
    img.save(TEST_TRANSPARENT_INPUT_FILENAME)
    
    converter = HEIC2PNG(TEST_TRANSPARENT_INPUT_FILENAME, quality=50, overwrite=True)
    converter.save(output_image_file_path=TEST_TRANSPARENT_OUTPUT_FILENAME)
    
    result_img = Image.open(TEST_TRANSPARENT_OUTPUT_FILENAME)
    assert result_img.mode in ['RGBA', 'LA', 'P'], "Fully transparent image should preserve transparency mode"
    
    # Test 2: Fully opaque image
    data = np.random.randint(0, 255, (100, 100, 4), dtype=np.uint8)
    data[:, :, 3] = 255  # Fully opaque
    img = Image.fromarray(data)
    img.save(TEST_TRANSPARENT_INPUT_FILENAME)
    
    converter = HEIC2PNG(TEST_TRANSPARENT_INPUT_FILENAME, quality=50, overwrite=True)
    converter.save(output_image_file_path=TEST_TRANSPARENT_OUTPUT_FILENAME)
    
    result_img = Image.open(TEST_TRANSPARENT_OUTPUT_FILENAME)
    assert result_img.mode in ['RGBA', 'LA', 'P'], "Fully opaque image should preserve transparency mode"
    
    # Test 3: Mixed transparency levels
    data = np.zeros((100, 100, 4), dtype=np.uint8)
    data[:, :, :3] = 128  # Gray color
    data[0:33, :, 3] = 0      # Fully transparent
    data[33:66, :, 3] = 128  # Semi-transparent
    data[66:100, :, 3] = 255 # Fully opaque
    
    img = Image.fromarray(data)
    img.save(TEST_TRANSPARENT_INPUT_FILENAME)
    
    converter = HEIC2PNG(TEST_TRANSPARENT_INPUT_FILENAME, quality=30, overwrite=True)
    converter.save(output_image_file_path=TEST_TRANSPARENT_OUTPUT_FILENAME)
    
    result_img = Image.open(TEST_TRANSPARENT_OUTPUT_FILENAME)
    assert result_img.mode in ['RGBA', 'LA', 'P'], "Mixed transparency image should preserve transparency mode"
    
    if result_img.mode == 'P':
        assert result_img.info.get('transparency') is not None, "Mixed transparency should be preserved in palette"

def test_cli_stdin_stdout_compatibility(cleanup):
    """Test CLI stdin/stdout functionality and compatibility with regular file operations."""
    import subprocess
    import os
    
    # Test 1: Regular file input/output
    input_file = "tests/calder-flamingo.heic"
    output_file = "test_regular_cli.png"
    
    result = subprocess.run([
        'heic2png', '-i', input_file, '-o', output_file, '--quality', '80', '--overwrite'
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"Regular CLI failed: {result.stderr}"
    assert os.path.exists(output_file), "Regular CLI output file not created"
    
    # Test 2: stdin/stdout
    stdin_output_file = "test_stdin_cli.png"
    
    with open(input_file, 'rb') as inp:
        with open(stdin_output_file, 'wb') as outp:
            result = subprocess.run([
                'heic2png', '--quality', '80'
            ], stdin=inp, stdout=outp, stderr=subprocess.PIPE, text=True)
    
    assert result.returncode == 0, f"stdin/stdout CLI failed: {result.stderr}"
    assert os.path.exists(stdin_output_file), "stdin/stdout output file not created"
    
    # Test 3: Compare file sizes (should be similar for same quality)
    regular_size = os.path.getsize(output_file)
    stdin_size = os.path.getsize(stdin_output_file)
    
    # Allow 5% difference due to compression variations
    size_diff_percent = abs(regular_size - stdin_size) / regular_size * 100
    assert size_diff_percent < 5, f"File sizes differ too much: {regular_size} vs {stdin_size} ({size_diff_percent:.1f}%)"
    
    # Test 4: stdin with different quality
    stdin_optimized_file = "test_stdin_optimized.png"
    
    with open(input_file, 'rb') as inp:
        with open(stdin_optimized_file, 'wb') as outp:
            result = subprocess.run([
                'heic2png', '--quality', '30'
            ], stdin=inp, stdout=outp, stderr=subprocess.PIPE, text=True)
    
    assert result.returncode == 0, f"stdin/stdout optimized CLI failed: {result.stderr}"
    assert os.path.exists(stdin_optimized_file), "stdin/stdout optimized output file not created"
    
    # Test 5: Verify optimization worked (optimized should be smaller)
    optimized_size = os.path.getsize(stdin_optimized_file)
    assert optimized_size < stdin_size, f"Optimized file should be smaller: {optimized_size} >= {stdin_size}"
    
    # Test 6: stdout only (no output file specified)
    stdout_output_file = "test_stdout_only.png"
    
    with open(input_file, 'rb') as inp:
        with open(stdout_output_file, 'wb') as outp:
            result = subprocess.run([
                'heic2png', '--quality', '80'
            ], stdin=inp, stdout=outp, stderr=subprocess.PIPE, text=True)
    
    assert result.returncode == 0, f"stdout-only CLI failed: {result.stderr}"
    assert os.path.exists(stdout_output_file), "stdout-only output file not created"
    
    # Cleanup test files
    for file in [output_file, stdin_output_file, stdin_optimized_file, stdout_output_file]:
        if os.path.exists(file):
            os.remove(file)

def test_cli_error_handling():
    """Test CLI error handling for invalid inputs."""
    import subprocess
    
    # Test 1: Non-existent input file
    result = subprocess.run([
        'heic2png', '-i', 'non_existent.heic', '-o', 'output.png'
    ], capture_output=True, text=True)
    
    assert result.returncode != 0, "Should fail for non-existent file"
    assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()
    
    # Test 2: Invalid quality value
    result = subprocess.run([
        'heic2png', '-i', 'tests/calder-flamingo.heic', '-o', 'output.png', '--quality', '150'
    ], capture_output=True, text=True)
    
    assert result.returncode != 0, "Should fail for invalid quality"
    assert "quality" in result.stderr.lower() or "error" in result.stderr.lower()
    
    # Test 3: stdin with no data
    result = subprocess.run([
        'heic2png', '-o', 'output.png'
    ], stdin=subprocess.DEVNULL, capture_output=True, text=True)
    
    assert result.returncode != 0, "Should fail for empty stdin"
    assert "error" in result.stderr.lower() or "failed" in result.stderr.lower()
