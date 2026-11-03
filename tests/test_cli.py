"""Tests for the heic2png command."""
import pytest


def test_file_and_stdin_give_the_same_png(heic2png, sample_heic, tmp_path):
    from_file = heic2png("-i", sample_heic, "-o", "from_file.png")
    from_stdin = heic2png(stdin=sample_heic)

    assert from_file.returncode == 0, from_file.stderr
    assert from_stdin.returncode == 0, from_stdin.stderr
    assert from_stdin.stdout == (tmp_path / "from_file.png").read_bytes()
    assert from_stdin.stderr == b""  # stream mode prints no messages


def test_lower_quality_gives_a_smaller_file(heic2png, sample_heic):
    default = heic2png(stdin=sample_heic)
    low = heic2png("--quality", 30, stdin=sample_heic)

    assert low.returncode == 0, low.stderr
    assert 0 < len(low.stdout) < len(default.stdout)


@pytest.mark.parametrize("args, message", [
    (["-i", "missing.heic", "-o", "out.png"], b"not found"),
    (["-i", "{sample}", "-o", "out.png", "--quality", "150"], b"quality"),
    (["-o", "out.png"], b"failed to open image"),  # stdin is empty
])
def test_errors_exit_non_zero(heic2png, sample_heic, tmp_path, args, message):
    result = heic2png(*[a.format(sample=sample_heic) for a in args])

    assert result.returncode != 0
    assert message in result.stderr.lower()
    assert not (tmp_path / "out.png").exists()
