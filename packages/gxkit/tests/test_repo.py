"""Repository hygiene: the files a host and a contributor expect, and the
cross-platform defaults that keep a checkout reproducible.
"""

from __future__ import annotations

import pathlib
import re
import runpy
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]

REQUIRED = (
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
    "SKILL.md",
    "llms.txt",
    "action.yml",
    ".gitattributes",
    ".mailmap",
    ".github/dependabot.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/ISSUE_TEMPLATE/config.yml",
)


def test_required_repo_files_exist():
    for rel in REQUIRED:
        assert (ROOT / rel).exists(), f"missing {rel}"


def test_security_points_at_the_reporting_path():
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "security/advisories" in text, "SECURITY.md has no reporting path"
    assert "Supported versions" in text, "SECURITY.md states no supported versions"
    assert "gxcore" in text and "gxkit-cli" in text, "SECURITY.md names no distributions"
    assert "3.10" in text, "SECURITY.md states no Python range"


def test_every_html_image_in_the_readme_has_alt_text():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for tag in re.findall(r"<img\b[^>]*>", readme):
        assert "alt=" in tag, f"an <img> has no alt text: {tag}"


def test_gitattributes_pins_text_to_lf():
    text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "text=auto" in text and "eol=lf" in text, "text is not normalized to LF"


AUTHOR_ALLOWLIST = {
    "nekomario28 <206304251+nekomario28@users.noreply.github.com>",
    "dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>",
}


def test_authors_are_canonicalised_through_the_mailmap():
    # `gh pr merge --squash` authored one commit as the profile display name; the
    # `.mailmap` maps it back. A new bare name means a new entry is wanted.
    if not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    out = subprocess.run(
        ["git", "log", "--format=%aN <%aE>"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    found = {line.strip() for line in out.splitlines() if line.strip()}
    unexpected = found - AUTHOR_ALLOWLIST
    assert not unexpected, f"unexpected authors — add a .mailmap entry: {sorted(unexpected)}"


def test_the_readme_agent_prompt_targets_the_family_install_command():
    runpy.run_path(str(ROOT / "scripts/guard_contracts.py"))["check_agent_prompt"](ROOT)


def test_the_coverage_floor_names_every_distribution():
    if sys.platform == "win32":
        pytest.skip("shell-argument observation runs on the POSIX coverage lanes")
    runpy.run_path(str(ROOT / "scripts/guard_contracts.py"))["check_coverage"](ROOT)


def test_ffmpeg_bound_modules_are_not_excluded_from_coverage():
    # The 100% floor is what makes a missing ffmpeg fail CI instead of silently
    # skipping; a `# pragma: no cover` here would unbind it.
    for name in ("checks", "clip", "probe", "render"):
        path = ROOT / "packages/framegx/src/framegx" / f"{name}.py"
        assert "pragma: no cover" not in path.read_text(encoding="utf-8"), (
            f"framegx/{name}.py excludes a capability-bound line from coverage"
        )


SELF = ROOT / "scripts/self_inspect.py"


def _self():
    return runpy.run_path(str(SELF))


PREPUBLISH = ROOT / "scripts" / "prepublish_check.py"


def _quoted(value: str) -> str:
    return '"' + value + '"'


# Assembled from pieces, never written whole: this file is tracked, and the gate
# this tests scans the tracked tree, so a literal sample would make the gate fail
# on its own test.
@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("aws = " + _quoted("AKIA" + "A" * 16), "aws-access-key"),
        ("token = " + _quoted("ghp_" + "a" * 24), "github-token"),
        ("key = " + _quoted("sk-" + "a" * 24), "openai-key"),
        ("key = " + _quoted("sk-" + "ant-" + "a" * 24), "anthropic-key"),
        ("hook = " + _quoted("xoxb-" + "1234567890"), "slack-token"),
        ("-----BEGIN " + "RSA PRIVATE KEY-----", "private-key-block"),
        ("password = " + _quoted("hunter2" * 2), "hardcoded-secret"),
        ("HOME=" + "/" + "home/someone/project", "unix-home-path"),
        ("path = C:" + "\\" + "Users\\someone\\project", "windows-home-path"),
    ],
)
def test_the_prepublication_rules_can_fire(text, rule):
    """A rule that cannot fire is not a gate, so each is shown firing."""
    found = runpy.run_path(str(PREPUBLISH))["findings_in"](text)
    assert rule in {found_rule for found_rule, _where, _line, _text in found}, found


def test_the_prepublication_rules_accept_ordinary_text():
    found = runpy.run_path(str(PREPUBLISH))["findings_in"](
        "key = os.environ['API_KEY']\npath = pathlib.Path('docs/README.md')\n"
    )
    assert found == []


def test_no_tracked_file_carries_a_credential_or_a_machine_path():
    """The gate itself, run over the real tree: this is what CI blocks on."""
    scan_head = runpy.run_path(str(PREPUBLISH))["scan_head"]
    assert scan_head() == []


def test_every_uploaded_artifact_expires():
    """CI artifacts nobody downloads must not accumulate without bound."""
    runpy.run_path(str(ROOT / "scripts/guard_contracts.py"))["check_artifacts"](ROOT)


def test_the_family_accepts_its_own_module_graph():
    """The real graph, inspected by the tool that would report a break in it."""
    assert _self()["main"]() == 0


def test_the_layering_rule_rejects_every_forbidden_direction():
    """A shared layer cannot express a sibling ban, so the rule is pinned here."""
    check = _self()["check_layering"]
    modules = ["gxcore", "gxkit", "chartgx", "crongx"]
    allowed = [("chartgx", "gxcore"), ("gxkit", "chartgx"), ("gxkit", "gxcore")]
    assert check(modules, allowed) == []
    assert check(modules, [("gxcore", "chartgx")]) == [
        "the shared core must not depend on 'chartgx'"
    ]
    assert check(modules, [("chartgx", "crongx")]) == [
        "'chartgx' must not depend on the sibling tool 'crongx'"
    ]
    assert check(modules, [("crongx", "gxkit")]) == ["'crongx' must not depend on the umbrella"]


#: The only places allowed to opt out of the coverage floor, and why. An agent
#: reaching for a 100% floor reaches for this pragma, and a handful of silent ones
#: turns the floor into decoration.
EXCLUDED_FROM_COVERAGE = {
    "packages/gxcore/src/gxcore/config.py": "tomllib import guard: 3.11+ only",
    "packages/shadergx/src/shadergx/gl.py": "import guard for a missing GL binding",
}


def test_the_coverage_exclusions_are_the_declared_ones():
    """Every `# pragma: no cover` is named here with its reason.

    The floor is only worth what it excludes: a pragma added to make a red line
    green is how a 100% floor stops meaning anything. Adding one is fine — it just
    has to be a decision someone wrote down.
    """
    found: dict[str, list[str]] = {}
    for path in sorted((ROOT / "packages").glob("*/src/**/*.py")):
        text = path.read_text(encoding="utf-8")
        lines = [line.strip() for line in text.splitlines() if "pragma: no cover" in line]
        if lines:
            found[path.relative_to(ROOT).as_posix()] = lines
    assert set(found) == set(EXCLUDED_FROM_COVERAGE), (
        f"coverage exclusions changed: {sorted(set(found) ^ set(EXCLUDED_FROM_COVERAGE))}"
    )
    for path, lines in found.items():
        assert lines, path
        # Each exclusion states *why*, not just that it is excluded.
        assert all(len(line.split("no cover")[1].strip(" -:")) >= 8 for line in lines), (
            f"{path} excludes a line without a reason: {lines}"
        )
