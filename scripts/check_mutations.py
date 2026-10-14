"""Bounded red proofs: restore each audited defect in a disposable checkout.

Run the unmodified controls first. A mutant is killed only by its named test's
assertion, not by collection, import or environment failure. Copies and logs are
removed on exit; the real checkout and installed distributions are never edited.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT_TEST = "packages/gxkit/tests/"
CORE_TEST = "packages/gxcore/tests/"


@dataclass(frozen=True)
class Mutation:
    name: str
    path: str
    before: str
    after: str
    test: str


def mutations(root: Path) -> list[Mutation]:
    repo = KIT_TEST + "test_repo.py::"
    gates = KIT_TEST + "test_inspection_gates.py::"
    inputs = (
        KIT_TEST + "test_declared_inputs.py::test_malformed_members_are_rejected_with_their_index"
    )
    bounds = KIT_TEST + "test_input_boundaries.py::"
    prompt = re.search(
        r"> \*\*Set up with a prompt\.\*\*.*?(?=\n\n)",
        (root / "README.md").read_text(encoding="utf-8"),
        re.S,
    )
    assert prompt, "the control README must contain its prompt before mutation"
    coverage_test = repo + "test_the_coverage_floor_names_every_distribution"
    floor = "--cov-fail-under=100"
    cases = [
        Mutation(
            "prompt-deleted",
            "README.md",
            prompt.group(),
            "",
            repo + "test_the_readme_agent_prompt_targets_the_family_install_command",
        ),
        Mutation(
            "install-command-corrupted",
            "llms.txt",
            "uv tool install",
            "uv tool uninstall",
            repo + "test_the_readme_agent_prompt_targets_the_family_install_command",
        ),
        Mutation(
            "shell-floor-comment",
            "scripts/check.sh",
            floor,
            "--cov-fail-under=99\n# " + floor,
            coverage_test,
        ),
        Mutation(
            "ci-floor-comment",
            ".github/workflows/ci.yml",
            floor,
            "--cov-fail-under=99\n          # " + floor,
            coverage_test,
        ),
        Mutation("coverage-member-omitted", "scripts/check.sh", "--cov=seedgx ", "", coverage_test),
        Mutation(
            "coverage-only-echoed",
            "scripts/check.sh",
            "step uv run pytest \\\n",
            "step echo uv run pytest \\\n",
            coverage_test,
        ),
        Mutation(
            "coverage-disabled", "scripts/check.sh", floor, floor + " --no-cov", coverage_test
        ),
        Mutation(
            "artifact-exit-bypass",
            "packages/gxkit/src/gxkit/cli.py",
            "except (Exception, SystemExit) as exc:",
            "except Exception as exc:",
            gates + "test_artifact_exit_is_a_load_failure_and_does_not_stop_the_directory",
        ),
        Mutation(
            "double-artifact-execution",
            "packages/gxcore/src/gxcore/loading.py",
            "token = _MODULES.set({})",
            "token = _MODULES.set(None)",
            gates + "test_auto_detection_and_inspection_share_one_execution_per_invocation",
        ),
        Mutation(
            "stale-bytecode",
            "packages/gxcore/src/gxcore/loading.py",
            'exec(compile(path.read_bytes(), str(path), "exec", dont_inherit=True), module.__dict__)',
            "spec.loader.exec_module(module)",
            CORE_TEST + "test_loading.py::test_same_size_edits_are_not_hidden_by_cached_bytecode",
        ),
        Mutation(
            "baseline-occurrences-collapsed",
            "packages/gxcore/src/gxcore/baseline.py",
            "    before: dict[str, deque[int]] = defaultdict(deque)",
            "    report.problems = list({fingerprint(p.code, p.target, p.label, p.identity): p for p in report.problems}.values())\n    before: dict[str, deque[int]] = defaultdict(deque)",
            CORE_TEST
            + "test_baseline_occurrences.py::test_an_additional_occurrence_is_a_new_error",
        ),
        Mutation(
            "overlap-partner-not-identified",
            "packages/crongx/src/crongx/checks.py",
            "                        identity=(a.resource, *sorted((a.name, b.name))),\n",
            "",
            gates + "test_replacing_an_overlap_partner_is_a_new_error",
        ),
        Mutation(
            "conversion-failure-falls-back",
            "packages/gxcore/src/gxcore/loading.py",
            "        except InvalidArtifact:\n            raise",
            "        except InvalidArtifact:\n            return None",
            inputs,
        ),
        Mutation(
            "tuple-resource-default",
            "packages/crongx/src/crongx/model.py",
            'resource=str(value[3]) if len(value) > 3 else "",',
            'resource=str(value[3]) if len(value) > 3 else "0.0",',
            bounds + "test_abbreviated_run_tuples_keep_the_unshared_resource_default",
        ),
        Mutation(
            "empty-interval-overlap",
            "packages/crongx/src/crongx/model.py",
            "return valid and a.start < b.end and b.start < a.end",
            "return a.start < b.end and b.start < a.end",
            bounds + "test_empty_or_reversed_intervals_never_overlap",
        ),
        Mutation(
            "fractional-seed-truncated",
            "packages/seedgx/src/seedgx/model.py",
            "return Stream(str(name), _seed(seed))",
            "return Stream(str(name), int(seed) if seed is not None else None)",
            bounds + "test_seed_declarations_reject_noninteger_values_without_truncation",
        ),
        Mutation(
            "empty-environment-references",
            "packages/envgx/src/envgx/checks.py",
            "if reference not in declared:",
            "if declared and reference not in declared:",
            bounds + "test_empty_environment_still_checks_references",
        ),
        Mutation(
            "empty-network-references",
            "packages/netgx/src/netgx/checks.py",
            "if node not in declared:",
            "if declared and node not in declared:",
            bounds + "test_empty_network_still_checks_edge_endpoints",
        ),
        Mutation(
            "api-prefix-not-boundary",
            "packages/apigx/src/apigx/checks.py",
            "if api.base and not under_base:",
            "if api.base and not endpoint.path.startswith(api.base):",
            bounds + "test_api_version_prefix_matches_a_path_boundary",
        ),
    ]
    for package, field, singular, marker in [
        ("crongx", "runs", "run", "RUNS"),
        ("seedgx", "streams", "stream", "STREAMS"),
        ("pipegx", "steps", "step", "STEPS"),
    ]:
        cases.append(
            Mutation(
                f"{package}-drops-member",
                f"packages/{package}/src/{package}/model.py",
                f'{field}=convert_items({field}, _as_{singular}, field="{marker}")',
                f"{field}=[v for v in (_as_{singular}(item) for item in {field}) if v is not None]",
                inputs,
            )
        )
    for package, field, singular in [
        ("envgx", "variables", "variable"),
        ("apigx", "endpoints", "endpoint"),
    ]:
        cases.append(
            Mutation(
                f"{package}-drops-member",
                f"packages/{package}/src/{package}/model.py",
                f'{field}=convert_items(value["{field}"], _as_{singular}, field="{field}")',
                f'{field}=[v for v in (_as_{singular}(item) for item in value["{field}"]) if v is not None]',
                inputs,
            )
        )
    shell = (root / "scripts/check.sh").read_text(encoding="utf-8")
    block = re.search(r"step uv run pytest .*?(?=\nstep |\nif )", shell, re.S)
    assert block
    cases.extend(
        [
            Mutation(
                "coverage-step-unreachable",
                "scripts/check.sh",
                block.group(),
                "if false; then\n" + block.group() + "\nfi",
                coverage_test,
            ),
            Mutation(
                "coverage-floor-separate-override",
                "scripts/check.sh",
                floor,
                floor + " --cov-fail-under 99",
                coverage_test,
            ),
        ]
    )
    checks = (root / "packages/crongx/src/crongx/checks.py").read_text(encoding="utf-8")
    invalid = re.search(r"        if not run\.is_finite:\n.*?            continue\n", checks, re.S)
    assert invalid
    cases.append(
        Mutation(
            "nonfinite-time-certified",
            "packages/crongx/src/crongx/checks.py",
            invalid.group(),
            "",
            bounds + "test_nonfinite_time_cannot_be_certified_or_used_for_overlap",
        )
    )
    cases.append(
        Mutation(
            "loader-future-flags-inherited",
            "packages/gxcore/src/gxcore/loading.py",
            ", dont_inherit=True",
            "",
            CORE_TEST
            + "test_loading.py::test_future_annotations_follow_the_artifact_not_the_loader",
        )
    )
    return cases


def _pytest(root: Path, env: dict[str, str], tests: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-o", "addopts=", "-q", *tests],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )


def main() -> int:
    cases = mutations(ROOT)
    with tempfile.TemporaryDirectory(prefix="gxkit-mutations-") as directory:
        copy = Path(directory) / "tree"
        shutil.copytree(
            ROOT,
            copy,
            ignore=shutil.ignore_patterns(
                ".git",
                ".venv",
                "dist",
                "__pycache__",
                "*.pyc",
                ".coverage",
                ".mypy_cache",
                ".ruff_cache",
                ".pytest_cache",
            ),
        )
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                str(path) for path in sorted(copy.glob("packages/*/src"))
            ),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_ADDOPTS": "",
        }
        # Assert imports resolve to the disposable code, not editable installs.
        ownership = subprocess.run(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; import gxcore, gxkit; assert all(Path(m.__file__).is_relative_to(Path.cwd()) for m in (gxcore, gxkit))",
            ],
            cwd=copy,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert ownership.returncode == 0, ownership.stderr
        control = _pytest(copy, env, sorted({case.test for case in cases}))
        if control.returncode != 0:
            print(control.stdout + control.stderr)
            print("FAIL: unmodified controls did not pass")
            return 1
        for case in cases:
            path = copy / case.path
            original = path.read_text(encoding="utf-8")
            assert original.count(case.before) == 1, f"{case.name}: ambiguous/stale mutation target"
            try:
                path.write_text(original.replace(case.before, case.after), encoding="utf-8")
                result = _pytest(copy, env, [case.test])
                output = result.stdout + result.stderr
                killed = (
                    result.returncode == 1
                    and "AssertionError" in output
                    and f"FAILED {case.test}" in output
                    and "ERROR collecting" not in output
                )
                if not killed:
                    print(output)
                    print(f"FAIL: {case.name} survived or failed for the wrong reason")
                    return 1
                print(f"killed: {case.name}", flush=True)
            finally:
                path.write_text(original, encoding="utf-8")
        print(f"All {len(cases)} bounded mutants were killed after green controls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
