"""Reviewed deterministic builder for the first ReAgent-prepared Experiment family."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .experiment_preparation_contracts import (
    BuilderFamily,
    ExperimentMethodology,
    ExperimentPreparationContractError,
)
from .security import reject_sensitive_content, require_relative_path
from .serialization import SerializableContract, canonical_hash, canonical_json, sha256_bytes

SPEC_SCHEMA = "reagent.sklearn-tabular-classification-spec/v0.1"
BUILDER_VERSION = "1.0.0"
DATASET = "SKLEARN_WINE"
ESTIMATOR = "KNEIGHBORS_CLASSIFIER"
CONDITIONS = ("RAW", "STANDARD_SCALER", "MINMAX_SCALER")
METRICS = ("accuracy", "macro_f1")
DEPENDENCIES = "numpy\nscikit-learn\n"


class AutomaticPreparationUnsupported(ExperimentPreparationContractError):
    """The requested methodology is outside the reviewed automatic family."""


@dataclass(frozen=True, slots=True)
class SklearnTabularClassificationSpec(SerializableContract):
    schema: str
    builder_family: BuilderFamily
    methodology_checksum: str
    dataset: str
    estimator: str
    conditions: tuple[str, ...]
    n_neighbors: int
    cv_splits: int
    cv_repeats: int
    cv_seed: int
    metrics: tuple[str, ...]
    robustness_neighbors: tuple[int, ...]
    result_schema: str
    specification_checksum: str

    def __post_init__(self) -> None:
        if self.schema != SPEC_SCHEMA:
            raise AutomaticPreparationUnsupported("AUTOMATIC_PREPARATION_UNSUPPORTED: specification schema")
        object.__setattr__(self, "builder_family", BuilderFamily(self.builder_family))
        object.__setattr__(self, "conditions", tuple(self.conditions))
        object.__setattr__(self, "metrics", tuple(self.metrics))
        object.__setattr__(self, "robustness_neighbors", tuple(self.robustness_neighbors))
        if (
            self.builder_family is not BuilderFamily.SKLEARN_TABULAR_CLASSIFICATION_V1
            or self.dataset != DATASET
            or self.estimator != ESTIMATOR
            or self.conditions != CONDITIONS
            or self.metrics != METRICS
            or self.result_schema != "reagent.experiment-result/v0.2"
            or not 1 <= self.n_neighbors <= 31
            or not 2 <= self.cv_splits <= 10
            or not 1 <= self.cv_repeats <= 20
            or not 0 <= self.cv_seed <= 2**31 - 1
            or not self.robustness_neighbors
            or len(self.robustness_neighbors) > 15
            or tuple(sorted(set(self.robustness_neighbors))) != self.robustness_neighbors
            or any(value < 1 or value > 31 for value in self.robustness_neighbors)
        ):
            raise AutomaticPreparationUnsupported("AUTOMATIC_PREPARATION_UNSUPPORTED: reviewed vocabulary")
        payload = self.to_dict()
        checksum = payload.pop("specification_checksum")
        if canonical_hash(payload) != checksum:
            raise ExperimentPreparationContractError("Implementation specification checksum mismatch")

    @classmethod
    def create(cls, **values: Any) -> "SklearnTabularClassificationSpec":
        values = {"schema": SPEC_SCHEMA, "builder_family": BuilderFamily.SKLEARN_TABULAR_CLASSIFICATION_V1, **values}
        return cls(**values, specification_checksum=canonical_hash(values))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SklearnTabularClassificationSpec":
        fields = set(cls.__dataclass_fields__)
        if not isinstance(value, Mapping) or set(value) != fields:
            raise AutomaticPreparationUnsupported("AUTOMATIC_PREPARATION_UNSUPPORTED: specification fields")
        return cls(**dict(value))

    def validate_methodology(self, methodology: ExperimentMethodology) -> None:
        if methodology.unresolved_methodological_decisions:
            raise ExperimentPreparationContractError("Unresolved methodology blocks implementation preparation")
        searchable = " ".join((methodology.dataset, *methodology.experiment_conditions, *methodology.evaluation_protocol, *methodology.metrics, *methodology.robustness_analysis, *methodology.leakage_controls)).casefold()
        required = ("wine", "knn", "standard", "minmax", "stratified", "accuracy", "macro", "neighbor", "fold")
        if self.methodology_checksum != methodology.methodology_checksum or any(term not in searchable for term in required):
            raise AutomaticPreparationUnsupported("AUTOMATIC_PREPARATION_UNSUPPORTED: methodology/specification mismatch")
        if self.cv_repeats != methodology.repetitions or self.cv_seed not in methodology.seeds:
            raise AutomaticPreparationUnsupported("AUTOMATIC_PREPARATION_UNSUPPORTED: CV scope differs from methodology")


ENTRYPOINT = r'''#!/usr/bin/env python3
import json, math, sys
from pathlib import Path
from sklearn.datasets import load_wine
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, StandardScaler

config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
X, y = load_wine(return_X_y=True)
cv = RepeatedStratifiedKFold(n_splits=config["cv_splits"], n_repeats=config["cv_repeats"], random_state=config["cv_seed"])

def evaluate(condition, neighbors):
    scores = {"accuracy": [], "macro_f1": []}
    for train, test in cv.split(X, y):
        estimator = KNeighborsClassifier(n_neighbors=neighbors)
        if condition == "STANDARD_SCALER": estimator = Pipeline([("scale", StandardScaler()), ("knn", estimator)])
        elif condition == "MINMAX_SCALER": estimator = Pipeline([("scale", MinMaxScaler()), ("knn", estimator)])
        estimator.fit(X[train], y[train])
        predicted = estimator.predict(X[test])
        scores["accuracy"].append(accuracy_score(y[test], predicted))
        scores["macro_f1"].append(f1_score(y[test], predicted, average="macro"))
    return {name: sum(values) / len(values) for name, values in scores.items()}

conditions = [{"condition": name, "n_neighbors": config["n_neighbors"], "metrics": evaluate(name, config["n_neighbors"])} for name in config["conditions"]]
robustness = [{"condition": name, "n_neighbors": value, "metrics": evaluate(name, value)} for value in config["robustness_neighbors"] for name in config["conditions"]]
result = {"schema_version": "reagent.experiment-result/v0.2", "conditions": conditions, "robustness": robustness}
if not all(math.isfinite(metric) for row in conditions + robustness for metric in row["metrics"].values()): raise RuntimeError("non-finite metric")
print(json.dumps(result, sort_keys=True, separators=(",", ":")))
'''


def rendered_files(spec: SklearnTabularClassificationSpec, runtime_version: str) -> dict[str, bytes]:
    config = {
        "schema": "reagent.sklearn-tabular-classification-config/v0.1",
        "conditions": list(spec.conditions), "n_neighbors": spec.n_neighbors,
        "cv_splits": spec.cv_splits, "cv_repeats": spec.cv_repeats,
        "cv_seed": spec.cv_seed, "metrics": list(spec.metrics),
        "robustness_neighbors": list(spec.robustness_neighbors),
    }
    manifest = {
        "schema_version": "reagent.experiment-package/v0.1",
        "entrypoint": "run_experiment.py", "runtime": "PYTHON",
        "runtime_version": runtime_version, "lock_file": "requirements.lock",
    }
    expected = {
        "schema": "reagent.experiment-result-expectation/v0.1",
        "conditions": list(spec.conditions), "metrics": list(spec.metrics),
        "robustness_neighbors": list(spec.robustness_neighbors),
    }
    return {
        ".reagent-experiment.json": (canonical_json(manifest) + "\n").encode(),
        "run_experiment.py": ENTRYPOINT.encode(),
        "requirements.lock": DEPENDENCIES.encode(),
        "experiment-config.json": (canonical_json(config) + "\n").encode(),
        "result-expectations.json": (canonical_json(expected) + "\n").encode(),
    }


def render_candidate(root: Path, spec: SklearnTabularClassificationSpec, runtime_version: str) -> None:
    if root.exists() or root.is_symlink():
        raise ExperimentPreparationContractError("Candidate preparation directory already exists")
    root.mkdir(parents=True)
    for relative, content in rendered_files(spec, runtime_version).items():
        require_relative_path(relative)
        reject_sensitive_content(content, path=relative)
        path = root / relative
        path.write_bytes(content)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def package_tree(root: Path) -> tuple[str, list[dict[str, Any]]]:
    if root.is_symlink() or not root.is_dir():
        raise ExperimentPreparationContractError("Experiment Package root is unsafe")
    entries: list[dict[str, Any]] = []
    folded: set[str] = set()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        require_relative_path(relative)
        if relative.casefold() in folded:
            raise ExperimentPreparationContractError("Experiment Package contains a case collision")
        folded.add(relative.casefold())
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode) or path.stat().st_nlink != 1:
            raise ExperimentPreparationContractError("Experiment Package contains a link, directory, or special file")
        content = path.read_bytes()
        reject_sensitive_content(content, path=relative)
        entries.append({"path": relative, "sha256": sha256_bytes(content), "size_bytes": len(content)})
    return canonical_hash(entries), entries
