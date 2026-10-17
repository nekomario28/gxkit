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

from gxcore.loading import convert_bool, convert_items, convert_mapping, convert_names

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
            required=convert_bool(value.get("required", False), field="required"),
            # `bool("no")` is True: a string where a flag belongs made the tool report
            # the opposite of the declaration (`secret = "no"` produced a
            # `secret-with-default` error).
            secret=convert_bool(value.get("secret", False), field="secret"),
            default=str(default) if default is not None else None,
        )
    return None


def _as_environment(value: object) -> Environment | None:
    if isinstance(value, Environment):
        value.variables = convert_items(value.variables, _as_variable, field="variables")
        return value
    if isinstance(value, dict) and "variables" in value:
        return Environment(
            variables=convert_items(value["variables"], _as_variable, field="variables"),
            references=convert_names(value.get("references", []), field="references"),
            name=str(value.get("name", "env")),
        )
    if isinstance(value, (list, tuple)):
        return Environment(variables=convert_items(value, _as_variable, field="variables"))
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
            variables = convert_items(
                list(convert_mapping(declaration, field="VARIABLES").items()),
                lambda item: _from_declaration(item[0], item[1]),
                field="VARIABLES",
            )
            env = Environment(
                variables=variables,
                references=convert_names(getattr(module, "REFERENCES", []), field="REFERENCES"),
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
