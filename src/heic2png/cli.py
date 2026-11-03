"""The ``heic2png`` command."""
import argparse
import logging
import sys
import traceback
from pathlib import Path
from typing import BinaryIO, NoReturn, Optional, Sequence, Union

from heic2png import __version__
from heic2png.heic2png import (
    DEFAULT_EXTENSION, HEIC2PNG, MAX_PALETTE_COLORS, MAX_QUALITY, MIN_QUALITY, OUTPUT_EXTENSIONS,
    output_extension,
)

# Logging is configured in cli(), not at import time, so `import heic2png`
# does not change the logging setup of the program that imports it.
logger = logging.getLogger(__name__)

PROG = "heic2png"
ISSUES_URL = "https://github.com/NatLee/heic2png/issues"
EPILOG = f"""
Examples:
  %(prog)s -i photo.heic                    writes photo.png next to photo.heic
  %(prog)s -i photo.heic -o out.png -q 100  keeps every color
  %(prog)s -i photo.heic -f jpg             writes photo.jpg
  %(prog)s -i photo.heic -o photo.jpg       the file name picks JPEG
  cat photo.heic | %(prog)s > photo.png     stdin to stdout, no messages

Notes:
  - Without -i, the image is read from stdin.
  - Without -o, the output goes next to the input file, or to stdout when
    reading from stdin.
  - The format comes from -f, else from the -o file name ({', '.join(OUTPUT_EXTENSIONS)}),
    else it is {DEFAULT_EXTENSION.lstrip('.')}. A -o name of another format is refused.
  - Below quality {MAX_QUALITY}, PNG output is reduced to at most {MAX_PALETTE_COLORS} colors.
    For JPEG output, quality is the usual JPEG quality.
  - Messages go to stderr, so stdout only ever carries image data.
"""


class CLIError(Exception):
    """An error meant for the user: cli() prints the message and exits with status 1."""


class UsageError(CLIError):
    """Options that cannot work together: cli() prints the usage and exits with status 2, like argparse."""


def _quality(value: str) -> int:
    """argparse type for --quality: a whole number from MIN_QUALITY to MAX_QUALITY."""
    try:
        quality = int(value)
    except ValueError:
        quality = 0
    if not MIN_QUALITY <= quality <= MAX_QUALITY:
        raise argparse.ArgumentTypeError(
            f"must be a whole number from {MIN_QUALITY} to {MAX_QUALITY}, got {value!r}"
        )
    return quality


def setup_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the heic2png command."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Convert HEIC images to PNG format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )

    io_group = parser.add_argument_group('Input/Output Options')
    io_group.add_argument(
        "-i", "--input-path",
        type=Path,
        help="Path to the input HEIC image (if not specified, reads from stdin)",
    )
    io_group.add_argument(
        "-o", "--output-path",
        type=Path,
        help="Path to save the converted image (default: next to the input file, "
             "or stdout when reading from stdin)",
    )

    conversion_group = parser.add_argument_group('Conversion Options')
    conversion_group.add_argument(
        "-q", "--quality",
        type=_quality,
        default=80,
        metavar="QUALITY",
        help=f"Quality of the converted image ({MIN_QUALITY}-{MAX_QUALITY}), default: %(default)s. "
             f"Below {MAX_QUALITY}, PNG output is reduced to a palette of at most {MAX_PALETTE_COLORS} colors; "
             f"use {MAX_QUALITY} to keep every color.",
    )
    conversion_group.add_argument(
        "-f", "--format",
        choices=[extension.lstrip('.') for extension in OUTPUT_EXTENSIONS],
        help=f"Output format (default: from the -o file name, else {DEFAULT_EXTENSION.lstrip('.')})",
    )

    behavior_group = parser.add_argument_group('Behavior Options')
    behavior_group.add_argument(
        "-w", "--overwrite",
        action="store_true",
        help="Overwrite existing output file",
    )
    behavior_group.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-error messages",
    )
    behavior_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed processing information",
    )
    behavior_group.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def is_stream_mode(args: argparse.Namespace) -> bool:
    """Stream mode means reading from stdin; it prints no progress messages."""
    return args.input_path is None


