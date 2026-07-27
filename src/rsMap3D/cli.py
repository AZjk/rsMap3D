"""
Copyright (c) 2026, UChicago Argonne, LLC
See LICENSE file.
"""

import argparse
import json


def _load_config(config_path):
    with open(config_path) as config_file:
        return json.load(config_file)


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="rsMap3D",
        description="rsMap3D: map x-ray scattering images into reciprocal space.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("gui", help="Launch the rsMap3D GUI (default).")

    angle_scan_parser = subparsers.add_parser(
        "map-angle-scan",
        help="Grid a spec angle scan into a reciprocal space map (Sector 33).",
    )
    angle_scan_parser.add_argument("config_path", help="Path to an rsmconfig.json file.")

    parametric_scan_parser = subparsers.add_parser(
        "map-parametric-scan",
        help="Grid a parametric scan, one output file per image in the scan (Sector 33).",
    )
    parametric_scan_parser.add_argument("config_path", help="Path to a parametric scan config JSON file.")

    powder_scan_parser = subparsers.add_parser(
        "powder-scan",
        help="Reduce spec scans into 1D powder-diffraction curves (Sector 33).",
    )
    powder_scan_parser.add_argument("config_path", help="Path to a powder scan config JSON file.")

    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "gui"):
        from rsMap3D.rsmEdit import main as gui_main

        gui_main()
    elif args.command == "map-angle-scan":
        from rsMap3D.workflows import angle_scan

        angle_scan.run(_load_config(args.config_path))
    elif args.command == "map-parametric-scan":
        from rsMap3D.workflows import parametric_scan

        parametric_scan.run(_load_config(args.config_path))
    elif args.command == "powder-scan":
        from rsMap3D.workflows import powder_scan

        powder_scan.run(_load_config(args.config_path))


if __name__ == "__main__":
    main()
