from __future__ import annotations

import argparse

from piper_app.cli.click_pick_demo import build_parser as build_click_pick_parser
from piper_app.yolo_target_pick_demo.gui import run


def build_parser() -> argparse.ArgumentParser:
    parser = build_click_pick_parser()
    parser.description = (
        "YOLO label-driven tabletop pick demo for Piper using D405 depth and hand-eye calibration."
    )
    parser.set_defaults(yolo=True)
    parser.add_argument(
        "--target-label",
        type=str,
        default="",
        help="Optional initial target object class name.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.yolo = True
    run(args)


if __name__ == "__main__":
    main()
