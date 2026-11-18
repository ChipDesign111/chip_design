"""Write small representative NumPy inputs outside the tracked model sources."""
import argparse
from pathlib import Path
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('test/int8/runs/raw_frontend_demo'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    x = np.linspace(-1, 1, 65, dtype=np.float32).reshape(1, 65)
    np.save(args.out/'input.npy', x)
    np.save(args.out/'calibration.npy', np.stack([-x, x*0.5]))
    np.save(args.out/'held_out.npy', x*0.75-0.125)
    print(args.out)


if __name__ == '__main__':
    main()
