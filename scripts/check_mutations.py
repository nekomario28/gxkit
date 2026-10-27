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
    gates = KIT_TEST + "test_inspection_gates.py::"
    parents = KIT_TEST + "test_declared_inputs.py::"
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
            bounds + "test_seed_declarations_report_noninteger_values_without_truncation",
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
            "        for node in (src, dst):\n            if node not in declared:",
            "        for node in (src, dst):\n            if declared and node not in declared:",
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
    # A report must survive a console that cannot encode every character it
    # names; losing it to an encoding error would turn a verdict into exit 2.
    cases.append(
        Mutation(
            "report-output-not-tolerated",
            "packages/gxcore/src/gxcore/cli.py",
            "def run(\n    tool: Tool,\n    argv: list[str] | None = None,\n    known_tools: Iterable[str] | None = None,\n    known_codes: Mapping[str, Iterable[str]] | None = None,\n) -> int:\n    printable_output()\n",
            "def run(\n    tool: Tool,\n    argv: list[str] | None = None,\n    known_tools: Iterable[str] | None = None,\n    known_codes: Mapping[str, Iterable[str]] | None = None,\n) -> int:\n",
            gates + "test_a_report_survives_a_console_that_cannot_encode_it",
        )
    )
    # A replaced relationship must not read as unchanged debt: the finding names
    # its own edge and endpoint, and a baseline compares identities.
    cases.append(
        Mutation(
            "network-relationship-unidentified",
            "packages/netgx/src/netgx/checks.py",
            "                        identity=(src, dst, node),\n",
            "",
            gates + "test_replacing_an_unknown_edge_endpoint_is_a_new_error",
        )
    )
    # An artifact's own directory change must not redirect the inspection.
    cases.extend(
        [
            Mutation(
                "relative-input-not-resolved",
                "packages/gxkit/src/gxkit/cli.py",
                "        target = Path(raw).resolve()",
                "        target = Path(raw)",
                gates
                + "test_a_relative_input_keeps_its_identity_when_the_artifact_changes_directory",
            ),
            Mutation(
                "direct-tool-config-looked-up-after-load",
                "packages/gxcore/src/gxcore/cli.py",
                "apply_config(report, load_config(path.parent, known_tools, known_codes), tool.name)",
                "apply_config(report, load_config(Path(args.file).resolve().parent, known_tools, known_codes), tool.name)",
                gates + "test_a_direct_tool_reads_its_own_config_directory",
            ),
        ]
    )
    # A recognized declaration must fail closed instead of coercing its members.
    cases.extend(
        [
            Mutation(
                "name-member-coerced",
                "packages/gxcore/src/gxcore/loading.py",
                '    if not isinstance(value, str):\n        raise InvalidArtifact(f"expected a name, not {value!r}")\n    return value',
                "    return str(value)",
                parents + "test_a_malformed_name_reports_its_field_and_index",
            ),
            Mutation(
                "name-collection-unvalidated",
                "packages/gxcore/src/gxcore/loading.py",
                "    return convert_items(values, _name, field=field)",
                "    return [str(value) for value in values]",
                parents + "test_a_recognized_parent_with_an_invalid_collection_is_not_replaced",
            ),
            Mutation(
                "envgx-parent-names-coerced",
                "packages/envgx/src/envgx/model.py",
                'references=convert_names(value.get("references", []), field="references"),',
                'references=[str(r) for r in value.get("references", [])],',
                parents + "test_a_recognized_parent_with_an_invalid_collection_is_not_replaced",
            ),
            Mutation(
                "pipegx-parent-names-coerced",
                "packages/pipegx/src/pipegx/model.py",
                'goals=convert_names(value.get("goals", []), field="goals"),',
                'goals=[str(g) for g in value.get("goals", [])],',
                parents + "test_a_recognized_parent_with_an_invalid_collection_is_not_replaced",
            ),
            Mutation(
                "apigx-parent-names-coerced",
                "packages/apigx/src/apigx/model.py",
                'auth_schemes=convert_names(value.get("auth_schemes", []), field="auth_schemes"),',
                'auth_schemes=list(value.get("auth_schemes", [])),',
                parents + "test_a_recognized_parent_with_an_invalid_collection_is_not_replaced",
            ),
        ]
    )
    # An importer must not widen a check's claim: authentication, the supported
    # version and a malformed document all have to reach the same codes.
    cases.extend(
        [
            Mutation(
                "openapi-inherited-security-ignored",
                "packages/apigx/src/apigx/openapi.py",
                '    requirements = operation["security"] if "security" in operation else document.get("security")',
                '    requirements = operation["security"] if "security" in operation else None',
                KIT_TEST
                + "test_foreign_inputs.py::test_a_spec_that_inherits_its_security_has_no_unauthenticated_mutation",
            ),
            Mutation(
                "openapi-version-unchecked",
                "packages/apigx/src/apigx/openapi.py",
                '    if not isinstance(version, str) or not version.startswith("3."):',
                "    if False:",
                KIT_TEST
                + "test_foreign_inputs.py::test_a_malformed_document_is_an_input_failure_with_its_location",
            ),
            Mutation(
                "openapi-malformed-swallowed",
                "packages/apigx/src/apigx/openapi.py",
                '    except json.JSONDecodeError as exc:\n        raise InvalidArtifact(f"{path}: not JSON ({exc})") from exc',
                "    except json.JSONDecodeError:\n        return API()",
                KIT_TEST
                + "test_foreign_inputs.py::test_a_malformed_document_is_an_input_failure_with_its_location",
            ),
            Mutation(
                "openapi-json-not-routed",
                "packages/apigx/src/apigx/model.py",
                '    if Path(path).suffix.lower() == ".json":',
                "    if False:",
                KIT_TEST
                + "test_foreign_inputs.py::test_a_published_spec_is_inspected_by_the_same_codes",
            ),
            Mutation(
                "foreign-document-detected-as-python",
                "packages/gxkit/src/gxkit/cli.py",
                '    if suffix != ".py":',
                "    if False:",
                KIT_TEST + "test_foreign_inputs.py::test_a_document_needs_the_tool_named",
            ),
        ]
    )
    # The DDL importer must not guess where the schema is ambiguous, and must
    # keep reading a dump whose keys are spelled the way a dialect spells them.
    cases.extend(
        [
            Mutation(
                "ddl-composite-key-guessed",
                "packages/schemagx/src/schemagx/ddl.py",
                '        if len(columns) != 1:\n            raise InvalidArtifact(\n                f"{where}: a composite primary key on {table!r} is not representable; "',
                "        if False:\n            raise InvalidArtifact('unused'",
                "packages/schemagx/tests/test_ddl.py::test_a_file_that_is_not_readable_ddl_says_where_it_is_wrong",
            ),
            Mutation(
                "ddl-unclosed-table-accepted",
                "packages/schemagx/src/schemagx/ddl.py",
                '    raise InvalidArtifact("a CREATE TABLE is never closed")',
                "    return len(text)",
                "packages/schemagx/tests/test_ddl.py::test_a_file_that_is_not_readable_ddl_says_where_it_is_wrong",
            ),
            Mutation(
                "ddl-type-families-dropped",
                "packages/schemagx/src/schemagx/model.py",
                "    return TYPE_FAMILIES.get(text, text)",
                "    return text",
                "packages/schemagx/tests/test_ddl.py::test_synonymous_types_are_the_same_family",
            ),
            Mutation(
                "ddl-json-not-routed",
                "packages/schemagx/src/schemagx/model.py",
                '    if Path(path).suffix.lower() == ".sql":',
                "    if False:",
                "packages/gxkit/tests/test_foreign_inputs.py::test_a_sql_file_is_inspected_by_the_same_codes",
            ),
        ]
    )
    # The Mermaid importer must keep the structure the diagram draws: the start
    # marker, the terminal marker, and a refusal where Mermaid can express more
    # than the machine can hold.
    cases.extend(
        [
            Mutation(
                "mermaid-start-marker-ignored",
                "packages/flowgx/src/flowgx/mermaid.py",
                "        if source_state == INITIAL:",
                "        if False:",
                "packages/gxkit/tests/test_foreign_inputs.py::test_a_mermaid_diagram_is_inspected_by_the_same_codes",
            ),
            Mutation(
                "mermaid-terminal-marker-ignored",
                "packages/flowgx/src/flowgx/mermaid.py",
                "        if target_state == INITIAL:\n            diagram.accept.append(source_state)\n            continue",
                "        if False:\n            continue",
                "packages/flowgx/tests/test_mermaid.py::test_a_terminal_marker_makes_the_state_accepting",
            ),
            Mutation(
                "mermaid-composite-flattened",
                "packages/flowgx/src/flowgx/mermaid.py",
                '        if depth > 0 or line.rstrip().endswith("{"):',
                "        if False:",
                "packages/gxkit/tests/test_foreign_inputs.py::test_a_diagram_that_cannot_be_read_says_where_it_is_wrong",
            ),
            Mutation(
                "mermaid-markdown-not-routed",
                "packages/flowgx/src/flowgx/machine.py",
                '    if path.suffix.lower() in {".mmd", ".mermaid", ".md", ".markdown"}:',
                "    if False:",
                "packages/gxkit/tests/test_foreign_inputs.py::test_a_diagram_drawn_in_a_document_is_read_through_it",
            ),
        ]
    )
    # The review of the importers found five ways they could be silently wrong:
    # an anonymous alternative read as authenticated, a server path ignored, an
    # intervening statement skipped, an omitted reference column invented, and a
    # referenced path item dropped. Each is restored and must be rejected.
    cases.extend(
        [
            Mutation(
                "openapi-anonymous-alternative-authenticated",
                "packages/apigx/src/apigx/openapi.py",
                "    return all(requirement for requirement in requirements)",
                "    return True",
                "packages/apigx/tests/test_openapi.py::test_an_anonymous_alternative_makes_the_operation_public",
            ),
            Mutation(
                "openapi-server-path-ignored",
                "packages/apigx/src/apigx/openapi.py",
                '    if not server_path:\n        return path\n    return server_path + (path if path.startswith("/") else f"/{path}")',
                "    return path",
                "packages/apigx/tests/test_openapi.py::test_an_operation_path_is_relative_to_the_server_path",
            ),
            Mutation(
                "openapi-reference-dropped",
                "packages/apigx/src/apigx/openapi.py",
                "    if reference is not None:",
                "    if False:",
                "packages/apigx/tests/test_openapi.py::test_a_reference_anywhere_is_refused_with_its_location",
            ),
            Mutation(
                "ddl-next-statement-searched-past",
                "packages/schemagx/src/schemagx/ddl.py",
                "        match = CREATE_TABLE.match(cleaned, position)",
                "        match = CREATE_TABLE.search(cleaned, position)",
                "packages/schemagx/tests/test_ddl.py::test_a_statement_between_two_tables_is_refused_not_skipped",
            ),
            Mutation(
                "ddl-reference-column-invented",
                "packages/schemagx/src/schemagx/ddl.py",
                "        primary = primary_keys.get(parent)\n        if primary is None:",
                '        primary = primary_keys.get(parent) or "id"\n        if False:',
                "packages/schemagx/tests/test_ddl.py::test_a_reference_to_a_table_without_a_primary_key_is_refused",
            ),
        ]
    )
    # "Silence is never a verdict": an unhandled construct must be refused, and
    # the refusal must be what the test sees.
    cases.extend(
        [
            Mutation(
                "openapi-unknown-keys-ignored",
                "packages/apigx/src/apigx/openapi.py",
                '    return sorted(\n        str(key) for key in keys if str(key) not in known and not str(key).lower().startswith("x-")\n    )',
                "    return []",
                KIT_TEST
                + "test_foreign_inputs.py::test_an_importer_refuses_what_it_cannot_account_for",
            ),
            Mutation(
                "openapi-webhooks-ignored",
                "packages/apigx/src/apigx/openapi.py",
                '    if document.get("webhooks"):',
                "    if False:",
                KIT_TEST
                + "test_foreign_inputs.py::test_an_importer_refuses_what_it_cannot_account_for",
            ),
        ]
    )
    # Deeper component reporting is only honest if every component is reported
    # and if the fingerprint follows the component rather than the witness.
    cases.extend(
        [
            Mutation(
                "depsgx-cycle-identity-from-display",
                "packages/depsgx/src/depsgx/checks.py",
                "                identity=tuple(component),\n",
                "",
                KIT_TEST + "test_inspection_gates.py::test_a_rotated_cycle_witness_is_not_new_debt",
            ),
        ]
    )
    # What the second review and the coherence sweep found: a composite key
    # truncated before validation, a literal read as a comment, a server override
    # ignored, and a declared suffix nothing used.
    cases.extend(
        [
            Mutation(
                "ddl-composite-child-column-dropped",
                "packages/schemagx/src/schemagx/ddl.py",
                '        if len(columns) != 1:\n            raise InvalidArtifact(\n                f"{where}: a composite foreign key on {table!r} is not representable; "\n                "declare the schema in Python"\n            )',
                "        if False:\n            raise InvalidArtifact('unused')",
                KIT_TEST
                + "test_foreign_inputs.py::test_a_composite_key_is_still_refused_when_the_target_is_omitted",
            ),
            Mutation(
                "ddl-comment-stripping-not-quote-aware",
                "packages/schemagx/src/schemagx/ddl.py",
                '        if character in "\'\\"":\n            quote = character\n            out.append(character)\n            index += 1\n            continue',
                "        if False:\n            index += 1\n            continue",
                KIT_TEST
                + "test_foreign_inputs.py::test_a_sql_literal_containing_a_comment_marker_is_read",
            ),
            Mutation(
                "openapi-server-override-ignored",
                "packages/apigx/src/apigx/openapi.py",
                '        path_override = _override_path(operations.get("servers"))',
                "        path_override = None",
                KIT_TEST
                + "test_foreign_inputs.py::test_a_server_override_the_model_cannot_represent_is_refused",
            ),
            Mutation(
                "gxkit-foreign-suffix-not-named",
                "packages/gxkit/src/gxkit/cli.py",
                "        if len(readers) == 1:",
                "        if False:",
                KIT_TEST + "test_cli_units.py::test_a_foreign_document_is_told_which_tool_reads_it",
            ),
            Mutation(
                "netgx-duplicate-edge-unidentified",
                "packages/netgx/src/netgx/checks.py",
                "                    identity=(src, dst),\n",
                "",
                KIT_TEST
                + "test_inspection_gates.py::test_a_replaced_duplicate_edge_is_not_the_same_finding",
            ),
        ]
    )
    # A malformed input *file* must be refused like a malformed declaration:
    # gxcore's own config and baseline are inputs too, and both used to be read
    # as something other than what they said.
    cases.extend(
        [
            Mutation(
                "config-ignore-string-split",
                "packages/gxcore/src/gxcore/config.py",
                "    if not isinstance(value, list) or not all(isinstance(name, str) for name in value):",
                "    if False:",
                CORE_TEST
                + "test_config.py::test_a_config_that_cannot_be_understood_is_refused_with_its_field",
            ),
            Mutation(
                "config-invalid-severity-ignored",
                "packages/gxcore/src/gxcore/config.py",
                "        if not isinstance(severity, str) or severity not in VALID_SEVERITIES:",
                "        if False:",
                CORE_TEST
                + "test_config.py::test_a_config_that_cannot_be_understood_is_refused_with_its_field",
            ),
            Mutation(
                "config-tool-key-unchecked",
                "packages/gxcore/src/gxcore/config.py",
                "        if extra:",
                "        if False:",
                CORE_TEST
                + "test_config.py::test_a_config_that_cannot_be_understood_is_refused_with_its_field",
            ),
            Mutation(
                "baseline-record-shape-unchecked",
                "packages/gxcore/src/gxcore/baseline.py",
                "                if not isinstance(record.get(required), str):",
                "                if False:",
                CORE_TEST
                + "test_baseline.py::test_a_baseline_that_cannot_be_read_is_refused_with_its_field",
            ),
        ]
    )
    # A picture that numbers the wrong problem, and an empty declaration that
    # reports nothing, are both silent: each is restored and must be rejected.
    cases.extend(
        [
            Mutation(
                "storyboard-numbering-off-by-one",
                "packages/gxcore/src/gxcore/storyboard.py",
                "    for number, problem in enumerate(sorted(problems, key=sort_key), start=1):",
                "    for number, problem in enumerate(sorted(problems, key=sort_key), start=0):",
                KIT_TEST
                + "test_storyboards.py::test_every_located_problem_is_the_number_the_picture_shows",
            ),
            Mutation(
                "storyboard-unlocated-problem-boxed",
                "packages/gxcore/src/gxcore/storyboard.py",
                "        if problem.bbox is None:\n            continue",
                "        if problem.bbox is None:\n            problem.bbox = (0.0, 0.0, 0.0, 0.0)",
                KIT_TEST
                + "test_storyboards.py::test_every_located_problem_is_the_number_the_picture_shows",
            ),
            Mutation(
                "netgx-empty-network-silent",
                "packages/netgx/src/netgx/checks.py",
                "    if not net.nodes:",
                "    if False:",
                "packages/netgx/tests/test_networks.py::test_an_empty_network_says_so",
            ),
        ]
    )
    # The gates themselves must be shown failing: a repo-hygiene rule, the
    # packaging check, the traceability freshness guard, the layering rule and
    # the action's refusal of an empty directory.
    cases.extend(
        [
            Mutation(
                "prepublish-aws-rule-blind",
                "scripts/prepublish_check.py",
                '    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),',
                '    ("aws-access-key", re.compile(r"AKIA-never-matches")),',
                KIT_TEST + "test_repo.py::test_the_prepublication_rules_can_fire",
            ),
            Mutation(
                "prepublish-home-path-rule-blind",
                "scripts/prepublish_check.py",
                '    ("unix-home-path", re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+/")),',
                '    ("unix-home-path", re.compile(r"/home-never-matches/")),',
                KIT_TEST + "test_repo.py::test_the_prepublication_rules_can_fire",
            ),
            Mutation(
                "release-license-unchecked",
                "scripts/release.py",
                '        if not any(m.endswith("licenses/LICENSE") for m in members):',
                "        if False:",
                KIT_TEST + "test_release.py::test_check_dist_reports_a_wheel_without_a_license",
            ),
            Mutation(
                "release-unexpected-wheel-unchecked",
                "scripts/release.py",
                "    for key in sorted(set(wheels) - {_normalize(n) for n in expected}):",
                "    for key in []:",
                KIT_TEST + "test_release.py::test_check_dist_reports_an_unexpected_wheel",
            ),
            Mutation(
                "trace-codes-column-dropped",
                "scripts/make_trace.py",
                'f"| {len(codes)} | {_examples(spec.name)} |"',
                'f"| {_examples(spec.name)} |"',
                KIT_TEST + "test_docs.py::test_trace_document_covers_every_tool_and_is_current",
            ),
            Mutation(
                "self-inspect-sibling-rule-dropped",
                "scripts/self_inspect.py",
                "        elif src in domains and dst in domains:",
                "        elif False:",
                KIT_TEST + "test_repo.py::test_the_layering_rule_rejects_every_forbidden_direction",
            ),
            Mutation(
                "action-empty-directory-accepted",
                "scripts/inspect_path.sh",
                "    exit 1\n  fi",
                "    true\n  fi",
                KIT_TEST + "test_action_script.py::test_an_empty_directory_fails",
            ),
        ]
    )
    # The "only the first cycle" defect was fixed for depsgx and lived on in four
    # more tools. One mutant per tool keeps it from coming back in any of them.
    cycles = (
        KIT_TEST
        + "test_input_boundaries.py::test_every_independent_cycle_is_a_finding_not_only_the_first"
    )
    for tool, path, call in [
        (
            "depsgx",
            "packages/depsgx/src/depsgx/checks.py",
            "cycle_witnesses(acyclic, self_loops=False)",
        ),
        (
            "authzgx",
            "packages/authzgx/src/authzgx/checks.py",
            "cycle_witnesses(model.role_edges())",
        ),
        ("pipegx", "packages/pipegx/src/pipegx/checks.py", "cycle_witnesses(edges)"),
        (
            "flowgx",
            "packages/flowgx/src/flowgx/checks.py",
            "cycle_witnesses(edges, self_loops=False)",
        ),
        (
            "protogx",
            "packages/protogx/src/protogx/checks.py",
            "cycle_witnesses(edges, self_loops=False)",
        ),
        (
            "schemagx",
            "packages/schemagx/src/schemagx/checks.py",
            "cycle_witnesses(schema.edges(), self_loops=False)",
        ),
    ]:
        cases.append(
            Mutation(
                f"{tool}-first-cycle-only",
                path,
                call,
                f"{call}[:1]",
                cycles,
            )
        )
    cases.append(
        Mutation(
            "cycle-witness-single",
            "packages/gxcore/src/gxcore/graph.py",
            "    for component in strongly_connected_components(e):",
            "    for component in strongly_connected_components(e)[:1]:",
            cycles,
        )
    )
    # A code the reference documents do not name is a finding nobody can look up.
    cases.append(
        Mutation(
            "docs-code-omitted",
            "packages/crongx/README.md",
            "| `non-finite-time` | error |",
            "| `time-not-finite` | error |",
            KIT_TEST + "test_docs.py::test_every_problem_code_is_documented_for_its_tool",
        )
    )
    # An artifact that exits with success is a load failure on every route, the
    # umbrella's and each tool's own.
    cases.append(
        Mutation(
            "direct-tool-artifact-exit-bypass",
            "packages/gxcore/src/gxcore/cli.py",
            "    except SystemExit as e:",
            "    except Exception as e:",
            # One case, so the kill is a named assertion rather than 112
            # failures whose summary pytest elides.
            KIT_TEST
            + "test_robustness.py::test_malformed_input_exits_2_not_traceback"
            + "[exits-zero-while-loading-chartgx]",
        )
    )
    # The baseline contract holds for every tool: accepting an artifact and
    # re-inspecting it reports nothing new.
    cases.append(
        Mutation(
            "baseline-records-nothing",
            "packages/gxcore/src/gxcore/baseline.py",
            "        return cls(name=report.name, problems=[_record(p) for p in report.sorted()])",
            "        return cls(name=report.name, problems=[])",
            KIT_TEST + "test_contract.py::test_a_baseline_round_trips_for_every_tool[chartgx]",
        )
    )
    # An upload with no retention accumulates silently in a repository nobody
    # looks at; 148 artifacts and ~53 MB had built up before anyone did.
    cases.append(
        Mutation(
            "artifact-retention-removed",
            ".github/workflows/ci.yml",
            "          retention-days: 7\n",
            "",
            KIT_TEST + "test_repo.py::test_every_uploaded_artifact_expires",
        )
    )
    # The declared-chart route must refuse what it cannot read, and must report
    # the defect it finds under the tool's existing code.
    cases.extend(
        [
            Mutation(
                "declared-model-unknown-key-ignored",
                "packages/chartgx/src/chartgx/model.py",
                '    if unknown:\n        raise InvalidModel(f"{path}: unrecognised key(s) {unknown}")',
                "    if False:\n        pass",
                "packages/chartgx/tests/test_model_route.py::test_a_declaration_that_cannot_be_read_is_refused_where_it_is_wrong",
            ),
            Mutation(
                "off-canvas-box-not-clamped",
                "packages/gxcore/src/gxcore/storyboard.py",
                "    x = max(0.0, min(box[0], max(0.0, width - tw - 8)))",
                "    x = max(0.0, box[0])",
                "packages/gxcore/tests/test_more.py::test_every_number_the_report_lists_is_drawn_even_when_its_box_is_off_canvas",
            ),
            Mutation(
                "numbers-not-compressed",
                "packages/gxcore/src/gxcore/storyboard.py",
                '        runs.append(f"{start}" if start == previous else f"{start}-{previous}")\n    return ",".join(runs)',
                '        runs.append(f"{start}" if start == previous else f"{start},{previous}")\n    return ",".join(runs)',
                "packages/gxcore/tests/test_more.py::test_a_shared_box_names_its_numbers_as_ranges",
            ),
            Mutation(
                "self-loop-not-clamped",
                "packages/gxcore/src/gxcore/diagram.py",
                "    if low < margin:\n        return margin - low",
                "    if False:\n        return margin - low",
                "packages/gxcore/tests/test_more.py::test_a_self_loop_stays_inside_the_canvas",
            ),
            Mutation(
                "blank-label-drawn-as-blank",
                "packages/gxcore/src/gxcore/diagram.py",
                '        font, shown = _fit(draw, label if label.strip() else "?", r * 1.7, r * 0.55)',
                "        font, shown = _fit(draw, label, r * 1.7, r * 0.55)",
                "packages/gxcore/tests/test_more.py::test_a_node_whose_name_is_only_spaces_shows_a_marker",
            ),
            Mutation(
                "unwritable-output-drops-the-report",
                "packages/gxcore/src/gxcore/cli.py",
                "                failed_output = True",
                "                return 2",
                "packages/gxkit/tests/test_inspection_gates.py::test_an_unwritable_output_still_prints_the_report",
            ),
            Mutation(
                # The set is a pure performance change, so no mutation of *it* is
                # observable; what is observable is the deduplication it computes, and
                # that is what this mutant breaks.
                "state-dedupe-never-remembers",
                "packages/flowgx/src/flowgx/machine.py",
                "                known.add(s)\n                seen.append(s)",
                "                seen.append(s)",
                "packages/gxcore/tests/test_more.py::test_states_are_deduplicated_in_first_seen_order",
            ),
            Mutation(
                "crongx-run-fields-unchecked",
                "packages/crongx/src/crongx/model.py",
                '        validate_number(self.start, field="start")',
                "        pass",
                "packages/gxkit/tests/test_declaration_inputs.py::test_a_model_built_with_a_wrong_typed_field_is_refused_where_it_is_set",
            ),
            Mutation(
                "flowgx-states-unchecked",
                "packages/flowgx/src/flowgx/machine.py",
                '        validate_names(self.states, field="states")',
                "        pass",
                "packages/gxkit/tests/test_declaration_inputs.py::test_a_model_built_with_a_wrong_typed_field_is_refused_where_it_is_set",
            ),
            Mutation(
                "docgx-width-unchecked",
                "packages/docgx/src/docgx/model.py",
                '        validate_number(self.width, field="width", integer=True)',
                "        pass",
                "packages/gxkit/tests/test_declaration_inputs.py::test_a_model_built_with_a_wrong_typed_field_is_refused_where_it_is_set",
            ),
            Mutation(
                # A guard in the other direction: validating the *value* would take the
                # finding away, so the mutation restores that validation.
                "seed-value-validated-again",
                "packages/seedgx/src/seedgx/model.py",
                '        validate_names([self.name], field="name")',
                '        validate_names([self.name], field="name")\n'
                '        validate_optional_number(self.seed, field="seed", integer=True)',
                "packages/gxkit/tests/test_declaration_inputs.py::test_a_value_the_tool_has_a_finding_for_is_not_refused_at_construction",
            ),
            Mutation(
                # The one-BFS form of "what can any principal reach" (measured: 2 000
                # principals spent 1.8 s unioning one traversal each).
                "reachable-from-principals-per-principal",
                "packages/authzgx/src/authzgx/authmodel.py",
                "        return reachable(edges, [self.pid(p) for p in self.principals])",
                "        out: set[str] = set()\n"
                "        for p in self.principals:\n"
                "            out |= reachable(edges, [self.pid(p)])\n"
                "        return out",
                "packages/authzgx/tests/test_auth.py::test_the_escalation_check_does_not_traverse_once_per_principal",
            ),
            Mutation(
                # The empty-role question asked per role (one traversal and one graph
                # per role) instead of once for all of them.
                "empty-role-asked-per-role",
                "packages/authzgx/src/authzgx/checks.py",
                "        if model.rid(role) not in reaches_a_permission:",
                "        if not any(\n"
                "            model.xid(x) in can_reach(graph, [model.rid(role)])\n"
                "            for x in model.permissions\n"
                "        ):",
                "packages/authzgx/tests/test_auth.py::test_the_escalation_check_does_not_traverse_once_per_principal",
            ),
            Mutation(
                # The forward form for every principal, where the reverse one answers
                # all of them at once. Same findings either way — the guard is the
                # traversal count, which is the thing that was wrong.
                "effective-set-asked-per-principal",
                "packages/authzgx/src/authzgx/checks.py",
                "            if len(escalating) > len(model.permissions)",
                "            if False",
                "packages/authzgx/tests/test_auth.py::test_the_escalation_check_does_not_traverse_once_per_principal",
            ),
            Mutation(
                "effective-map-ignores-the-asked-subset",
                "packages/authzgx/src/authzgx/authmodel.py",
                "        wanted = list(self.principals if principals is None else principals)",
                "        wanted = list(self.principals)",
                "packages/authzgx/tests/test_auth.py::test_effective_map_agrees_with_effective",
            ),
            Mutation(
                "route-map-does-not-seed-its-targets",
                "packages/gxcore/src/gxcore/graph.py",
                "    hop: dict[_H, _H] = {t: t for t in ordered}",
                "    hop: dict[_H, _H] = {}",
                "packages/gxcore/tests/test_graph_properties.py::test_route_to_matches_networkx",
            ),
            Mutation(
                "the-way-in-is-not-walked",
                "packages/gxcore/src/gxcore/graph.py",
                "    if start not in hop:\n        return None",
                "    if True:\n        return None",
                "packages/gxcore/tests/test_graph_properties.py::test_route_nodes_walks_the_map_and_refuses_what_is_not_in_it",
            ),
            Mutation(
                "overlap-rule-back-to-every-pair",
                "packages/gxcore/src/gxcore/layout.py",
                "        if covering > cell_budget:",
                "        if True:",
                "packages/gxcore/tests/test_core.py::test_the_overlap_rule_does_not_compare_every_pair",
            ),
            Mutation(
                "oversized-box-left-out-of-the-grid",
                "packages/gxcore/src/gxcore/layout.py",
                "            candidates = list(range(index))",
                "            candidates = []",
                "packages/gxcore/tests/test_geometry_properties.py::test_the_grid_finds_exactly_the_pairs_the_rule_defines",
            ),
            Mutation(
                "crongx-overlap-sweep-back-to-pairs",
                "packages/crongx/src/crongx/checks.py",
                "        open_runs = [index for index in open_runs if schedule.runs[index].end > b.start]",
                "        open_runs = list(open_runs) + [index for index in open_runs]",
                "packages/crongx/tests/test_schedules.py::test_the_overlap_rule_is_not_quadratic",
            ),
            Mutation(
                "flag-coerced-from-a-string",
                "packages/gxcore/src/gxcore/loading.py",
                "    if not isinstance(value, bool):",
                "    if False:",
                "packages/gxkit/tests/test_declaration_inputs.py::test_a_flag_that_is_not_a_flag_is_refused",
            ),
            Mutation(
                "pair-arity-truncated",
                "packages/gxcore/src/gxcore/loading.py",
                "        if not isinstance(item, (list, tuple)) or len(item) != arity:",
                "        if not isinstance(item, (list, tuple)) or len(item) < arity:",
                "packages/gxkit/tests/test_declaration_inputs.py::test_a_pair_list_keeps_its_arity",
            ),
            Mutation(
                "mapping-accepts-a-string",
                "packages/gxcore/src/gxcore/loading.py",
                '    if not isinstance(value, dict):\n        raise InvalidArtifact(f"{field}: expected a mapping, not {value!r}")',
                "    if False:\n        pass",
                "packages/gxkit/tests/test_declaration_inputs.py::test_a_mapping_is_a_mapping",
            ),
            Mutation(
                "netgx-dict-route-shape-falls-through",
                "packages/netgx/src/netgx/model.py",
                '            nodes=convert_mapping(value.get("nodes", {}), field="nodes"),',
                '            nodes={str(k): str(v) for k, v in value.get("nodes", {}).items()},',
                "packages/gxkit/tests/test_declaration_inputs.py::test_netgx_refuses_a_malformed_network_dict_instead_of_reading_another_attr",
            ),
            Mutation(
                "flowgx-string-states-exploded",
                "packages/flowgx/src/flowgx/machine.py",
                '                states=convert_names(\n                    getattr(module, "STATES", getattr(module, "states", [])), field="STATES"\n                ),',
                '                states=list(getattr(module, "STATES", getattr(module, "states", []))),',
                "packages/gxkit/tests/test_declaration_inputs.py::test_flowgx_refuses_a_state_list_that_is_a_string",
            ),
            Mutation(
                "docgx-blocks-string-exploded",
                "packages/docgx/src/docgx/model.py",
                '                blocks=convert_items(blocks or [], _block, field="BLOCKS"),',
                "                blocks=[_block(b) for b in (blocks or [])],",
                "packages/gxkit/tests/test_declaration_inputs.py::test_docgx_refuses_blocks_that_are_not_a_list",
            ),
            Mutation(
                "chartgx-log-bars-invisible",
                "packages/chartgx/src/chartgx/checks.py",
                "        for j, patch in enumerate(ax.patches):\n            if float(patch.get_height()) <= 0:",
                "        for j, patch in enumerate([]):\n            if float(patch.get_height()) <= 0:",
                "packages/gxkit/tests/test_declaration_inputs.py::test_chartgx_reports_a_bar_on_a_log_axis_from_the_figure_route",
            ),
            Mutation(
                "schemagx-roots-assumed-modelled",
                "packages/schemagx/src/schemagx/checks.py",
                "        if table in schema.roots or not schema.roots_modelled:",
                "        if table in schema.roots:",
                "packages/gxkit/tests/test_declaration_inputs.py::test_schemagx_does_not_report_orphans_for_a_schema_without_declared_roots",
            ),
            Mutation(
                "self-loop-cycle-skipped",
                "packages/gxcore/src/gxcore/graph.py",
                "            if not self_loops or only is None or only not in e.get(only, ()):",
                "            if True:",
                "packages/gxcore/tests/test_core.py::test_a_self_loop_is_a_cycle_only_where_the_domain_says_so",
            ),
            Mutation(
                "pair-rule-uses-the-larger-box",
                "packages/gxcore/src/gxcore/geometry.py",
                "            frac = max(covered(boxes[i], boxes[j]), covered(boxes[j], boxes[i]))",
                "            frac = min(covered(boxes[i], boxes[j]), covered(boxes[j], boxes[i]))",
                "packages/gxcore/tests/test_core.py::test_the_geometry_pair_rule_is_the_fraction_of_the_smaller_box",
            ),
            Mutation(
                "same-text-position-ignored",
                "packages/gxcore/src/gxcore/layout.py",
                "            if x.text.strip() == y.text.strip() and x.bbox == y.bbox:",
                "            if x.text.strip() == y.text.strip():",
                "packages/gxcore/tests/test_core.py::test_two_identically_labelled_boxes_that_do_not_share_a_place_still_collide",
            ),
            Mutation(
                "null-identity-crashes-compare",
                "packages/gxcore/src/gxcore/baseline.py",
                '    identity = record.get("identity") or ()',
                '    identity = record.get("identity")',
                "packages/gxcore/tests/test_baseline.py::test_a_null_identity_is_no_identity_rather_than_a_crash",
            ),
            Mutation(
                "diagram-label-keeps-its-newline",
                "packages/gxcore/src/gxcore/diagram.py",
                "        label = one_line(node.text)",
                "        label = node.text",
                "packages/gxcore/tests/test_more.py::test_a_label_with_a_newline_is_flattened_rather_than_losing_the_image",
            ),
            Mutation(
                "storyboard-non-finite-box-rounded",
                "packages/gxcore/src/gxcore/storyboard.py",
                "        if any(not math.isfinite(value) for value in problem.bbox):",
                "        if False:",
                "packages/gxcore/tests/test_more.py::test_a_finding_with_an_unplaceable_box_does_not_lose_the_whole_storyboard",
            ),
            Mutation(
                # Removing the trap itself cannot be caught by an in-process test —
                # the mutant kills the runner, which is the point of the rule. The
                # refusal's *report* is what the test can hold it to, and the trap's
                # behaviour is proven by the test passing at all.
                "artifact-exit-refusal-unreported",
                "packages/gxcore/src/gxcore/loading.py",
                '        raise InvalidArtifact(f"the artifact called os._exit({code!r}) while loading")',
                '        raise InvalidArtifact(f"exit {code!r}")',
                "packages/gxkit/tests/test_inspection_gates.py::test_an_artifact_that_ends_the_process_is_a_refusal_not_a_verdict",
            ),
            Mutation(
                "non-file-artifact-read-anyway",
                "packages/gxcore/src/gxcore/loading.py",
                '    if not path.is_file():\n        raise InvalidArtifact(f"{path}: not a regular file, so there is nothing to read")',
                "    if False:\n        pass",
                "packages/gxcore/tests/test_loading.py::test_a_fifo_is_refused_rather_than_waited_on",
            ),
            Mutation(
                "config-code-name-unchecked",
                "packages/gxcore/src/gxcore/config.py",
                "    if known is not None:\n        unknown = sorted(names - set(known))",
                "    if False:\n        unknown = []",
                "packages/gxcore/tests/test_config.py::test_a_code_name_that_names_no_code_is_refused",
            ),
            Mutation(
                "baseline-provenance-unchecked",
                "packages/gxcore/src/gxcore/cli.py",
                "            if known and codes and not (codes & known):",
                "            if False:",
                "packages/gxkit/tests/test_inspection_gates.py::test_a_baseline_for_another_tool_is_refused_rather_than_compared",
            ),
            Mutation(
                "multi-artifact-routed-to-first",
                "packages/gxkit/src/gxkit/cli.py",
                "    if len(found) > 1:",
                "    if False:",
                "packages/gxkit/tests/test_inspection_gates.py::test_a_file_declaring_two_artifacts_is_not_routed_to_one_of_them",
            ),
            Mutation(
                # Swapping the clause cannot mutate anything: an earlier
                # `except SystemExit` already exists, so the copy would be dead. The
                # *code* the interrupt reports is what the test can hold.
                "interrupt-reported-as-a-plain-refusal",
                "packages/gxcore/src/gxcore/cli.py",
                '        print(f"{tool.name}: interrupted", file=sys.stderr)\n        return 130',
                '        print(f"{tool.name}: {tool.name} failed", file=sys.stderr)\n        return 2',
                "packages/gxkit/tests/test_inspection_gates.py::test_an_interrupt_is_the_shells_code_without_a_traceback",
            ),
            Mutation(
                "openapi-response-entry-unchecked",
                "packages/apigx/src/apigx/openapi.py",
                "                if not isinstance(value, dict):",
                "                if False:",
                "packages/apigx/tests/test_openapi.py::test_a_response_entry_that_is_not_an_object_is_refused_with_its_status",
            ),
            Mutation(
                "declared-model-non-finite-error-accepted",
                "packages/chartgx/src/chartgx/model.py",
                "                if any(not math.isfinite(value) for value in magnitudes):",
                "                if False:",
                "packages/chartgx/tests/test_model_route.py::test_a_non_finite_value_cannot_be_placed",
            ),
            Mutation(
                "declared-model-truncated-baseline-missed",
                "packages/chartgx/src/chartgx/model.py",
                "        if minimum is not None and minimum > 0:",
                "        if False:",
                "packages/chartgx/tests/test_model_route.py::test_a_truncated_baseline_is_the_same_code_the_figure_route_uses",
            ),
            Mutation(
                "skip-instead-of-asserting",
                "packages/levelgx/tests/test_levels.py",
                '    assert_fires(r, "soft-lock", ERROR)',
                '    import pytest; pytest.skip("dodging the assertion")',
                "packages/levelgx/tests/test_levels.py::test_softlock_is_an_error",
            ),
            Mutation(
                "openapi-extension-becomes-an-endpoint",
                "packages/apigx/src/apigx/openapi.py",
                '        if str(path).lower().startswith("x-"):\n            continue\n',
                "",
                "packages/apigx/tests/test_openapi.py::test_a_specification_extension_in_paths_is_not_a_route",
            ),
            Mutation(
                "openapi-ranged-status-dropped",
                "packages/apigx/src/apigx/openapi.py",
                "        if isinstance(key, str) and key.upper() in _RANGES:",
                "        if False:",
                "packages/apigx/tests/test_openapi.py::test_a_ranged_response_key_documents_its_errors",
            ),
            Mutation(
                "openapi-malformed-security-read-as-anonymous",
                "packages/apigx/src/apigx/openapi.py",
                '        if "security" in holder and not isinstance(holder["security"], list):',
                "        if False:",
                "packages/apigx/tests/test_openapi.py::test_a_malformed_security_block_is_refused_rather_than_read_as_anonymous",
            ),
            Mutation(
                "openapi-responses-optional",
                "packages/apigx/src/apigx/openapi.py",
                '            if "responses" not in operation:',
                "            if False:",
                "packages/apigx/tests/test_openapi.py::test_a_response_list_is_required",
            ),
            Mutation(
                "mermaid-note-any-word",
                "packages/flowgx/src/flowgx/mermaid.py",
                "    if not NOTE.match(line):",
                "    if not re.match(r'^\\s*note\\b', line, re.IGNORECASE):",
                "packages/flowgx/tests/test_machines.py::test_a_state_named_note_keeps_its_transition",
            ),
            Mutation(
                "mermaid-marker-target-becomes-a-state",
                "packages/flowgx/src/flowgx/mermaid.py",
                "            if target_state == INITIAL:",
                "            if False:",
                "packages/flowgx/tests/test_machines.py::test_both_ends_being_the_marker_is_refused",
            ),
            Mutation(
                "declared-scale-typo-falls-back",
                "packages/chartgx/src/chartgx/model.py",
                "        if scale_field in model and model[scale_field] not in SCALES:",
                "        if False:",
                "packages/chartgx/tests/test_model_route.py::test_the_closed_sets_and_types_are_checked_where_the_model_is_read",
            ),
            Mutation(
                "declared-heatmap-axis-setting-silent",
                "packages/chartgx/src/chartgx/model.py",
                '    if model.get("y_min") is not None or model.get("y_scale") == "log":',
                "    if False:",
                "packages/chartgx/tests/test_model_route.py::test_colour_is_not_a_length_but_the_axis_setting_still_cannot_apply",
            ),
            Mutation(
                "ddl-string-literal-is-sql",
                "packages/schemagx/src/schemagx/ddl.py",
                "            masked_rest = _mask_literals(rest)\n",
                "            masked_rest = rest\n",
                "packages/schemagx/tests/test_ddl.py::test_a_string_literal_is_not_sql",
            ),
            Mutation(
                "ddl-index-clause-is-a-column",
                "packages/schemagx/src/schemagx/ddl.py",
                "            if INDEX_CLAUSE.match(item):",
                "            if False:",
                "packages/schemagx/tests/test_ddl.py::test_an_index_clause_is_not_a_column",
            ),
            Mutation(
                "ddl-table-options-refused",
                "packages/schemagx/src/schemagx/ddl.py",
                "            option = TABLE_OPTIONS.match(cleaned, position)",
                "            option = None",
                "packages/schemagx/tests/test_ddl.py::test_a_table_option_is_read_and_recorded_rather_than_refused",
            ),
            Mutation(
                "netgx-sensitive-list-falls-back",
                "packages/netgx/src/netgx/model.py",
                "        if self.sensitive:",
                "        if False:",
                "packages/netgx/tests/test_networks.py::test_a_declared_sensitive_list_is_never_replaced_by_the_data_kind_fallback",
            ),
            Mutation(
                "framegx-all-black-by-mean",
                "packages/framegx/src/framegx/checks.py",
                "    if float(np.max(peaks)) < _BLACK_LEVEL:",
                "    if float(np.mean(frames.reshape(n, -1))) < _BLACK_LEVEL:",
                "packages/framegx/tests/test_video.py::test_a_visible_mark_on_black_is_not_a_black_frame",
            ),
            Mutation(
                "schemagx-no-pk-reference-silent",
                "packages/schemagx/src/schemagx/checks.py",
                "        elif pk is None:",
                "        elif False:",
                "packages/schemagx/tests/test_schemas.py::test_a_reference_to_a_table_with_no_primary_key_cannot_be_to_one",
            ),
            Mutation(
                "pipegx-self-need-unchecked",
                "packages/pipegx/src/pipegx/checks.py",
                "        if step.name in step.needs:",
                "        if False:",
                "packages/pipegx/tests/test_pipelines.py::test_a_step_that_needs_itself_is_a_cycle_not_a_clean_pipeline",
            ),
            Mutation(
                "chartgx-categorical-x-skips-the-line",
                "packages/chartgx/src/chartgx/checks.py",
                "artist.get_xydata()",
                "np.column_stack((artist.get_xdata(), artist.get_ydata()))",
                "packages/chartgx/tests/test_charts.py::test_clipped_data_is_reported_whatever_the_x_axis_is",
            ),
            Mutation(
                "flowgx-identical-duplicate-is-ambiguity",
                "packages/flowgx/src/flowgx/checks.py",
                "            if len(destinations) < 2:",
                "            if False:",
                "packages/flowgx/tests/test_machines.py::test_identical_duplicate_transitions_are_not_ambiguity",
            ),
            Mutation(
                "protogx-single-destination-is-nondeterminism",
                "packages/protogx/src/protogx/checks.py",
                "        if len(destinations) > 1:",
                "        if len(destinations) >= 1:",
                "packages/protogx/tests/test_protocols.py::test_the_same_transition_twice_is_not_nondeterminism",
            ),
            Mutation(
                "depsgx-self-edge-counts-as-a-user",
                "packages/depsgx/src/depsgx/checks.py",
                "            users = [src for src in reverse_edges.get(module, []) if src != module]",
                "            users = reverse_edges.get(module, [])",
                "packages/depsgx/tests/test_modules.py::test_a_self_edge_is_not_a_user_of_the_module",
            ),
            Mutation(
                "docgx-title-words-uncounted",
                "packages/docgx/src/docgx/checks.py",
                "    words = len(page.title.split()) + sum(len(b.text.split()) for b in page.blocks)",
                "    words = sum(len(b.text.split()) for b in page.blocks)",
                "packages/docgx/tests/test_pages.py::test_the_word_budget_counts_the_title",
            ),
            Mutation(
                "seedgx-noninteger-seed-refused-at-load",
                "packages/seedgx/src/seedgx/model.py",
                "    if value is None or isinstance(value, (int, float, str)):",
                "    if value is None or (isinstance(value, int) and not isinstance(value, bool)):",
                "packages/gxkit/tests/test_input_boundaries.py::test_seed_declarations_report_noninteger_values_without_truncation",
            ),
            Mutation(
                "baseline-identity-shape-unchecked",
                "packages/gxcore/src/gxcore/baseline.py",
                "            if identity is not None and (",
                "            if False and (",
                "packages/gxcore/tests/test_baseline.py::test_a_record_shape_that_would_match_wrongly_is_refused_with_field_and_index",
            ),
            Mutation(
                "config-table-name-unchecked",
                "packages/gxcore/src/gxcore/config.py",
                "        if known_tools is not None and name not in known_tools:",
                "        if False:",
                "packages/gxcore/tests/test_config.py::test_a_table_that_names_no_tool_is_refused_when_the_caller_knows_the_family",
            ),
            Mutation(
                "apigx-root-key-unchecked",
                "packages/apigx/src/apigx/openapi.py",
                "    unknown = _unrecognised(document, ROOT_KEYS)",
                "    unknown = []",
                "packages/apigx/tests/test_openapi.py::test_a_key_nothing_reads_is_refused_wherever_it_sits",
            ),
            Mutation(
                "schemagx-not-modelled-silent",
                "packages/schemagx/src/schemagx/ddl.py",
                "        if seen_not_modelled:",
                "        if False:",
                "packages/schemagx/tests/test_ddl.py::test_a_clause_the_model_cannot_carry_is_reported_not_dropped",
            ),
            Mutation(
                "cli-output-skip-ignored",
                "packages/gxcore/src/gxcore/cli.py",
                """        except Exception as exc:
            if args.output:""",
                """        except Exception as exc:
            if False:""",
                "packages/gxkit/tests/test_contract_conformance.py::test_a_requested_storyboard_that_cannot_be_drawn_is_refused",
            ),
            Mutation(
                "trace-codes-column-unlabelled",
                "docs/TRACE.md",
                "| tool | inspects | reads | module | codes (#) | examples |",
                "| tool | inspects | reads | module | codes | examples |",
                "packages/gxkit/tests/test_contract_conformance.py::test_the_trace_table_labels_its_codes_column_as_a_count",
            ),
            Mutation(
                "report-omits-a-documented-key",
                "packages/gxcore/src/gxcore/model.py",
                '            "details": list(self.details),\n',
                "",
                "packages/gxkit/tests/test_contract_conformance.py::test_the_json_report_carries_the_documented_keys",
            ),
            Mutation(
                "warn-becomes-an-error",
                "packages/gxcore/src/gxcore/model.py",
                'WARN = "warn"',
                'WARN = "error"',
                "packages/gxkit/tests/test_contract_conformance.py::test_a_warn_or_info_never_fails_a_build",
            ),
            Mutation(
                "readme-link-dangling-unanchored",
                "README.md",
                "[`docs/TRACE.md`](docs/TRACE.md)",
                "[`docs/TRACE.md`](docs/NOTHING.md)",
                "packages/gxkit/tests/test_docs.py::test_no_broken_internal_link",
            ),
            Mutation(
                "readme-transcript-drift",
                "packages/apigx/src/apigx/checks.py",
                '                    WARN,\n                    "path-outside-base",',
                '                    INFO,\n                    "path-outside-base",',
                "packages/gxkit/tests/test_docs.py::test_a_tool_readme_shows_a_transcript_it_can_still_produce",
            ),
            Mutation(
                "hero-domains-hardcoded",
                "docs/hero/hero_domains.py",
                """    return sorted(
        path.name
        for path in (ROOT / "packages").iterdir()
        if (path / "pyproject.toml").exists() and path.name not in {"gxcore", "gxkit"}
    )""",
                """    return [
        "apigx",
        "authzgx",
        "chartgx",
        "crongx",
        "depsgx",
        "docgx",
        "envgx",
        "flowgx",
        "framegx",
        "levelgx",
        "netgx",
        "pipegx",
        "protogx",
        "schemagx",
        "seedgx",
    ]""",
                "packages/gxkit/tests/test_docs.py::test_the_hero_draws_one_cube_per_tool",
            ),
            Mutation(
                "hero-manifest-stale",
                "docs/assets/hero.json",
                '"domains": 17,',
                '"domains": 10,',
                "packages/gxkit/tests/test_docs.py::test_the_committed_hero_matches_what_was_rendered",
            ),
            Mutation(
                "hero-assumes-no-projection-squash",
                "docs/hero/hero_domains.py",
                "SQUASH = 0.81",
                "SQUASH = 1.0",
                "packages/gxkit/tests/test_docs.py::test_the_hero_cannot_crowd_its_cubes",
            ),
            Mutation(
                "hero-leaves-no-room-for-the-title",
                "docs/hero/hero_domains.py",
                "TEXT_BAND_PX = 190.0",
                "TEXT_BAND_PX = 0.0",
                "packages/gxkit/tests/test_docs.py::test_the_hero_leaves_room_for_its_title",
            ),
            Mutation(
                "hero-green-in-palette",
                "docs/hero/hero_domains.py",
                '    "#2563eb",',
                '    "#22c55e",',
                "packages/gxkit/tests/test_docs.py::test_the_hero_draws_one_cube_per_tool",
            ),
            Mutation(
                "authzgx-dangling-low-skipped",
                "packages/authzgx/src/authzgx/checks.py",
                "            if name not in known:",
                "            if False:",
                "packages/authzgx/tests/test_auth.py::test_a_declared_list_that_names_nothing_is_reported",
            ),
            Mutation(
                "netgx-dangling-sensitive-skipped",
                "packages/netgx/src/netgx/checks.py",
                "        if node not in declared:\n            out.append(",
                "        if False:\n            out.append(",
                "packages/netgx/tests/test_networks.py::test_a_sensitive_name_that_is_not_a_node_is_reported",
            ),
            Mutation(
                "depsgx-dangling-rule-skipped",
                "packages/depsgx/src/depsgx/checks.py",
                '        ("forbidden", [name for pair in graph.forbidden for name in pair]),',
                '        ("forbidden", []),',
                "packages/depsgx/tests/test_modules.py::test_a_declared_rule_that_names_nothing_is_reported",
            ),
            Mutation(
                "schemagx-dangling-root-skipped",
                "packages/schemagx/src/schemagx/checks.py",
                "    for table in schema.roots:\n        if table not in declared:",
                "    for table in []:\n        if False:",
                "packages/schemagx/tests/test_schemas.py::test_a_root_that_is_not_a_table_is_reported",
            ),
            Mutation(
                "protogx-dangling-request-skipped",
                "packages/protogx/src/protogx/checks.py",
                "    for request in proto.requests:\n        if proto.messages and request not in proto.messages:",
                "    for request in []:\n        if proto.messages and request not in proto.messages:",
                "packages/protogx/tests/test_protocols.py::test_a_statement_about_a_state_or_message_that_does_not_exist_is_reported",
            ),
            Mutation(
                "flowgx-dangling-accept-skipped",
                "packages/flowgx/src/flowgx/checks.py",
                "    for s in dict.fromkeys(machine.accept):\n        if declared and s not in declared:",
                "    for s in []:\n        if declared and s not in declared:",
                "packages/flowgx/tests/test_machines.py::test_an_accepting_state_that_is_not_a_state_is_reported",
            ),
            Mutation(
                "declared-model-empty-mark-silent",
                "packages/chartgx/src/chartgx/model.py",
                "            if not points:\n"
                '                report_problem("empty-chart", f"{kind} mark declares no points to draw", target)',
                "            pass",
                "packages/chartgx/tests/test_model_route.py::test_an_empty_mark_is_an_error_rather_than_a_clean_report",
            ),
            Mutation(
                "declared-model-short-line-accepted",
                "packages/chartgx/src/chartgx/model.py",
                '            if kind == "line" and len(points) == 1:',
                "            if False:",
                "packages/chartgx/tests/test_model_route.py::test_a_one_point_line_is_short_rather_than_empty",
            ),
            Mutation(
                "declared-model-mark-field-unchecked",
                "packages/chartgx/src/chartgx/model.py",
                "        unknown = sorted(key for key in mark if key not in MARK_FIELDS[str(kind)])\n"
                "        if unknown:\n"
                "            raise InvalidModel(\n"
                '                f"{path}: marks[{index}] has unrecognised key(s) {unknown} for a {kind} mark"\n'
                "            )",
                "        unknown = []",
                "packages/chartgx/tests/test_model_route.py::test_an_unknown_field_inside_a_mark_is_refused_not_ignored",
            ),
            Mutation(
                "declared-model-heatmap-ragged-accepted",
                "packages/chartgx/src/chartgx/model.py",
                """                if len(row) != width:
                    report_problem(
                        "mismatched-lengths",
                        f"heatmap row {position} has {len(row)} cells for {width} columns",
                        target,
                    )""",
                "                pass",
                "packages/chartgx/tests/test_model_route.py::test_a_ragged_matrix_disagrees_with_itself",
            ),
            Mutation(
                "declared-model-ambiguous-labels-unchecked",
                "packages/chartgx/src/chartgx/model.py",
                "    if len(named) > 1 and any(labels != named[0] for labels in named):",
                "    if False:",
                "packages/chartgx/tests/test_model_route.py::test_two_names_for_one_axis_are_refused_rather_than_picked_between",
            ),
            Mutation(
                "declared-model-lengths-unchecked",
                "packages/chartgx/src/chartgx/model.py",
                '                expected = len(points) if shape == "symmetric" else len(points) * 2',
                "                expected = len(magnitudes)",
                "packages/chartgx/tests/test_model_route.py::test_error_magnitudes_must_match_the_points",
            ),
            Mutation(
                "declared-model-storyboard-faked",
                "packages/chartgx/src/chartgx/tool.py",
                """        raise ValueError(
            "a declared model has no storyboard here: box numbers are drawn over a "
            "matplotlib figure's artists, which a declaration does not have. The "
            "renderer that owns the model can draw one — `figspec storyboard "
            "model.json -o model.storyboard.svg` boxes the marks these findings name"
        )""",
                "        return Image.new('RGB', (1, 1))",
                "packages/chartgx/tests/test_model_route.py::test_the_tool_dispatches_a_declaration_without_touching_matplotlib",
            ),
        ]
    )
    # An exposure route is identified by the route: the first one was reported
    # alone, and a baseline could not see the route change.
    cases.extend(
        [
            Mutation(
                "netgx-first-exposure-route-only",
                "packages/netgx/src/netgx/checks.py",
                "                        identity=(entry, sensitive),\n                    )\n                )",
                "                        identity=(entry, sensitive),\n                    )\n                )\n                break",
                "packages/netgx/tests/test_networks.py::test_every_public_entry_that_reaches_a_sensitive_node_is_reported",
            ),
            Mutation(
                "netgx-exposure-route-unidentified",
                "packages/netgx/src/netgx/checks.py",
                "                        identity=(entry, sensitive),\n",
                "",
                "packages/netgx/tests/test_networks.py::test_a_replaced_exposure_route_is_new_debt",
            ),
        ]
    )
    # The identity inventory is a ratchet: a new finding that cannot be told apart
    # from its sibling is refused until someone gives it a target or an identity.
    cases.append(
        Mutation(
            "identity-debt-grows",
            "packages/seedgx/src/seedgx/checks.py",
            "    report.problems = out",
            '    out.append(Problem(ERROR, "missing-seed", "a finding with no location"))\n    report.problems = out',
            "packages/gxkit/tests/test_identity_inventory.py::test_no_finding_that_can_repeat_is_indistinguishable",
        )
    )
    # Each relationship identity must be load-bearing: removing it makes a
    # replaced relationship read as unchanged debt.
    identities = "packages/gxkit/tests/test_relationship_identities.py::"
    for name, path, before in [
        (
            "identity-pipeline-goal",
            "packages/pipegx/src/pipegx/checks.py",
            "                    identity=(goal,),\n",
        ),
        (
            "identity-protogx-message",
            "packages/protogx/src/protogx/checks.py",
            "                    identity=(message,),\n",
        ),
        (
            "identity-authzgx-grant",
            "packages/authzgx/src/authzgx/checks.py",
            '                    identity=(f"grant:{role}:{perm}", "role", role),\n',
        ),
        (
            "identity-schemagx-fk",
            "packages/schemagx/src/schemagx/checks.py",
            '                    identity=(child, parent, "parent-column", pc),\n',
        ),
    ]:
        cases.append(
            Mutation(
                name,
                path,
                before,
                "",
                identities + "test_a_pipeline_with_two_unproduced_goals_reports_two"
                if name.endswith("goal")
                else identities + "test_a_protocol_with_two_unhandled_messages_reports_two"
                if "message" in name
                else identities + "test_two_dangling_grants_are_two_findings"
                if "grant" in name
                else identities + "test_two_dangling_foreign_keys_are_two_findings",
            )
        )
    # The coverage gate must be provable in both directions: an environment
    # override cannot disable it, and a failing run cannot be discarded.
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    marker = "      - name: Tests with a coverage floor\n"
    assert workflow.count(marker) == 1
    cases.append(
        Mutation(
            "coverage-disabled-by-environment",
            ".github/workflows/ci.yml",
            marker,
            marker + '        env:\n          PYTEST_ADDOPTS: "--no-cov"\n',
            coverage_test,
        )
    )
    cases.append(
        Mutation(
            "coverage-failure-swallowed",
            "scripts/check.sh",
            floor,
            floor + " || true",
            coverage_test,
        )
    )
    # Artist visibility is not render eligibility: the real pilot chart offered
    # tick 350 but never drew it. The oracle observes Text.draw, not our selector.
    chart_text = "packages/chartgx/tests/test_rendered_text.py::"
    chart_checks = "packages/chartgx/src/chartgx/checks.py"
    cases.extend(
        [
            Mutation(
                "chart-undrawn-ticks-inspected",
                chart_checks,
                "for tick in axis._update_ticks():",
                "for tick in axis.get_major_ticks() + axis.get_minor_ticks():",
                chart_text + "test_valid_pilot_chart_has_no_errors_from_undrawn_tick",
            ),
            Mutation(
                "chart-minor-labels-ignored",
                chart_checks,
                "for tick in axis._update_ticks():",
                "for tick in (t for t in axis._update_ticks() if t in axis.majorTicks):",
                chart_text + "test_selected_ticks_match_actual_draw_calls",
            ),
            Mutation(
                "chart-hidden-axes-text-inspected",
                chart_checks,
                "    if not ax.get_visible():\n        return []\n",
                "",
                chart_text + "test_hidden_ancestors_do_not_contribute_text[axes]",
            ),
            Mutation(
                "chart-hidden-axis-text-inspected",
                chart_checks,
                "if (axis3d_on if axis3d_on is not None else ax.axison and axis.get_visible())",
                "if True",
                chart_text + "test_hidden_ancestors_do_not_contribute_text",
            ),
            Mutation(
                "chart-hidden-tick-text-inspected",
                chart_checks,
                "if tick.get_visible():",
                "if True:",
                chart_text + "test_hidden_ancestors_do_not_contribute_text[tick]",
            ),
            Mutation(
                "chart-3d-axis-labels-dropped",
                chart_checks,
                'axis3d_on = getattr(ax, "_axis3don", None)',
                "axis3d_on = None",
                chart_text + "test_3d_axis_labels_follow_the_projection_visibility",
            ),
            Mutation(
                "chart-clipping-advice-removed",
                chart_checks,
                'if problem.code == "clipped-text":',
                "if False:",
                chart_text + "test_real_title_clipping_is_actionable_and_wrapping_repairs_it",
            ),
        ]
    )
    value_axes = "packages/chartgx/tests/test_value_axes.py::"
    cases.extend(
        [
            Mutation(
                "chart-bar-orientation-guessed-from-magnitude",
                chart_checks,
                'axis = {"vertical": "y", "horizontal": "x"}.get(container.orientation or "")',
                'axis = "y" if container.patches[0].get_height() >= container.patches[0].get_width() else "x"',
                value_axes + "test_bar_value_axis_is_independent_of_magnitude_and_direction",
            ),
            Mutation(
                "chart-bar-unit-axis-duplicated",
                chart_checks,
                'for axis in _bar_value_axes(ax) if kind == "bar" else ["y"]:',
                'for axis in ["y"]:',
                value_axes + "test_units_note_uses_the_same_native_bar_value_axis",
            ),
            Mutation(
                "chart-inverted-bar-baseline-compared-in-view-order",
                chart_checks,
                'lo, hi = sorted(ax.get_ylim() if axis == "y" else ax.get_xlim())',
                'lo, hi = ax.get_ylim() if axis == "y" else ax.get_xlim()',
                value_axes + "test_bar_value_axis_is_independent_of_magnitude_and_direction",
            ),
            Mutation(
                "chart-only-first-bar-value-axis",
                chart_checks,
                "    return axes\n",
                "    return axes[:1]\n",
                value_axes + "test_mixed_bar_value_axes_are_checked_and_identified_separately",
            ),
            Mutation(
                "chart-bar-value-axis-unidentified",
                chart_checks,
                "                    identity=(axis,),\n",
                "",
                value_axes + "test_mixed_bar_value_axes_are_checked_and_identified_separately",
            ),
            Mutation(
                "chart-scatter-clipping-ignored",
                chart_checks,
                '("scatter", getattr(ax, "collections", ()))',
                '("scatter", ())',
                value_axes + "test_data_clipping_uses_both_axes_and_order_independent_limits",
            ),
            Mutation(
                "chart-undrawn-points-retained",
                chart_checks,
                "points = points[np.isfinite(points).all(axis=1)]",
                "points = np.asarray(points)",
                value_axes + "test_undrawn_masked_or_nonfinite_points_do_not_create_clipping",
            ),
            Mutation(
                "chart-nondata-dimension-compared",
                chart_checks,
                "                    data_axes[column]\n                    and values.size\n",
                "                    values.size\n",
                value_axes + "test_axes_relative_artists_are_not_compared_with_data_limits",
            ),
            Mutation(
                "chart-unclipped-artists-flagged-as-clipped",
                chart_checks,
                "                if not artist.get_clip_on():\n                    continue\n",
                "",
                value_axes + "test_unclipped_artists_do_not_claim_data_is_cut_off",
            ),
            Mutation(
                "chart-artist-to-data-transform-ignored",
                chart_checks,
                "points = (transform - ax.transData).transform(points)",
                "points = points.copy()",
                value_axes + "test_artist_coordinates_are_mapped_to_data_before_comparison",
            ),
        ]
    )
    return cases


