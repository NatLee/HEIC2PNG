"""Tests for the heic2png command.

Most tests call cli() in-process: messages are checked through caplog and image
data on stdout through capsysbinary. The tests at the end run the installed
command on the real sample photo.
"""
import io
import sys

import pytest
from PIL import Image

from heic2png import __version__
from heic2png import cli as cli_module
from heic2png.cli import cli, main, setup_parser

from .images import noise


@pytest.fixture
def photo(tmp_path):
    """A small real HEIC file."""
    path = tmp_path / "photo.heic"
    noise("RGB", (32, 24)).save(path)
    return path


@pytest.fixture
def stdin(monkeypatch):
    """Replace stdin with a text stream over the given bytes, like a shell pipe."""
    def feed(data: bytes) -> None:
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(data)))
    return feed


class _Terminal:
    def isatty(self) -> bool:
        return True


# --- options -----------------------------------------------------------------

def test_options_and_defaults_are_unchanged():
    parser = setup_parser()
    options = {s for action in parser._actions for s in action.option_strings}
    assert options == {
        "-h", "--help", "-i", "--input-path", "-o", "--output-path", "-q", "--quality",
        "-f", "--format", "-w", "--overwrite", "--quiet", "-v", "--verbose", "--version",
    }
    args = parser.parse_args([])
    assert (args.quality, args.format, args.overwrite, args.quiet, args.verbose) == (80, "png", False, False, False)


def test_help_describes_where_the_output_goes():
    text = setup_parser().format_help()
    assert "Without -o, the output goes next to the input file" in text
    assert "only applies to PNG" not in text  # it applies to JPEG too


@pytest.mark.parametrize("value", ["0", "101", "abc", "1.5"])
def test_invalid_quality_is_a_usage_error(capsys, value):
    with pytest.raises(SystemExit) as exit_info:
        cli(["-i", "photo.heic", "-q", value])

    assert exit_info.value.code == 2
    err = capsys.readouterr().err
    assert f"argument -q/--quality: must be a whole number from 1 to 100, got '{value}'" in err
    assert "choose from" not in err


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"heic2png {__version__}\n"


# --- converting files --------------------------------------------------------

def test_converts_next_to_the_input(photo, caplog):
    assert cli(["-i", str(photo)]) == 0

    out = photo.with_suffix(".png")
    with Image.open(out) as img:
        assert img.format == "PNG"
        assert img.mode == "P"  # default quality 80 reduces the colors
    assert caplog.messages == ["Converting image...", f"Successfully saved converted image to: {out}"]


@pytest.mark.parametrize("args, name, image_format, mode", [
    (["-o", "out.png", "-q", "100"], "out.png", "PNG", "RGB"),
    (["-f", "jpg"], "photo.jpg", "JPEG", "RGB"),
    (["-f", "jpeg", "-o", "out.jpeg"], "out.jpeg", "JPEG", "RGB"),
])
def test_output_path_quality_and_format(photo, tmp_path, monkeypatch, args, name, image_format, mode):
    monkeypatch.chdir(tmp_path)

    assert cli(["-i", str(photo), *args]) == 0

    with Image.open(tmp_path / name) as img:
        assert (img.format, img.mode) == (image_format, mode)


def test_existing_output_needs_overwrite(photo, caplog):
    out = photo.with_suffix(".png")
    out.write_bytes(b"keep me")

    assert cli(["-i", str(photo)]) == 1
    assert out.read_bytes() == b"keep me"
    assert caplog.messages[-1] == (
        f"heic2png: error: Output file already exists: {out}. Use -w/--overwrite to replace it."
    )

    assert cli(["-i", str(photo), "-w"]) == 0
    assert out.read_bytes().startswith(b"\x89PNG")


def test_quiet_prints_nothing(photo, caplog):
    assert cli(["-i", str(photo), "--quiet"]) == 0
    assert photo.with_suffix(".png").exists()
    assert caplog.messages == []


def test_verbose_lists_the_settings(photo, caplog):
    assert cli(["-i", str(photo), "--verbose"]) == 0
    assert caplog.messages == [
        "Converting image...",
        "Conversion settings:",
        f"Input: {photo}",
        f"Output: {photo.with_suffix('.png')}",
        "Quality: 80",
        "Format: png",
        "Overwrite: False",
        f"Successfully saved converted image to: {photo.with_suffix('.png')}",
    ]


def test_quiet_and_verbose_cannot_be_combined(photo, caplog):
    assert cli(["-i", str(photo), "--quiet", "--verbose"]) == 1
    assert caplog.messages == ["heic2png: error: --quiet and --verbose cannot be used together"]


# --- errors ------------------------------------------------------------------

@pytest.mark.parametrize("name, content, message", [
    ("missing.heic", None, "Input file not found: "),
    ("notes.txt", b"hello", "Unsupported input file type: "),
    ("broken.heic", b"not an image", "is damaged or not a supported image"),
])
def test_input_errors_say_what_is_wrong(tmp_path, caplog, name, content, message):
    src = tmp_path / name
    if content is not None:
        src.write_bytes(content)

    assert cli(["-i", str(src)]) == 1

    assert len(caplog.messages) == 1
    assert caplog.messages[0].startswith("heic2png: error: ")
    assert message in caplog.messages[0]


