# Skills bundled with Workflows

Skills are reviewed operating instructions that a Workflow uses locally. You do
not download, copy, choose, or edit them separately. A Workflow version pins
exact Skill versions, and `python reagent_local.py sync .` installs them inside
the verified Capsule.

The Workflow Board shows the bundled Skill name, exact version, and
**Built-in reviewed** trust. Writing, Review, and Reproduction & Experiment
0.2.0 currently include:

- Research Artifact Provenance 0.1.0
- Scaffold Core Safety 0.1.0

These Skills preserve exact input provenance and prevent fabricated scientific
claims. They do not make the scaffold research core complete: Writing, Review,
and Experiment remain clearly marked Prototype/Scaffold Workflows.

If local Skill content is missing or changed, run/preflight stops. Preserve
research state and use the documented verified-Capsule recovery before syncing;
do not edit `skill.json` or copy Skill files by hand. Skill files are immutable capability inputs, while `memory/`, `outputs/`,
and Progress remain the mutable per-Workflow state.

ReAgent currently accepts only repository-maintained declarative built-in Skills.
User upload, remote import, executable Skills, marketplace installation, and
browser admin mutation are not available.
