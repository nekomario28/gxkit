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
    # A report must survive a console that cannot encode every character it
    # names; losing it to an encoding error would turn a verdict into exit 2.
    cases.append(
        Mutation(
            "report-output-not-tolerated",
            "packages/gxcore/src/gxcore/cli.py",
            "def run(tool: Tool, argv: list[str] | None = None) -> int:\n    printable_output()\n",
            "def run(tool: Tool, argv: list[str] | None = None) -> int:\n",
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
                "apply_config(report, load_config(path.parent), tool.name)",
                "apply_config(report, load_config(Path(args.file).resolve().parent), tool.name)",
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
                "    return all(isinstance(requirement, dict) and requirement for requirement in requirements)",
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
                '        if "$ref" in operations:',
                "        if False:",
                "packages/apigx/tests/test_openapi.py::test_a_reference_is_refused_rather_than_dropped",
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
                "        if readers:",
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
        ("depsgx", "packages/depsgx/src/depsgx/checks.py", "cycle_witnesses(acyclic)"),
        (
            "authzgx",
            "packages/authzgx/src/authzgx/checks.py",
            "cycle_witnesses(model.role_edges())",
        ),
        ("pipegx", "packages/pipegx/src/pipegx/checks.py", "cycle_witnesses(edges)"),
        ("flowgx", "packages/flowgx/src/flowgx/checks.py", "cycle_witnesses(edges)"),
        ("protogx", "packages/protogx/src/protogx/checks.py", "cycle_witnesses(edges)"),
        (
            "schemagx",
            "packages/schemagx/src/schemagx/checks.py",
            "cycle_witnesses(schema.edges())",
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
                # `pytest.raises` reports an intended rejection that stopped
                # happening as "DID NOT RAISE", not as an AssertionError.
                asserted = "AssertionError" in output or "DID NOT RAISE" in output
                killed = (
                    result.returncode == 1
                    and asserted
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
