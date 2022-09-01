import unittest
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

from heic2png.heic2png import HEIC2PNG


class TestHEIC2PNG(unittest.TestCase):

    __test_input_filename = 'test.heic'
    __test_output_filename = 'test.png'

    def test_save(self):
        register_heif_opener()
        img = Image.new('RGB', (30, 30), color = 'red')
        img.save(self.__test_input_filename)
        heic2png_obj = HEIC2PNG(self.__test_input_filename)
        heic2png_obj.save()
        self.assertEqual(Path(self.__test_output_filename).exists(), True)

if __name__ == '__main__':
    unittest.main()
