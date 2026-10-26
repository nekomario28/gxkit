"""Every finding is a shape I met while measuring: a check that reads as coverage and cannot fail."""

import pytest

import checkgx as c
from checkgx.checks import inspect_registry


def codes(registry):
    return [problem.code for problem in inspect_registry(registry).problems]


def test_a_clean_registry_has_only_the_standing_warning():
    registry = c.Registry(checks=["a", "b"], evaluated=["a", "b"], metadata=["status"])
    assert codes(registry) == ["not-a-proof-of-failure"]


def test_a_name_written_twice_is_reported():
    # Three pull requests appended the same check while merging; a dict keeps one of them.
    registry = c.Registry(checks=["a", "a", "a"], evaluated=["a"], metadata=[])
    assert "duplicate-check" in codes(registry)


def test_a_check_in_the_metadata_dict_is_reported():
    # The check was written into the report's metadata, so it compiled, printed PASS and never ran.
    registry = c.Registry(checks=["a", "late"], evaluated=["a"], metadata=["late", "status"])
    assert "check-in-metadata" in codes(registry)


def test_a_declared_check_nobody_reads_is_reported():
    registry = c.Registry(checks=["a", "forgotten"], evaluated=["a"], metadata=[])
    assert "check-never-evaluated" in codes(registry)


def test_an_evaluated_name_nobody_declared_is_reported():
    registry = c.Registry(checks=["a"], evaluated=["a", "typoo"], metadata=[])
    assert "evaluated-but-undeclared" in codes(registry)


def test_an_empty_registry_is_an_error_not_a_pass():
    assert "no-checks" in codes(c.Registry())


def test_the_report_counts_errors_so_the_exit_code_can_be_a_gate():
    report = inspect_registry(c.Registry(checks=["a", "a"], evaluated=["a"]))
    assert report.errors >= 1
    assert report.as_dict()["errors"] >= 1


def test_the_storyboard_can_be_drawn():
    from checkgx.render import render_image

    image = render_image(c.Registry(checks=["a", "b"], evaluated=["a"], metadata=["status"]))
    assert image.size[0] > 0 and image.size[1] > 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
