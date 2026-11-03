"""Regression tests for behaviour that broke between 1.1.x and 1.2.0."""
from heic2png.cli import setup_parser


def test_short_q_sets_quality():
    # 1.1.x and the README use `-q 90` for quality; 1.2.0 had turned -q into --quiet.
    args = setup_parser().parse_args(["-i", "photo.heic", "-q", "90"])
    assert args.quality == 90
    assert args.quiet is False


def test_quiet_is_still_available_as_long_option():
    args = setup_parser().parse_args(["-i", "photo.heic", "--quiet"])
    assert args.quiet is True
    assert args.quality == 80  # default unchanged (user decision, 2026-11-03)
