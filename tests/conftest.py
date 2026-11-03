"""Shared fixtures. Tests write only into pytest's tmp_path, never into the working directory."""
import shutil
import subprocess
from contextlib import nullcontext
from pathlib import Path
from typing import Callable, Optional, Union

import pytest
from pillow_heif import register_heif_opener

register_heif_opener()  # lets the tests save .heic files with Pillow

SAMPLE_HEIC = Path(__file__).parent / "calder-flamingo.heic"


@pytest.fixture
def sample_heic() -> Path:
    """A real 4032x3024 iPhone photo."""
    return SAMPLE_HEIC


@pytest.fixture
def heic2png(tmp_path: Path) -> Callable[..., subprocess.CompletedProcess]:
    """
    Run the installed heic2png command inside tmp_path.

    Usage: heic2png("-i", path, "-q", 100, stdin=path_or_None) -> CompletedProcess with bytes output.
    Without stdin= the command gets an empty, non-terminal stdin.
    """
    exe = shutil.which("heic2png")
    if exe is None:
        pytest.fail("the heic2png command is not on PATH; install the package first: pip install -e .")

    def run(*args: Union[str, Path, int], stdin: Optional[Path] = None) -> subprocess.CompletedProcess:
        with open(stdin, "rb") if stdin is not None else nullcontext(subprocess.DEVNULL) as stdin_file:
            return subprocess.run(
                [exe, *map(str, args)], stdin=stdin_file, capture_output=True, cwd=tmp_path
            )

    return run
