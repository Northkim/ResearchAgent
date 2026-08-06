# Project Workspace V0.1 Design Schemas

These JSON Schema 2020-12 documents are **design drafts only**. They are not
imported by runtime code, do not modify existing Package/Progress/API schemas,
and require a separate promotion decision before implementation.

Canonical serialization uses UTF-8 JSON, lexicographically sorted object keys,
no insignificant whitespace, Unicode strings as provided after schema
validation, and JSON integer representation for bounded counts/revisions.
Checksums use `sha256:` plus 64 lowercase hexadecimal characters. A document's
own checksum field is omitted when calculating that document checksum, so no
circular checksum exists. Arrays whose order is not semantically meaningful
must be sorted by their primary identity before serialization; schemas identify
the relevant identity in descriptions.

All object schemas reject unknown fields. Every Workspace file governed here is
secret-prohibited: credentials, bearer tokens, API keys, database URLs,
credential-bearing locators, and private absolute paths are outside the model.

`examples/valid` contains one fictional conforming document per schema;
`examples/invalid` contains one deliberately rejected document per schema.
Validation is offline and treats every invalid example as required-to-fail.

ARCH-D1 parsed all eight drafts and used the repository-installed Ajv 6 to
validate their draft-07-compatible keyword subset: all eight valid examples
passed and all eight invalid examples failed. The repository does not currently
contain a native draft-2020-12 meta-schema validator. Promotion to a runtime
contract therefore requires native 2020-12 validation in addition to these
design checks; ARCH-D1 did not download a new dependency.
