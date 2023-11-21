import traceback
import argparse
from pillow_heif import register_heif_opener

from . import __version__
from .heic2png import HEIC2PNG

def cli(args):
    """
    Command Line Interface for converting HEIC images to PNG.

    :param args: Parsed command-line arguments.
    """
    print(f'Processing the HEIC image at `{args.input_path}`')

    if args.output_path:
        print(f'Specified output path: `{args.output_path}`')

    if args.quality and not 1 <= args.quality <= 100:
        print('Error: Quality should be a value between 1 and 100.')
        return

    try:
        print('==========================')
        print('==== HEIC2PNG Options ====')
        print('==========================')
        print(f'>> Input file path: {args.input_path}')
        print(f'>> Output file path: {args.output_path}')
        print(f'>> Quality: {args.quality}')
        print(f'>> Overwrite: {args.overwrite}')
        print('==========================')
        heic_img = HEIC2PNG(args.input_path, args.quality, args.overwrite)
        print('Converting the image...')

        if args.output_path and args.overwrite:
            print(f'Overwriting the existing file at `{args.output_path}`')

        output_path = heic_img.save(args.output_path)
        print(f'Success! The converted image is saved at `{output_path}`')

    except FileExistsError:
        print('Error: The specified output file already exists.')
        print('Use the -w option to overwrite the existing file.')

    except ValueError as e:
        print('Error: Invalid input or output format.')
        print(e)
        traceback.print_exc()

    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        print('Here are the details:')
        print('==========================')
        traceback.print_exc()
        print('==========================')
        print('Please report this issue with the full traceback.')
        print('-> https://github.com/NatLee/HEIC2PNG/issues')

def main():
    """
    Main function to register the HEIF opener and initiate the argparse CLI.
    """
    register_heif_opener()

    print(f'HEIC2PNG v{__version__}')

    parser = argparse.ArgumentParser(description="Convert HEIC images to PNG.")
    parser.add_argument("-i", "--input_path", required=True, help="Path to the input HEIC image.")
    parser.add_argument("-o", "--output_path", help="Path to save the converted PNG image.")
    parser.add_argument("-q", "--quality", type=int, help="Quality of the converted PNG image (1-100).")
    parser.add_argument("-w", "--overwrite", action="store_true", help="Overwrite the existing file if it already exists.")

    args = parser.parse_args()
    cli(args)
