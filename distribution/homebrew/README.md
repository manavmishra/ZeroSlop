# Homebrew preparation for 2.10.0

This directory is not a published tap. `zero-slop.rb.in` is a release template,
not an installable formula. No placeholder checksum may be published.

[Formula/zero-slop.rb](Formula/zero-slop.rb) contains the candidate generated from
the published 2.10.0 tarball, with its verified SHA-256. The opt-in
`Homebrew release acceptance` workflow audits, installs and tests it in a
runner-local tap. That workflow does not create or publish a GitHub repository.

On 2026-09-07, the authenticated owner-repository listing and the paginated public
GitHub listing found no `manavmishra` repository with `homebrew` or `tap` in its
name. Homebrew was absent from PATH, `/opt/homebrew/bin/brew`, and
`/usr/local/bin/brew`. No external repository was created.

## Generate after npm publication

```sh
node --test distribution/homebrew/prepare-formula.test.mjs
node distribution/homebrew/prepare-formula.mjs distribution/homebrew/Formula/zero-slop.rb
```

The helper reads only the exact published npm version, downloads its fixed
registry tarball URL, verifies npm's SHA-512 integrity, and calculates the real
SHA-256 for Homebrew. It refuses an unavailable release, changed package/version,
different tarball URL, missing integrity, mismatched bytes, or an existing output
file. It does not install or publish anything.

Review the generated formula and copy it into `Formula/zero-slop.rb` in the
approved tap repository. A tap name and external publication still need approval.
Do not advertise a working Homebrew install command before that tap is live.

## Validate with Homebrew before publishing the tap

From a machine with Homebrew, add the local tap checkout using the chosen tap
name, then run `brew audit --strict`, `brew install --build-from-source`, and
`brew test` for that formula. The embedded functional test checks the installed
version, JSON scoring, and skill installation into Homebrew's temporary test
directory. It does not write to a real user's assistant configuration.

The formula declares Node and Python, installs npm files under its own prefix,
uses Homebrew's default disabled npm lifecycle scripts, and wraps the executable
so its declared interpreters are available. The package needs no npm dependencies.
Local preparation tests do not substitute for a successful Homebrew installation.

## Official references

- [Node formula guidance](https://docs.brew.sh/Language-Specific-Formulae#nodejs)
- [Formula tests and audit](https://docs.brew.sh/Formula-Cookbook)
- [Creating and maintaining a tap](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap)
- [Python 3.14 formula](https://formulae.brew.sh/formula/python@3.14)
