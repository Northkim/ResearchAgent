# External Resources

Resources let a Project record an exact external repository, dataset, model, or
checkpoint without uploading its bytes to ReAgent Cloud.

The safe flow is:

1. Open the Reproduction & Experiment Workflow card.
2. Add credential-free reference metadata: kind, provider, locator, exact
   immutable revision, and expected SHA-256 checksum.
3. Bind that exact reference to an optional Workflow Resource requirement.
4. In the Local Workspace, inspect it with
   `python reagent_local.py resource list . --workflow reproduction-experiment-local-experimental`.
5. Resolve and verify it locally with the displayed exact Workflow selector.
6. Check drift with `python reagent_local.py resource status .`.

Adding or binding a Resource does not download anything. Cloud stores metadata
only, never provider tokens or Resource bytes, and cannot report local
verification. Resource selectors are separate from Artifact selectors:
Artifacts are outputs produced by Project Workflows; Resources originate
outside the Workflow graph.

GitHub and Hugging Face network resolution is not implemented in this scaffold
version. Their exact metadata can be recorded, but local resolve stops with
`RESOURCE_RESOLVER_NOT_IMPLEMENTED` and makes no network call. `LOCAL_TEST` is
available only to isolated controlled qualification and is not shown as an
ordinary production provider.

The Experiment Workflow remains a non-executing Scaffold even when Resources
are bound. No repository code, dataset, model, or checkpoint is executed, and
no real experimental result is produced.