def test_verbose_errors_include_the_traceback(tmp_path, caplog):
    src = tmp_path / "broken.heic"
    src.write_bytes(b"not an image")

    assert cli(["-i", str(src), "--verbose"]) == 1
    assert caplog.messages[-1].startswith("Traceback (most recent call last):")


def test_no_input_on_a_terminal(monkeypatch, caplog):
    monkeypatch.setattr(sys, "stdin", _Terminal())

    assert cli([]) == 1
    assert caplog.messages == [
        "heic2png: error: No input: give a file with -i, or pipe an image into stdin (see --help)"
    ]


def test_ctrl_c_exits_with_130(photo, monkeypatch, caplog):
    def interrupted(args):
        raise KeyboardInterrupt
    monkeypatch.setattr(cli_module, "process_image", interrupted)

    assert cli(["-i", str(photo)]) == 130
    assert caplog.messages == ["\nOperation cancelled by user"]


@pytest.mark.parametrize("verbose", [False, True])
def test_unexpected_errors_ask_for_a_bug_report(photo, monkeypatch, caplog, verbose):
    def broken(args):
        raise RuntimeError("boom")
    monkeypatch.setattr(cli_module, "process_image", broken)

    assert cli(["-i", str(photo)] + (["-v"] if verbose else [])) == 1

    assert caplog.messages[0] == "heic2png: unexpected error: boom"
    assert caplog.messages[-1] == "Please report this issue: https://github.com/NatLee/heic2png/issues"
    assert any(m.startswith("Traceback") for m in caplog.messages) == verbose


def test_main_exits_with_the_status_of_cli(photo, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["heic2png", "--quiet", "-i", str(photo)])
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 0

    monkeypatch.setattr(sys, "argv", ["heic2png", "--quiet", "-i", str(photo)])  # now the output exists
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 1


# --- stdin and stdout --------------------------------------------------------

def test_stdin_to_stdout_prints_only_image_data(photo, stdin, capsysbinary, caplog):
    stdin(photo.read_bytes())

    assert cli([]) == 0

    captured = capsysbinary.readouterr()
    assert captured.out.startswith(b"\x89PNG\r\n\x1a\n")
    assert captured.err == b""
    assert caplog.messages == []


def test_stdin_with_output_path(photo, stdin, tmp_path, capsysbinary, caplog):
    stdin(photo.read_bytes())

    assert cli(["-o", str(tmp_path / "out.png"), "-f", "png"]) == 0

    assert (tmp_path / "out.png").read_bytes().startswith(b"\x89PNG")
    assert capsysbinary.readouterr().out == b""
    assert caplog.messages == []


def test_damaged_stdin_is_an_error_even_in_stream_mode(stdin, capsysbinary, caplog):
    stdin(b"not an image")

    assert cli([]) == 1
    assert capsysbinary.readouterr().out == b""
    assert caplog.messages == ["heic2png: error: Failed to open image: the input stream is damaged or not a supported image"]


# --- the installed command on the real sample photo --------------------------

def test_file_and_stdin_give_the_same_png(heic2png, sample_heic, tmp_path):
    from_file = heic2png("-i", sample_heic, "-o", "from_file.png")
    from_stdin = heic2png(stdin=sample_heic)

    assert from_file.returncode == 0, from_file.stderr
    assert from_stdin.returncode == 0, from_stdin.stderr
    assert from_stdin.stdout == (tmp_path / "from_file.png").read_bytes()
    assert from_stdin.stderr == b""  # stream mode prints no messages
    with Image.open(tmp_path / "from_file.png") as img:  # the README's "about 200 colors" at the default
        assert img.mode == "P"
        assert len(img.getcolors()) <= 204


def test_lower_quality_gives_a_smaller_file(heic2png, sample_heic):
    default = heic2png(stdin=sample_heic)
    low = heic2png("--quality", 30, stdin=sample_heic)

    assert low.returncode == 0, low.stderr
    assert 0 < len(low.stdout) < len(default.stdout)


@pytest.mark.parametrize("args, message", [
    (["-i", "missing.heic", "-o", "out.png"], b"heic2png: error: Input file not found: missing.heic"),
    (["-i", "{sample}", "-o", "out.png", "--quality", "150"], b"must be a whole number from 1 to 100"),
    (["-o", "out.png"], b"<stdin> is damaged or not a supported image"),  # stdin is empty
])
def test_errors_exit_non_zero(heic2png, sample_heic, tmp_path, args, message):
    result = heic2png(*[a.format(sample=sample_heic) for a in args])

    assert result.returncode != 0
    assert message in result.stderr
    assert b"nexpected" not in result.stderr
    assert not (tmp_path / "out.png").exists()
