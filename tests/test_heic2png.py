from genericpath import exists
import unittest
import pytest
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

from heic2png.heic2png import HEIC2PNG


class TestHEIC2PNG(unittest.TestCase):

    __test_input_filename = './test.heic'
    __test_output_filename = './test.png'
    register_heif_opener()

    def test_save(self):

        img = Image.new('RGB', (30, 30), color = 'red')
        img.save(self.__test_input_filename)
        heic2png_obj = HEIC2PNG(self.__test_input_filename)
        heic2png_obj.save(output_image_file_path=self.__test_output_filename)
        self.assertTrue(Path(self.__test_output_filename).exists())

    @pytest.fixture(autouse=True)
    def run_around_tests(self):
        # before
        yield
        # after
        input_file = Path(self.__test_input_filename)
        output_file = Path(self.__test_output_filename)
        if input_file.exists():
            input_file.unlink()
        if output_file.exists():
            output_file.unlink()


if __name__ == '__main__':
    unittest.main()
