"""Repository hygiene: the files a host and a contributor expect, and the
cross-platform defaults that keep a checkout reproducible.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

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


def test_the_readme_agent_prompt_is_installable():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "llms.txt" in readme, "the README has no agent setup prompt"
    llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
    install = re.search(r"#subdirectory=packages/([a-z0-9]+)", llms)
    assert install, "llms.txt has no install line for the prompt to name"
    assert (ROOT / "packages" / install.group(1)).is_dir(), (
        f"the agent prompt installs a package that does not exist: {install.group(1)}"
    )


def test_the_coverage_floor_names_every_distribution():
    from gxkit.registry import TOOLS

    names = {"gxcore", "gxkit", *(tool.name for tool in TOOLS)}
    for rel in ("scripts/check.sh", ".github/workflows/ci.yml"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "--cov-fail-under=100" in text, f"{rel} has no coverage floor"
        found = set(re.findall(r"--cov=([a-z0-9_]+)", text))
        assert found == names, f"{rel} coverage set drifted: {sorted(found ^ names)}"


def test_ffmpeg_bound_modules_are_not_excluded_from_coverage():
    # The 100% floor is what makes a missing ffmpeg fail CI instead of silently
    # skipping; a `# pragma: no cover` here would unbind it.
    for name in ("checks", "clip", "probe", "render"):
        path = ROOT / "packages/framegx/src/framegx" / f"{name}.py"
        assert "pragma: no cover" not in path.read_text(encoding="utf-8"), (
            f"framegx/{name}.py excludes a capability-bound line from coverage"
        )