def validate_args(args: argparse.Namespace) -> None:
    """
    Check combinations argparse cannot check by itself.

    Raises:
        UsageError: If the arguments cannot work together.
    """
    if args.input_path is None and sys.stdin.isatty():
        raise UsageError("No input: give a file with -i, or pipe an image into stdin (see --help)")
    if args.quiet and args.verbose:
        raise UsageError("--quiet and --verbose cannot be used together")
    try:
        output_extension(_requested_extension(args), args.output_path)
    except ValueError as e:  # -f and -o disagree, or -o names a format heic2png cannot write
        raise UsageError(str(e)) from e


def _requested_extension(args: argparse.Namespace) -> Optional[str]:
    return f".{args.format}" if args.format else None


def process_image(args: argparse.Namespace) -> Union[Path, BinaryIO]:
    """
    Convert the image as the parsed arguments ask.

    Returns:
        The path of the converted image, or the binary stdout stream it was written to.

    Raises:
        CLIError: If the input cannot be read or the output cannot be written.
    """
    extension = output_extension(_requested_extension(args), args.output_path)
    try:
        converter = HEIC2PNG(
            image_file_path=args.input_path if args.input_path is not None else "",
            quality=args.quality,
            overwrite=args.overwrite,
        )
        logger.info("Converting image...")
        if args.verbose:
            _log_settings(args, converter._output_path(args.output_path, extension), extension)
        result = converter.save(args.output_path, extension=extension)
    except FileExistsError as e:
        raise CLIError(f"{e}. Use -w/--overwrite to replace it.") from e
    except (OSError, ValueError) as e:
        raise CLIError(str(e)) from e

    if isinstance(result, Path):
        logger.info(f"Successfully saved converted image to: {result}")
    return result


def cli(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the heic2png command.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        The exit status: 0 on success, 1 on error, 130 when interrupted. Usage errors
        exit with status 2 through argparse (SystemExit), as invalid options do.
    """
    parser = setup_parser()
    args = parser.parse_args(argv)
    try:
        validate_args(args)
    except UsageError as e:
        parser.error(str(e))
    _configure_logging(quiet=args.quiet or is_stream_mode(args))

    try:
        process_image(args)
        return 0
    except CLIError as e:
        logger.error(f"{PROG}: error: {e}")
        if args.verbose and e.__cause__ is not None:
            _log_traceback(e.__cause__)
        return 1
    except KeyboardInterrupt:
        logger.error("\nOperation cancelled by user")
        return 130
    except Exception as e:  # a bug in heic2png or a library: ask for a report
        logger.error(f"{PROG}: unexpected error: {e}")
        if args.verbose:
            _log_traceback(e)
        logger.error(f"Please report this issue: {ISSUES_URL}")
        return 1


def main() -> NoReturn:
    """Entry point of the heic2png console script."""
    sys.exit(cli())


def _configure_logging(quiet: bool) -> None:
    """
    Print the command's messages to stderr as plain lines.

    Only this module's logger gets a level, so other libraries keep their own
    (Pillow's debug messages stay hidden, also with --verbose).
    """
    logging.basicConfig(format='%(message)s', stream=sys.stderr)
    logger.setLevel(logging.WARNING if quiet else logging.INFO)


def _log_settings(args: argparse.Namespace, output_path: Optional[Path], extension: str) -> None:
    logger.info("Conversion settings:")
    logger.info(f"Input: {args.input_path}")
    logger.info(f"Output: {output_path if output_path is not None else 'stdout'}")
    logger.info(f"Quality: {args.quality}")
    logger.info(f"Format: {extension.lstrip('.').lower()}")
    logger.info(f"Overwrite: {args.overwrite}")


def _log_traceback(error: BaseException) -> None:
    logger.error(''.join(traceback.format_exception(type(error), error, error.__traceback__)).rstrip())


if __name__ == "__main__":
    main()
