from fire import Fire
from pillow_heif import register_heif_opener

from .heic2png import HEIC2PNG

def cli(input_path:str, output_path:str=None):
    print(f'----- Input file path is `{input_path}`')
    if output_path:
        print(f'----- Set the output path is `{output_path}`')
    try:
        heic_img = HEIC2PNG(input_path)
        print(f'----- Processing...')
        output_path = heic_img.save(output_path)
        print(f'----- Output file path is `{output_path}`')
    except FileExistsError:
        print('----- File already exists!')
    except ValueError:
        print('----- You need to check the format of image!')
        print('Input must be `.heic` and output must be `.png`.')
    except Exception as e:
        print(f'----- Error with {e}')
        print('----- Please report this issue!')

def main():
    register_heif_opener()
    Fire(cli)
