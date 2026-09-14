#!/usr/bin/env python3
"""Validate release metadata, build source assets, and manage GitHub releases."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'release.json').read_text())
VERSION = (ROOT / 'VERSION').read_text().strip()


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def validate(tag: str | None = None) -> None:
    if not re.fullmatch(r'\d+\.\d+\.\d+', VERSION):
        raise SystemExit('VERSION must be a stable major.minor.patch release')
    if tag is not None and tag != f'v{VERSION}':
        raise SystemExit(f'Tag {tag!r} does not match VERSION v{VERSION}')
    for name in ('LICENSE-MIT', 'LICENSE-APACHE'):
        if not (ROOT / name).is_file():
            raise SystemExit(f'Missing {name}')
    language = CONFIG['language']
    if CONFIG['repository'] != f'schematic-tech/supertest-{language}':
        raise SystemExit('Release repository must be the matching schematic-tech repository')
    assert language == 'java'
    project = ET.parse(ROOT / 'pom.xml')
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
    assert project.findtext('m:groupId', namespaces=ns) == 'tech.schematic.supertest'
    assert project.findtext('m:artifactId', namespaces=ns) == 'schematic-supertest'
    assert project.findtext('m:version', namespaces=ns) == VERSION
    assert project.findtext('m:scm/m:tag', namespaces=ns) == f'v{VERSION}'
    assert len(project.findall('m:licenses/m:license', ns)) == 2
    for license in project.findall('m:licenses/m:license', ns):
        assert 'MIT OR Apache-2.0' in license.findtext('m:comments', namespaces=ns)
    print(f'{CONFIG["repository"]}: metadata agrees with v{VERSION}')


def require_public_tag() -> None:
    validate(os.environ.get('GITHUB_REF_NAME', ''))
    if os.environ.get('GITHUB_REPOSITORY') != CONFIG['repository'] or os.environ.get('GITHUB_REF_TYPE') != 'tag':
        raise SystemExit('Publishing is only allowed from a version tag in the matching public repository')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        raise SystemExit('Publishing requires a clean checkout')


def archive_files(paths: list[Path], prefix: str, tar_path: Path, zip_path: Path) -> None:
    # Stable metadata makes rebuilds of the same commit reproducible.
    epoch = int(subprocess.check_output(['git', 'log', '-1', '--format=%ct'], cwd=ROOT))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as archive:
        for path in paths:
            data = path.read_bytes()
            info = tarfile.TarInfo(prefix + path.relative_to(ROOT).as_posix())
            info.size = len(data)
            info.mtime = epoch
            info.mode = 0o755 if os.access(path, os.X_OK) else 0o644
            archive.addfile(info, io.BytesIO(data))
    tar_path.write_bytes(gzip.compress(buffer.getvalue(), mtime=0))
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            info = zipfile.ZipInfo(prefix + path.relative_to(ROOT).as_posix())
            info.external_attr = (0o755 if os.access(path, os.X_OK) else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def build_assets() -> None:
    validate()
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = [ROOT / name for name in sorted(tracked) if name and (ROOT / name).is_file()]
    # The checkout directory may have a different name on CI or after extraction.
    stem = f'{CONFIG["repository"].split("/")[1]}-{VERSION}'
    source_tar = output / f'{stem}.tar.gz'
    archive_files(paths, f'{stem}/', source_tar, output / f'{stem}.zip')
    for filename in ('LICENSE-MIT', 'LICENSE-APACHE'):
        shutil.copyfile(ROOT / filename, output / filename)
    checksum = output / 'SHA256SUMS'
    files = sorted(path for path in output.iterdir() if path.is_file() and path != checksum)
    checksum.write_text(''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n' for path in files))
    print(f'Built {len(files)} release assets and SHA256SUMS')


def verify_assets() -> None:
    output = ROOT / 'dist'
    for line in (output / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert Path(name).name == name
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest, name


def github_release() -> None:
    require_public_tag()
    verify_assets()
    repo = CONFIG['repository']
    tag = f'v{VERSION}'
    view = subprocess.run(['gh', 'release', 'view', tag, '--repo', repo, '--json', 'isDraft'],
                          cwd=ROOT, capture_output=True, text=True)
    if view.returncode == 0 and not json.loads(view.stdout)['isDraft']:
        # A retry after registry publication must not replace published assets.
        print(f'{tag} is already published on GitHub; keeping its assets unchanged')
        return
    if view.returncode != 0:
        run('gh', 'release', 'create', tag, '--repo', repo, '--verify-tag', '--draft',
            '--title', tag, '--generate-notes')
    assets = [str(path) for path in sorted((ROOT / 'dist').iterdir()) if path.is_file()]
    run('gh', 'release', 'upload', tag, '--repo', repo, '--clobber', *assets)
    run('gh', 'release', 'edit', tag, '--repo', repo, '--draft=false')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'guard', 'assets', 'verify-assets', 'github'])
    parser.add_argument('--tag')
    args = parser.parse_args()
    if args.command == 'check':
        validate(args.tag)
    elif args.command == 'guard':
        require_public_tag()
    elif args.command == 'assets':
        build_assets()
    elif args.command == 'verify-assets':
        verify_assets()
    elif args.command == 'github':
        github_release()


if __name__ == '__main__':
    main()
