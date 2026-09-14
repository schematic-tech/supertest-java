#!/usr/bin/env python3
"""Exercise signing and deployment against a loopback-only Central API fixture."""
from __future__ import annotations

import argparse
from email.parser import BytesParser
from email.policy import default
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from urllib.parse import parse_qs, urlsplit
import zipfile

from release import ROOT, VERSION, validate


DEPLOYMENT = '00000000-0000-0000-0000-000000000001'
uploads: list[bytes] = []
statuses: list[str] = []


class CentralFixture(BaseHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        pass

    def do_POST(self) -> None:
        path = urlsplit(self.path)
        query = parse_qs(path.query)
        body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        if path.path == '/api/v1/publisher/upload' and query.get('publishingType') == ['AUTOMATIC']:
            message = BytesParser(policy=default).parsebytes(
                ('Content-Type: ' + self.headers['Content-Type'] + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + body)
            parts = [part for part in message.iter_parts() if part.get_param('name', header='content-disposition') == 'bundle']
            if len(parts) != 1:
                self.send_error(400, 'Expected one bundle')
                return
            uploads.append(parts[0].get_payload(decode=True))
            self.respond(201, DEPLOYMENT.encode(), 'text/plain')
        elif path.path == '/api/v1/publisher/status' and query.get('id') == [DEPLOYMENT]:
            statuses.append(DEPLOYMENT)
            self.respond(200, json.dumps({'deploymentId': DEPLOYMENT, 'deploymentName': 'CI test',
                                         'deploymentState': 'PUBLISHED', 'purls': []}).encode(), 'application/json')
        else:
            self.send_error(400, 'Unexpected Central request')

    def respond(self, code: int, data: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--unprotected', action='store_true', help='Exercise a signing key with no passphrase')
args = parser.parse_args()
validate()
with tempfile.TemporaryDirectory(prefix='supertest-java-signing-') as directory:
    key_home = Path(directory) / 'gnupg'
    key_home.mkdir(mode=0o700)
    environment = dict(os.environ, GNUPGHOME=str(key_home),
                       MAVEN_GPG_PASSPHRASE='' if args.unprotected else 'temporary-test-key')
    gpg = ['gpg', '--batch', '--pinentry-mode', 'loopback', '--passphrase', environment['MAVEN_GPG_PASSPHRASE']]
    subprocess.run([*gpg, '--quick-generate-key', 'Supertest disposable CI key <ci@example.invalid>',
                    'rsa2048', 'sign', '1d'], env=environment, check=True, capture_output=True)
    environment['MAVEN_GPG_KEY'] = subprocess.check_output(
        [*gpg, '--armor', '--export-secret-keys'], env=environment, text=True)
    settings = Path(directory) / 'settings.xml'
    settings.write_text('<settings><servers><server><id>central</id>'
                        '<username>unused</username><password>unused</password>'
                        '</server></servers></settings>')
    wrapper = ROOT / ('mvnw.cmd' if os.name == 'nt' else 'mvnw')
    server = ThreadingHTTPServer(('127.0.0.1', 0), CentralFixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # Only the loopback fixture receives this disposable-key deployment.
        # skipPublishing is unsuitable here: plugin 0.11.0 skips bundle creation.
        subprocess.run([str(wrapper), '-B', '-ntp', '--settings', str(settings), '-Prelease',
                        f'-Dcentral.baseUrl=http://127.0.0.1:{server.server_port}',
                        '-Dmaven.install.skip=true', 'clean', 'deploy'],
                       cwd=ROOT, env=environment, check=True, timeout=300)
        bundle = ROOT / 'target/central-publishing/central-bundle.zip'
        assert uploads == [bundle.read_bytes()], 'Expected exactly one complete bundle upload'
        assert statuses, 'Plugin must wait for publication status'
        prefix = f'tech/schematic/supertest/schematic-supertest/{VERSION}/schematic-supertest-{VERSION}'
        with zipfile.ZipFile(bundle) as archive:
            for suffix in ('.jar', '-sources.jar', '-javadoc.jar', '.pom'):
                name = prefix + suffix
                data = archive.read(name)
                signature = archive.read(name + '.asc')
                assert hashlib.sha256(data).hexdigest() == archive.read(name + '.sha256').decode().strip()
                assert hashlib.sha512(data).hexdigest() == archive.read(name + '.sha512').decode().strip()
                artifact = Path(directory) / Path(name).name
                artifact.write_bytes(data)
                asc = artifact.with_name(artifact.name + '.asc')
                asc.write_bytes(signature)
                subprocess.run(['gpg', '--batch', '--verify', str(asc), str(artifact)], env=environment,
                               check=True, capture_output=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        subprocess.run(['gpgconf', '--kill', 'gpg-agent'], env=environment, check=True)
print('Signed Central bundle, signatures, checksums, automatic upload and status polling passed against localhost')
