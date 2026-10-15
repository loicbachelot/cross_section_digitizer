"""Check a release tag and README against the plugin metadata before packaging."""

import argparse
import configparser
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag', help='Release tag, for example v1.1.0')
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    metadata = configparser.ConfigParser()
    metadata.read(root / 'metadata.txt')
    version = metadata['general']['version']
    expected_tag = f'v{version}'
    if args.tag != expected_tag:
        parser.exit(1, f'Release tag {args.tag!r} does not match metadata '
                    f'version {version!r}; expected {expected_tag!r}.\n')

    readme = (root / 'README.md').read_text(encoding='utf-8')
    match = re.search(r'The current version is (\d+\.\d+\.\d+)\.', readme)
    if match is None or match.group(1) != version:
        parser.exit(1, f'README current version must match metadata version {version!r}.\n')
    if f'`{expected_tag}`' not in readme or f'Version {version} supports QGIS' not in readme:
        parser.exit(1, f'Update README release tag and installation version to {version!r}.\n')

    print(f'Release tag and README match metadata version {version}.')


if __name__ == '__main__':
    main()
