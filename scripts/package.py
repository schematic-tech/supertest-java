#!/usr/bin/env python3
"""Build and inspect the Maven artifacts without publishing."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

from release import ROOT, VERSION, validate


def maven(*args: str) -> None:
    wrapper = ROOT / ('mvnw.cmd' if os.name == 'nt' else 'mvnw')
    subprocess.run([str(wrapper), '--batch-mode', '--no-transfer-progress', *args], cwd=ROOT, check=True)


def collect() -> None:
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    stem = f'schematic-supertest-{VERSION}'
    for suffix in ('.jar', '-sources.jar', '-javadoc.jar'):
        source = ROOT / 'target' / (stem + suffix)
        with zipfile.ZipFile(source) as archive:
            for name in ('LICENSE-MIT', 'LICENSE-APACHE'):
                prefix = 'resources' if suffix == '-javadoc.jar' else 'META-INF'
                assert archive.read(f'{prefix}/{name}') == (ROOT / name).read_bytes()
            if suffix == '.jar':
                for name in archive.namelist():
                    if name.endswith('.class'):
                        assert int.from_bytes(archive.read(name)[6:8], 'big') == 52, name
                assert b'Automatic-Module-Name: tech.schematic.supertest' in archive.read('META-INF/MANIFEST.MF')
        shutil.copyfile(source, output / source.name)
    shutil.copyfile(ROOT / 'pom.xml', output / (stem + '.pom'))
    # Maven GPG writes signatures next to the corresponding target artifacts.
    for path in (ROOT / 'target').glob('*.asc'):
        shutil.copyfile(path, output / path.name)
    bundle = ROOT / 'target/central-publishing/central-bundle.zip'
    if bundle.is_file():
        shutil.copyfile(bundle, output / f'schematic-supertest-maven-central-{VERSION}.zip')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect-only', action='store_true')
    args = parser.parse_args()
    validate()
    if not args.collect_only:
        shutil.rmtree(ROOT / 'dist', ignore_errors=True)
        maven('clean', 'verify')
    collect()
    subprocess.run([os.sys.executable, 'scripts/test_consumer.py'], cwd=ROOT, check=True)
    print('Java artifacts, licenses, Java 8 bytecode, and standalone consumer passed')


if __name__ == '__main__':
    main()
