import sys
import traceback
import argparse
from pillow_heif import register_heif_opener

from heic2png import __version__
from heic2png.heic2png import HEIC2PNG


def eprint(*args, file=sys.stderr, **kwds):
    "print to stderr by default"
    print(*args, file=file, **kwds)

def cli(args):
    """
    Command Line Interface for converting HEIC images to PNG.

    :param args: Parsed command-line arguments.
    """
    eprint(f'Processing the HEIC image at `{args.input_path}`')

    if args.output_path:
        eprint(f'Specified output path: `{args.output_path}`')

    if args.quality and not 1 <= args.quality <= 100:
        eprint('Error: Quality should be a value between 1 and 100.')
        return

    try:
        eprint('==========================')
        eprint('==== HEIC2PNG Options ====')
        eprint('==========================')
        eprint(f'>> Input file path: {args.input_path}')
        eprint(f'>> Output file path: {args.output_path}')
        eprint(f'>> Quality: {args.quality}')
        eprint(f'>> Overwrite: {args.overwrite}')
        eprint('==========================')
        heic_img = HEIC2PNG(args.input_path, args.quality, args.overwrite)
        eprint('Converting the image...')

        if args.output_path and args.overwrite:
            eprint(f'Overwriting the existing file at `{args.output_path}`')

        output_path = heic_img.save(args.output_path)
        eprint(f'Success! The converted image is saved at `{output_path}`')

    except FileExistsError:
        eprint('Error: The specified output file already exists.')
        eprint('Use the -w option to overwrite the existing file.')

    except ValueError as e:
        eprint('Error: Invalid input or output format.')
        eprint(e)
        traceback.print_exc()

    except Exception as e:
        eprint(f'An unexpected error occurred: {e}')
        eprint('Here are the details:')
        eprint('==========================')
        traceback.print_exc()
        eprint('==========================')
        eprint('Please report this issue with the full traceback.')
        eprint('-> https://github.com/NatLee/HEIC2PNG/issues')



def main():
    """
    Main function to register the HEIF opener and initiate the argparse CLI.
    """
    register_heif_opener()

    eprint(f'HEIC2PNG v{__version__}')

    parser = argparse.ArgumentParser(description="Convert HEIC images to PNG.",
        epilog="""
In the absence of an input (-i) file, input is read from sys.stdin.
In the absence of an output (-o) file, output is written to sys.stdout.
""")
    parser.add_argument("-i", "--input_path", help="Path to the input HEIC image.")
    parser.add_argument("-o", "--output_path", help="Path to save the converted PNG image.")
    parser.add_argument("-q", "--quality", type=int, help="Quality of the converted PNG image (1-100).")
    parser.add_argument("-w", "--overwrite", action="store_true", help="Overwrite the existing file if it already exists.")

    args = parser.parse_args()
    cli(args)