def _pytest(root: Path, env: dict[str, str], tests: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a selector, tolerating a mutation whose defect *is* that it never returns.

    A restored fault can hang (measured: a loader that reads a FIFO blocks forever).
    That is the mutation being caught — the test that guards the rule can no longer
    finish — so it is reported with its own marker rather than aborting the
    catalogue.
    """
    try:
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-o", "addopts=", "-q", *tests],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        return subprocess.CompletedProcess(
            args=expired.cmd,
            returncode=-1,
            stdout=(expired.stdout or b"").decode("utf-8", "replace")
            if isinstance(expired.stdout, bytes)
            else (expired.stdout or ""),
            stderr="hung: the mutation never returned, which is the fault it restores",
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
            "GXKIT_REQUIRE_ALL_CAPABILITIES": "1",
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
                # A test can fail in several ways and they all count: an
                # assertion, a `pytest.raises` that stopped raising ("DID NOT
                # RAISE"), a `pytest.fail` with a message ("Failed: ..."), or an
                # exception the guard itself raises (a duplicate YAML key). What
                # must not count is a failure to *collect* the test — handled below.
                asserted = any(
                    marker in output
                    for marker in (
                        "AssertionError",
                        "DID NOT RAISE",
                        "Failed:",
                        f"FAILED {case.test}",
                    )
                )
                # The named test must be the one that failed. Usually pytest says
                # `FAILED <nodeid>`; a session-level guard (a test that skipped on a
                # machine with every capability) names it in its own failure text
                # instead, so the test's own name plus a failure marker also counts.
                named = f"FAILED {case.test}" in output or case.test.split("::")[-1] in output
                # A mutation whose fault is non-termination is caught by the guard
                # test never finishing, so the marker `_pytest` writes is a kill on
                # its own. The controls ran first on the unmutated copy, so this
                # cannot be a slow tree.
                if "the mutation never returned" in output:
                    print(f"killed (hung): {case.name}", flush=True)
                    continue
                killed = (
                    result.returncode == 1
                    and asserted
                    and named
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
