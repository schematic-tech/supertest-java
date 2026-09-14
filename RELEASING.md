# Releasing Java

Prepared version: **0.1.0**, licensed **MIT OR Apache-2.0** at the user's option.
Public repository: `schematic-tech/supertest-java`.
Maven coordinates: `tech.schematic.supertest:schematic-supertest:0.1.0`.

## One-time setup

1. Create the public repository from a reviewed squash snapshot, including `.github`
   and `.mvn`, without copying private Git history. Enable Actions. Create a GitHub
   environment named **`release`**, allowing version tags; leave required reviewers
   unset if publishing should proceed automatically after a tag push.
2. Sign in to the [Sonatype Central Portal](https://central.sonatype.com). Request
   namespace **`tech.schematic`**. Add its assigned verification key as a DNS TXT
   record at **`schematic.tech`**. Check that the TXT record resolves, then request
   verification in the portal. Ownership of this parent namespace authorizes the
   subgroup `tech.schematic.supertest` used by this artifact.
3. Generate a **Central Portal user token** for an account authorized to publish
   in that namespace. Save the token's generated username and password as GitHub
   environment secrets **`CENTRAL_USERNAME`** and **`CENTRAL_PASSWORD`**. These are
   token credentials, not your website login/password. This workflow uses the
   current Central Portal plugin, not an old OSSRH server.
4. Choose or generate an OpenPGP signing key. Publish its public
   key to a Sonatype-supported keyserver. Put its ASCII-armored secret-key export
   in the environment secret **`MAVEN_GPG_KEY`**, and its passphrase in
   **`MAVEN_GPG_PASSPHRASE`** (leave this empty for an unprotected key). Export exactly the intended signing key. The Maven
   GPG plugin reads these environment variables directly using its Java signer.

The GitHub CLI prompts securely for these three text secrets:

```sh
gh secret set CENTRAL_USERNAME --repo schematic-tech/supertest-java --env release
gh secret set CENTRAL_PASSWORD --repo schematic-tech/supertest-java --env release
gh secret set MAVEN_GPG_PASSPHRASE --repo schematic-tech/supertest-java --env release
```

To create a dedicated signing key, run `gpg --full-generate-key`, choose RSA with
signing capability, and set your release identity, expiration and passphrase.
Find its full fingerprint with `gpg --list-secret-keys --keyid-format long`.
Substitute it below. Keep the key/passphrase in your own secure backup and renew
the key before it expires.

```sh
release_key_fingerprint='REPLACE_WITH_FULL_SIGNING_KEY_FINGERPRINT'
gpg --keyserver hkps://keyserver.ubuntu.com --send-keys "$release_key_fingerprint"
gpg --armor --export-secret-keys "$release_key_fingerprint" |
  gh secret set MAVEN_GPG_KEY --repo schematic-tech/supertest-java --env release
```

No personal GitHub token is needed in the workflow. GitHub release uploads use
the built-in `GITHUB_TOKEN`. Maven Central currently uses the Portal token and
PGP key configured above in this pipeline.

## Publish

After the public snapshot's CI passes, from its clean checkout:

```sh
python3 scripts/release.py check --tag v0.1.0
git tag -a v0.1.0 -m 'Release 0.1.0'
git push origin v0.1.0
```

The tag workflow calls all CI jobs, including Java 8/25 and Windows consumers and
a disposable-key signing check. The publish job validates the public repo/tag and
artifact checksums, then runs the Maven release profile. That profile rebuilds and
tests, signs the main JAR, sources JAR, Javadoc JAR and POM, generates a checksummed
Central bundle, uploads it, and waits for automatic publication. It then uploads
the Java artifacts, signatures, bundle, source archives, licenses and `SHA256SUMS`
to a GitHub Release.

Local validation that **does not publish to any public service**:

```sh
python3 scripts/package.py
python3 scripts/test_signing.py
```

The latter uses a temporary key and overrides the Central URL with a localhost
API fixture. It verifies the actual bundle, signatures, checksums, automatic upload
and publication-status polling. The plugin's `skipPublishing` option skips staging
in version 0.11.0, so it cannot exercise bundle creation. Do not upload artifacts
carrying that disposable test signature. Ordinary CI
release assets are built separately from the signing-test job.

## Subsequent versions and retries

Update `VERSION`, `pom.xml`'s project version and SCM tag, and examples. Commit the
reviewed public squash update and tag it. Maven artifacts use reproducible ZIP
timestamps; Java release builds use JDK 17. A complete workflow rerun after toolchain
updates can produce different Javadoc, so prefer rerunning only failed jobs.

If credentials or a transient service error stop a release, correct the external
setting and rerun the failed job for the same tag. If Central already has the
version, the script compares all four artifact files to the CI artifacts, obtains
the published signatures, and continues the GitHub release without overwriting
Central. If they differ, use a new version. If Central accepted an upload before
the workflow timed out, inspect its deployment status before rerunning; complete
or drop a pending deployment in the portal as appropriate. Published GitHub assets
are also retained unchanged. The original Central upload bundle is available as a
GitHub asset when the deployment succeeds in that run; recovery from an already
published Central version includes its individual artifacts and signatures.

References: [namespace verification](https://central.sonatype.org/register/namespace/),
[Portal tokens](https://central.sonatype.org/publish/generate-portal-token/),
[Maven publishing plugin](https://central.sonatype.org/publish/publish-portal-maven/),
[PGP requirements](https://central.sonatype.org/publish/requirements/gpg/),
[Maven signing configuration](https://maven.apache.org/plugins/maven-gpg-plugin/sign-mojo.html).
