"""
Optimize icons.
copyright 2024 by Frank David Martinez M.
license: CCO-1.0
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

OPTIMIZER_AVAILABLE = True
try:
    import scour

    print(f"Optimization is available: scour-{scour.__version__}")
except ImportError:
    OPTIMIZER_AVAILABLE = False
    print("Optimization is disabled. Consider installing scour", file=sys.stderr)


def optimize(icons_dir: Path, out_dir: Path) -> None:
    """Write an optimized copy of every icon into out_dir."""
    from scour import scour

    for icon in icons_dir.glob("*.svg"):
        with icon.open(encoding="utf-8") as fin:
            optimized = scour.scourString(fin.read())
        (out_dir / icon.name).write_text(optimized, encoding="utf-8")


def main(optimized: bool = True) -> None:
    icons_dir = Path(__file__).parent / "icons"
    if not optimized:
        print("Optimization is disabled")
        return

    # Optimize into a temp dir first, so a failure cannot leave broken icons behind.
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        optimize(icons_dir, out_dir)
        for icon in out_dir.glob("*.svg"):
            shutil.copy2(icon, icons_dir / icon.name)

    print(f"Optimized {len(list(icons_dir.glob('*.svg')))} icons in {icons_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize the addon icons in place")
    parser.add_argument(
        "--no-opt",
        help="Disables optimization",
        default=False,
        action="store_true",
    )

    args = parser.parse_args()
    main(OPTIMIZER_AVAILABLE and (not args.no_opt))
