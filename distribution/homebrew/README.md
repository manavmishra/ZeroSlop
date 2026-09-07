# Homebrew release preparation

The approved public tap is [manavmishra/homebrew-zero-slop](https://github.com/manavmishra/homebrew-zero-slop).
Install it with `brew install manavmishra/zero-slop/zero-slop`. This directory
contains its release helper; `zero-slop.rb.in` is a template, not an installable
formula. No placeholder checksum may be published.

[Formula/zero-slop.rb](Formula/zero-slop.rb) contains the candidate generated from
the published 2.10.0 tarball, with its verified SHA-256. The opt-in
`Homebrew release acceptance` workflow audits, installs and tests it in a
runner-local tap. That workflow does not create or publish a GitHub repository.

The tap's 2.10.0 release passed strict audit, source installation and functional
tests on macOS on September 7, 2026. Linux Homebrew has not been tested. Update
the public formula only after the new npm tarball passes the same acceptance.

## Generate after npm publication

```sh
node --test distribution/homebrew/prepare-formula.test.mjs
node distribution/homebrew/prepare-formula.mjs /tmp/zero-slop-candidate.rb
```

The helper reads only the exact published npm version, downloads its fixed
registry tarball URL, verifies npm's SHA-512 integrity, and calculates the real
SHA-256 for Homebrew. It refuses an unavailable release, changed package/version,
different tarball URL, missing integrity, mismatched bytes, or an existing output
file. It does not install or publish anything.

Review the generated formula and copy it into `Formula/zero-slop.rb` in the
approved tap repository after its installation tests pass. Do not overwrite an
existing candidate blindly; choose a new output path for each preparation.

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
