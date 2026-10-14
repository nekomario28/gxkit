"""An environment / configuration declaration, as data.

    import envgx as e

    env = e.Environment(
        variables=[
            e.Variable("DATABASE_URL", required=True, secret=True),
            e.Variable("PORT", type="int", default="8080"),
        ],
        references=["DATABASE_URL", "PORT"],   # the names the code reads
    )

`references` is what the code actually reads; a name read but not declared, or a
name declared but never read, is configuration drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

TYPES = ("str", "int", "float", "bool")


@dataclass
class Variable:
    name: str
    type: str = "str"
    required: bool = False
    secret: bool = False
    default: str | None = None


@dataclass
class Environment:
    variables: list[Variable] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    name: str = "env"

    def names(self) -> list[str]:
        return [variable.name for variable in self.variables]


def _as_variable(value: object) -> Variable | None:
    if isinstance(value, Variable):
        return value
    if isinstance(value, str):
        return Variable(value)
    if isinstance(value, dict):
        name = value.get("name")
        if name is None:
            return None
        default = value.get("default")
        return Variable(
            str(name),
            type=str(value.get("type", "str")),
            required=bool(value.get("required", False)),
            secret=bool(value.get("secret", False)),
            default=str(default) if default is not None else None,
        )
    return None


def _as_environment(value: object) -> Environment | None:
    if isinstance(value, Environment):
        return value
    if isinstance(value, dict) and "variables" in value:
        variables = [_as_variable(item) for item in value["variables"]]
        if any(variable is None for variable in variables):
            return None
        return Environment(
            variables=[variable for variable in variables if variable is not None],
            references=[str(r) for r in value.get("references", [])],
            name=str(value.get("name", "env")),
        )
    if isinstance(value, (list, tuple)):
        built: list[Variable] = []
        for item in value:
            variable = _as_variable(item)
            if variable is None:
                return None
            built.append(variable)
        if built:
            return Environment(variables=built)
    return None


def _from_declaration(name: str, spec: object) -> Variable | None:
    if isinstance(spec, dict):
        return _as_variable({**spec, "name": name})
    if spec is None:
        return Variable(str(name))
    return _as_variable({"name": name, "type": str(spec)})


def load_environment(path: str | Path) -> tuple[Environment, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    env = resolve(
        module,
        attrs=("env", "environment", "ENV", "ENVIRONMENT", "config"),
        builders=("build", "make_env", "make"),
        convert=_as_environment,
    )
    if env is None:
        declaration = getattr(module, "VARIABLES", None)
        if declaration is not None:
            variables = [
                variable
                for variable in (_from_declaration(k, v) for k, v in dict(declaration).items())
                if variable is not None
            ]
            env = Environment(
                variables=variables,
                references=[str(r) for r in getattr(module, "REFERENCES", [])],
            )
    if env is None:
        raise ValueError(
            f"{path}: no environment found — define `env` (an Environment) or VARIABLES/REFERENCES"
        )
    env.name = getattr(module, "NAME", path.stem)
    return env, module


def environment_from_parts(
    variables: list[Variable] | None = None,
    references: list[str] | None = None,
    name: str = "env",
) -> Environment:
    return Environment(
        variables=list(variables or []),
        references=list(references or []),
        name=name,
    )
