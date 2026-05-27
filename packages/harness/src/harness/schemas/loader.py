"""Schema registry loading Wave 0 contracts/schemas/*.json.

Per HARNESS_DESIGN.md §3 (READ + EVAL schema validation).
Eager loads all *.schema.json files into Draft202012Validator instances
at construction time so every harness operation can validate I/O cheaply.
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


class SchemaValidationError(Exception):
    """Wraps jsonschema ValidationError for harness-internal use.

    Includes the schema name + offending field path for debuggability.
    """


class SchemaRegistry:
    """Loads `contracts/schemas/*.schema.json` from a repo root.

    The base name (filename without `.schema.json`) is the schema name.
    Example: `harness-tailor-input.schema.json` → name `harness-tailor-input`.
    """

    def __init__(self, repo_root: Path):
        self._dir = repo_root / "contracts" / "schemas"
        if not self._dir.is_dir():
            raise SchemaValidationError(
                f"Schemas directory does not exist: {self._dir}"
            )
        self._cache: dict[str, Draft202012Validator] = {}
        self._load_all()

    def _load_all(self) -> None:
        for path in self._dir.glob("*.schema.json"):
            name = path.stem.removesuffix(".schema")
            schema = json.loads(path.read_text())
            # Validate the schema itself against the meta-schema before caching
            Draft202012Validator.check_schema(schema)
            self._cache[name] = Draft202012Validator(schema)

    def schema_names(self) -> list[str]:
        return sorted(self._cache.keys())

    def validate(self, name: str, data: dict) -> None:
        """Validate `data` against schema `name`.

        Raises SchemaValidationError on:
        - Unknown schema name
        - Validation failure (with the offending field path in the message)
        """
        validator = self._cache.get(name)
        if validator is None:
            raise SchemaValidationError(
                f"Unknown schema: {name!r}. Available: {self.schema_names()}"
            )
        try:
            validator.validate(data)
        except ValidationError as e:
            field_path = " → ".join(str(p) for p in e.absolute_path) or "<root>"
            raise SchemaValidationError(
                f"Schema {name!r} validation failed at {field_path}: {e.message}"
            ) from e
