"""Repository hygiene: the files a host and a contributor expect, and the
cross-platform defaults that keep a checkout reproducible.
"""

from __future__ import annotations

import pathlib
import re

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
