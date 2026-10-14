"""The catalogue: every `*gx` tool, what it inspects, and how to recognise its artifact.

Static on purpose — `gxkit tools` and detection must not import matplotlib or
modernGL. A tool is imported only when it is actually chosen.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    inspects: str
    module: str  # "<tool>.tool" holds TOOL
    attrs: tuple[str, ...]  # module attributes holding the artifact object
    classes: tuple[str, ...]  # the artifact's class name(s)
    markers: tuple[str, ...]  # module-level names that also identify it


# Order matters: class matches win, then markers, and `protogx` is checked
# before `flowgx` because a protocol file also has STATES/TRANSITIONS.
TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "chartgx",
        "matplotlib charts",
        "chartgx.tool",
        ("fig", "figure"),
        ("Figure",),
        ("PLOT", "matplotlib"),
    ),
    ToolSpec(
        "levelgx",
        "game levels",
        "levelgx.tool",
        ("level",),
        ("Level",),
        ("LEVEL", "rows", "MAP", "map"),
    ),
    ToolSpec(
        "authzgx",
        "permission models",
        "authzgx.tool",
        ("model", "auth"),
        ("AuthModel",),
        ("GRANTS", "ROLES", "PERMISSIONS", "ASSIGNED"),
    ),
    ToolSpec(
        "depsgx",
        "module dependency graphs",
        "depsgx.tool",
        ("graph",),
        ("ModuleGraph",),
        ("DEPENDS", "MODULES", "LAYERS", "ROOTS"),
    ),
    ToolSpec(
        "schemagx",
        "relational schemas",
        "schemagx.tool",
        ("schema",),
        ("Schema",),
        ("TABLES", "FOREIGN_KEYS", "PRIMARY_KEYS"),
    ),
    ToolSpec(
        "docgx", "pages / slides", "docgx.tool", ("page", "slide"), ("Page",), ("BLOCKS", "TITLE")
    ),
    ToolSpec(
        "shadergx",
        "fragment shaders",
        "shadergx.tool",
        ("shader",),
        ("Shader",),
        ("FRAGMENT", "fragment"),
    ),
    ToolSpec(
        "framegx", "rendered animations", "framegx.tool", ("video", "clip"), ("Video",), ("PATH",)
    ),
    ToolSpec(
        "protogx",
        "protocols",
        "protogx.tool",
        ("protocol", "proto"),
        ("Protocol",),
        ("PROTOCOL", "MESSAGES", "REQUESTS", "RESPONSES"),
    ),
    ToolSpec(
        "flowgx",
        "state machines",
        "flowgx.tool",
        ("machine",),
        ("Machine",),
        ("MACHINE", "STATES", "TRANSITIONS", "ACCEPT"),
    ),
    ToolSpec(
        "apigx",
        "HTTP API contracts",
        "apigx.tool",
        ("api", "API", "contract"),
        ("API",),
        ("ENDPOINTS", "BASE"),
    ),
    ToolSpec(
        "netgx",
        "network topologies",
        "netgx.tool",
        ("network", "NETWORK", "net", "topology"),
        ("Network",),
        ("NODES", "EDGES", "SENSITIVE"),
    ),
    ToolSpec(
        "envgx",
        "environment / config",
        "envgx.tool",
        ("env", "environment", "ENV", "ENVIRONMENT", "config"),
        ("Environment",),
        ("VARIABLES", "REFERENCES"),
    ),
    ToolSpec(
        "pipegx",
        "build pipelines",
        "pipegx.tool",
        ("pipeline", "PIPELINE", "dag"),
        ("Pipeline",),
        ("STEPS", "GOALS"),
    ),
)

BY_NAME = {spec.name: spec for spec in TOOLS}


def detect(module: object) -> ToolSpec | None:
    """Which tool owns this module, by the artifact object it defines."""

    def first_attr(names: tuple[str, ...]) -> object | None:
        for name in names:
            value: object = getattr(module, name, None)
            if value is not None:
                return value
        return None

    for spec in TOOLS:
        value = first_attr(spec.attrs)
        if value is not None and type(value).__name__ in spec.classes:
            return spec
    for spec in TOOLS:
        if any(getattr(module, m, None) is not None for m in spec.markers):
            return spec
    return None
