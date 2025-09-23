import sys
import logging
import argparse
from pathlib import Path
from typing import Optional, Sequence, NoReturn

from pillow_heif import register_heif_opener

from heic2png import __version__
from heic2png.heic2png import HEIC2PNG

logging.basicConfig(
    format='%(message)s',
    level=logging.INFO,
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class CLIError(Exception):
    """Custom exception for CLI errors."""
    pass

def setup_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Convert HEIC images to PNG format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i image.heic -o output.png
  %(prog)s -i image.heic -o output.png -q 80
  %(prog)s -i image.heic -o output.png -w
  cat image.heic | %(prog)s > output.png

Notes:
  - If no input (-i) is specified, input is read from stdin
  - If no output (-o) is specified, output is written to stdout
  - Quality setting only applies to PNG output format
        """
    )
    
    input_group = parser.add_argument_group('Input/Output Options')
    input_group.add_argument(
        "-i", "--input-path",
        help="Path to the input HEIC image (if not specified, reads from stdin)",
        type=Path
    )
    input_group.add_argument(
        "-o", "--output-path",
        help="Path to save the converted image",
        type=Path
    )
    
    conversion_group = parser.add_argument_group('Conversion Options')
    conversion_group.add_argument(
        "--quality",
        type=int,
        help="Quality of the converted image (1-100), default: 80",
        metavar="QUALITY",
        choices=range(1, 101),
        default=80,
    )
    conversion_group.add_argument(
        "-f", "--format",
        choices=['png', 'jpg', 'jpeg'],
        default='png',
        help="Output format (default: png)"
    )
    
    behavior_group = parser.add_argument_group('Behavior Options')
    behavior_group.add_argument(
        "-w", "--overwrite",
        action="store_true",
        help="Overwrite existing output file"
    )
    behavior_group.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress non-error messages"
    )
    behavior_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed processing information"
    )
    behavior_group.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    return parser

def validate_args(args: argparse.Namespace) -> None:
    """
    Validate command line arguments.

    Args:
        args: Parsed command line arguments

    Raises:
        CLIError: If arguments are invalid
    """
    if args.input_path is None and sys.stdin.isatty():
        raise CLIError("No input file specified and no data on stdin")

    if args.quality is not None and not 1 <= args.quality <= 100:
        raise CLIError("Quality must be between 1 and 100")

    if args.quiet and args.verbose:
        raise CLIError("Cannot specify both --quiet and --verbose")

def process_image(args: argparse.Namespace) -> Optional[Path]:
    """
    Process the image according to command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Optional[Path]: Path to the output file if successful

    Raises:
        CLIError: If processing fails
    """
    try:
        # Convert None to empty string for stdin reading
        input_path = args.input_path if args.input_path is not None else ""
        
        converter = HEIC2PNG(
            image_file_path=input_path,
            quality=args.quality,
            overwrite=args.overwrite
        )
        
        if not args.quiet:
            logger.info("Converting image...")
            
        if args.verbose:
            logger.info("Conversion settings:")
            logger.info(f"Input: {args.input_path or 'stdin'}")
            logger.info(f"Output: {args.output_path or 'stdout'}")
            logger.info(f"Quality: {args.quality or 'default'}")
            logger.info(f"Format: {args.format}")
            logger.info(f"Overwrite: {args.overwrite}")

        output_path = converter.save(
            output_image_file_path=args.output_path,
            extension=f".{args.format}"
        )
        
        if not args.quiet and output_path != sys.stdout:
            logger.info(f"Successfully saved converted image to: {output_path}")
        
        return output_path

    except FileExistsError:
        raise CLIError(
            "Output file already exists. Use -w/--overwrite to force overwrite."
        )
    except ValueError as e:
        raise CLIError(f"Invalid input: {str(e)}")
    except Exception as e:
        logger.error("Unexpected error occurred during conversion:")
        logger.error(str(e))
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        raise CLIError("Conversion failed. Use --verbose for more details.")

def cli(argv: Optional[Sequence[str]] = None) -> int:
    """
    Main CLI entry point.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    parser = setup_parser()
    args = parser.parse_args(argv)

    # Configure logging based on verbosity
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        validate_args(args)
        process_image(args)
        return 0
    except CLIError as e:
        logger.error(str(e))
        return 1
    except KeyboardInterrupt:
        logger.error("\nOperation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        logger.error("Please report this issue: https://github.com/NatLee/HEIC2PNG/issues")
        return 1

def main() -> NoReturn:
    """
    Script entry point that exits with the appropriate status code.
    """
    register_heif_opener()
    sys.exit(cli())

if __name__ == "__main__":
    main()
