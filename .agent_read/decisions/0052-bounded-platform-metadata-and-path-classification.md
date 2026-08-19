# 0052: Bound managed platform metadata and classify private paths separately

- Status: Accepted
- Date: 2026-08-20

## Context

The real D1 Workspace was blocked by a macOS `.DS_Store` inside an installed
managed Capsule. A separate Generic Harness operator file containing an absolute
local path was rejected and described as prohibited credential material even
though no credential was present. Arbitrary undeclared Capsule files and actual
secrets must still fail closed, and immutable published Capsule validator bytes
cannot be rewritten in place.

## Decision

The Workspace coordinator recognizes only a bounded regular `.DS_Store` file of
at most 1 MiB as benign platform metadata. For a ReAgent-installed managed
Capsule it may remove that file before invoking the immutable embedded validator;
the source package is never changed. Symlinks, hardlinks, oversized metadata,
and every other undeclared file remain invalid.

Credential patterns and absolute private-path patterns are separate validation
classes. Actual credentials retain the existing fail-closed credential error.
Private local path metadata receives `LEGACY_PACKAGE_PRIVATE_PATH` and is never
described as an actual credential. Exact materialized scientific inputs retain
their narrower credential-only scan because valid Local Artifact content may
truthfully contain paths.

## Consequences

Normal macOS metadata no longer makes a managed Capsule unusable. Unknown files
and actual secrets remain rejected. Future Generic Harness work still requires
the R3 managed execution namespace; this decision does not authorize mutable
operator state inside immutable Capsule memory.

## Alternatives considered

- Editing historical embedded validators was rejected because published Capsule
  bytes are immutable.
- Ignoring all dotfiles or undeclared files was rejected because it weakens
  package integrity.
- Continuing to call all private paths credentials was rejected because the
  diagnosis is false and obscures the distinct privacy boundary.
