"""Copy a Vite build next to this server. Run after npm run build."""
import argparse
import shutil
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', type=Path,
                        help='Path to easound/dist (optional with standard sibling folders)')
    args = parser.parse_args()
    if args.source:
        source = args.source.resolve()
    else:
        candidates = [root.parent / name / 'dist' for name in ('easound', 'easound-main')]
        available = [path for path in candidates if (path / 'index.html').is_file()]
        if len(available) != 1:
            parser.error('Build easound first, or specify the exact dist directory')
        source = available[0]
    if not (source / 'index.html').is_file() or not (source / 'assets').is_dir():
        parser.error('Source must be a Vite dist directory with index.html and assets/')
    destination = root / 'frontend'
    if source == destination or destination in source.parents or source in destination.parents:
        parser.error('Source and frontend destination must be separate directories')
    # Overlay rather than delete: older hashed assets remain usable by open tabs.
    shutil.copytree(source, destination, dirs_exist_ok=True)
    print('Copied {} to {}'.format(source, destination))


if __name__ == '__main__':
    main()
