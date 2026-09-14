#!/usr/bin/env python3
"""Sign and deploy to Maven Central from the matching public version tag."""
from __future__ import annotations

import os
import shutil
import urllib.error
import urllib.request

from package import collect, maven
from release import ROOT, VERSION, build_assets, require_public_tag, verify_assets


def main() -> None:
    require_public_tag()
    verify_assets()
    # Unencrypted OpenPGP keys have no passphrase. The signer handles protected
    # keys and reports missing/incorrect passphrases when one is required.
    for name in ('CENTRAL_USERNAME', 'CENTRAL_PASSWORD', 'MAVEN_GPG_KEY'):
        if not os.environ.get(name):
            raise SystemExit(f'Set the {name} secret in the release environment')
    stem = f'schematic-supertest-{VERSION}'
    url = f'https://repo.maven.apache.org/maven2/tech/schematic/supertest/schematic-supertest/{VERSION}/{stem}.jar'
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            published = response.read()
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        published = None
    if published is not None:
        if published != (ROOT / 'dist' / (stem + '.jar')).read_bytes():
            raise SystemExit('This version already exists on Maven Central with different JAR bytes; release a new version')
        for suffix in ('.jar', '-sources.jar', '-javadoc.jar', '.pom'):
            name = stem + suffix
            artifact_url = url.rsplit('/', 1)[0] + '/' + name
            if suffix != '.jar':
                with urllib.request.urlopen(artifact_url, timeout=60) as response:
                    if response.read() != (ROOT / 'dist' / name).read_bytes():
                        raise SystemExit(f'Maven Central has different {name} bytes; release a new version')
            with urllib.request.urlopen(artifact_url + '.asc', timeout=60) as response:
                (ROOT / 'dist' / (name + '.asc')).write_bytes(response.read())
        build_assets()
        print('Matching version is already on Maven Central; keeping it unchanged')
        return
    # A standard deploy executes tests again in the signing job. Central validates
    # the signed bundle, publishes automatically, and blocks until publication.
    maven('clean', '-Prelease', 'deploy')
    shutil.rmtree(ROOT / 'dist')
    collect()
    build_assets()
    verify_assets()


if __name__ == '__main__':
    main()
