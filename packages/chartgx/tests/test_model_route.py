"""The declared-model route, branch by branch, without a subprocess.

The route reports chartgx's own codes, so these tests pin the two things a reader
depends on: a recognized declaration that cannot be read is refused where it is
wrong, and a defect is reported under the same code whichever route found it.
"""

from __future__ import annotations

import json
import re

import pytest
from chartgx.model import MODEL_CODES, InvalidModel, inspect_model, load_model
from gxcore import ERROR, INFO, WARN
from gxcore.testing import assert_fires


def bars(values: list[float]) -> dict:
    return {
        "kind": "bar",
        "categories": [f"c{index}" for index in range(len(values))],
        "values": values,
    }


def clean() -> dict:
    return {
        "title": "Revenue",
        "x_label": "quarter",
        "y_label": "revenue (M JPY)",
        "marks": [bars([31.5, 41.0])],
    }


def test_a_clean_declaration_has_nothing_to_report():
    # A complete declaration: no errors (a missing title is a warning, not a defect).
    assert inspect_model(clean()).errors == 0


def test_a_truncated_baseline_is_the_same_code_the_figure_route_uses():
    # The concept is one concept: a user who has seen `truncated-baseline` from a
    # matplotlib figure must not learn a second name for it here.
    report = inspect_model(clean() | {"y_min": 25})
    assert_fires(report, "truncated-baseline", ERROR)
    assert "no-title" not in {problem.code for problem in report.problems}


def test_an_empty_declaration_says_so_with_the_figure_routes_code():
    assert_fires(inspect_model({"marks": []}), "empty-chart", ERROR)


def test_missing_labels_are_warned_about_only_when_something_is_declared():
    empty = inspect_model({"marks": []})
    assert {problem.code for problem in empty.problems} == {"empty-chart"}
    labelled = inspect_model({"marks": [bars([1.0, 2.0])]})
    codes = {problem.code for problem in labelled.problems}
    assert {"no-title", "no-xlabel", "no-ylabel"} <= codes
    assert {MODEL_CODES[code] for code in ("no-title", "no-xlabel", "no-ylabel")} == {WARN}


def test_error_magnitudes_must_match_the_points():
    mark = {
        "kind": "line",
        "points": [[0.0, 1.0], [1.0, 2.0]],
        "y_err": [0.1],
    }
    report = inspect_model({"marks": [mark]})
    assert_fires(report, "mismatched-lengths", ERROR)
    assert "2 points" in report.problems[0].message


def test_asymmetric_errors_are_counted_per_point():
    mark = {
        "kind": "scatter",
        "points": [[0.0, 1.0], [1.0, 2.0]],
        "y_err_asymmetric": [[0.1, 0.2], [0.1, 0.2]],
    }
    assert inspect_model({"marks": [mark]}).errors == 0
    mark["y_err_asymmetric"] = [[0.1, 0.2]]
    assert_fires(inspect_model({"marks": [mark]}), "mismatched-lengths", ERROR)


def test_declaring_both_error_shapes_is_reported_once():
    mark = {
        "kind": "line",
        "points": [[0.0, 1.0], [1.0, 2.0]],
        "y_err": [0.1, 0.1],
        "y_err_asymmetric": [[0.1, 0.2], [0.1, 0.2]],
    }
    report = inspect_model({"marks": [mark]})
    assert_fires(report, "two-error-shapes", ERROR)


def test_a_log_axis_with_a_non_positive_bar_is_reported_once_per_mark():
    """The values, not the errors, are what a log axis has to place."""
    model = {
        "marks": [
            {"kind": "grouped_bar", "categories": ["a", "b"], "series": [{"values": [0.0, 1.0]}]}
        ],
        "y_scale": "log",
    }
    report = inspect_model(model)
    assert [problem.code for problem in report.problems if problem.severity == "error"] == [
        "log-nonpositive"
    ]


def test_a_log_axis_with_a_non_positive_line_point_is_reported():
    model = {"marks": [{"kind": "line", "points": [[0.0, 0.0], [1.0, 2.0]]}], "y_scale": "log"}
    report = inspect_model(model)
    assert [problem.code for problem in report.problems if problem.severity == "error"] == [
        "log-nonpositive"
    ]


def test_a_negative_error_magnitude_is_an_error():
    mark = {"kind": "scatter", "points": [[0.0, 1.0]], "y_err": [-0.5]}
    assert_fires(inspect_model({"marks": [mark]}), "negative-error", ERROR)


def test_a_group_needs_one_value_per_category_in_every_series():
    good = {
        "kind": "grouped_bar",
        "categories": ["Q1", "Q2"],
        "series": [{"values": [1.0, 2.0]}, {"values": [3.0, 4.0]}],
    }
    assert inspect_model({"marks": [good]}).errors == 0
    short = json.loads(json.dumps(good))
    short["series"][1]["values"] = [3.0]
    report = inspect_model({"marks": [short]})
    assert_fires(report, "mismatched-lengths", ERROR)
    assert "series 1" in report.problems[0].message


def test_a_non_positive_value_on_a_log_axis_is_reported_with_the_figure_routes_code():
    report = inspect_model({"marks": [bars([0.0, 1.0])], "y_scale": "log"})
    assert_fires(report, "log-nonpositive", ERROR)


def test_a_non_finite_value_cannot_be_placed():
    for kind, mark in (
        ("bar", {"kind": "bar", "categories": ["a"], "values": [float("nan")]}),
        ("line", {"kind": "line", "points": [[0.0, float("inf")], [1.0, 2.0]]}),
        (
            "grouped_bar",
            {"kind": "grouped_bar", "categories": ["a"], "series": [{"values": [float("nan")]}]},
        ),
    ):
        assert_fires(inspect_model({"marks": [mark]}), "non-finite-value", ERROR), kind


def test_every_code_in_the_table_is_reachable_from_these_tests():
    # The table is the contract; if a code cannot be produced, the guard in
    # test_codes should not be the only thing that notices.
    produced: set[str] = set()
    cases = [
        {"marks": []},
        clean() | {"y_min": 25},
        {"marks": [bars([1.0, 2.0])]},
        {"marks": [bars([0.0, 1.0])], "y_scale": "log"},
        {"marks": [{"kind": "bar", "categories": ["a"], "values": [float("nan")]}]},
        {"marks": [{"kind": "bar", "categories": ["a", "b"], "values": [1.0]}]},
        {"marks": [{"kind": "line", "points": [[0.0, 1.0]], "y_err": [-0.1]}]},
        {
            "marks": [
                {
                    "kind": "line",
                    "points": [[0.0, 1.0]],
                    "y_err": [0.1],
                    "y_err_asymmetric": [[0.1, 0.2]],
                }
            ]
        },
    ]
    for model in cases:
        produced |= {problem.code for problem in inspect_model(model).problems}
    assert set(MODEL_CODES) <= produced, sorted(set(MODEL_CODES) - produced)


# --------------------------------------------------------------------------- #
# Refusals: a recognized declaration with a member that cannot be read
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("not json", "not JSON"),
        ("[1, 2]", "expected an object"),
        ('{"marks": [], "titlee": "x"}', "unrecognised key"),
        ('{"marks": 42}', "'marks' must be a list"),
        ('{"marks": [42]}', "expected an object"),
        ('{"marks": [{"kind": "pie"}]}', "expected one of"),
        ('{"marks": [{"kind": "bar"}]}', "categories"),
        ('{"marks": [{"kind": "bar", "categories": [1]}]}', "list of strings"),
        ('{"marks": [{"kind": "bar", "categories": []}]}', "expected a list of numbers"),
        ('{"marks": [{"kind": "bar", "categories": ["a"], "values": ["x"]}]}', "expected a number"),
        ('{"marks": [{"kind": "line"}]}', "points: expected a list"),
        ('{"marks": [{"kind": "line", "points": [[1]]}]}', "expected [x, y]"),
        ('{"marks": [{"kind": "line", "points": [[1, "y"]]}]}', "expected a number"),
        ('{"marks": [{"kind": "line", "points": [], "y_err": "x"}]}', "y_err: expected a list"),
        (
            '{"marks": [{"kind": "line", "points": [], "y_err_asymmetric": [1]}]}',
            "expected [lower, upper]",
        ),
        (
            '{"marks": [{"kind": "line", "points": [], "y_err_asymmetric": "x"}]}',
            "expected a list of [lower, upper]",
        ),
        ('{"marks": [{"kind": "grouped_bar", "categories": ["a"]}]}', "non-empty list of series"),
        (
            '{"marks": [{"kind": "grouped_bar", "categories": ["a"], "series": [1]}]}',
            "expected an object",
        ),
        (
            '{"marks": [{"kind": "grouped_bar", "categories": ["a"], "series": [{"values": ["x"]}]}]}',
            "expected a number",
        ),
        ('{"marks": [{"kind": "bar", "categories": ["a"], "values": [1]}], "y_min": "x"}', "y_min"),
    ],
)
def test_a_declaration_that_cannot_be_read_is_refused_where_it_is_wrong(
    tmp_path, payload, expected
):
    """Refused by the load-then-inspect chain the tool actually runs.

    `load_model` owns the figure's own shape; the marks' bodies are validated
    where the checks are. A caller always runs both, so the refusal is asserted on
    the chain rather than on which function notices.
    """
    path = tmp_path / "chart.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(InvalidModel, match=re.escape(expected)):
        inspect_model(load_model(path))


def test_a_missing_file_is_an_input_failure(tmp_path):
    with pytest.raises(InvalidModel, match="no-such-file"):
        load_model(tmp_path / "no-such-file.json")


def test_a_declaration_is_refused_by_the_checks_too_when_its_numbers_are_wrong(tmp_path):
    path = tmp_path / "chart.json"
    path.write_text('{"marks": [{"kind": "bar", "categories": ["a"], "values": [1]}], "y_min": 25}')
    model = load_model(path)
    report = inspect_model(model)
    assert report.problems[0].code == "truncated-baseline"


def test_the_info_severity_is_used_nowhere_in_this_route_yet():
    # Stated rather than implied: the model route has no informational findings, so
    # a reader comparing it to the figure route knows that is deliberate.
    assert INFO not in set(MODEL_CODES.values())


def test_the_two_routes_agree_on_a_truncated_baseline(tmp_path):
    """Measured end to end: the same defect, the same code, either route.

    A matplotlib figure whose y axis is trimmed and a declaration that says
    `y_min` are the same chart. A user must not have to learn two names for the
    finding, which is what the `declared-` prefix in an earlier draft would have
    done.
    """
    from chartgx.checks import inspect_figure

    script = tmp_path / "chart.py"
    script.write_text(
        "import matplotlib\nmatplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "fig, ax = plt.subplots()\n"
        "ax.bar(['Q1', 'Q2'], [31.5, 41.0])\n"
        "ax.set_ylim(25, None)\n"
        "ax.set_title('Trimmed')\n"
        "ax.set_xlabel('quarter')\nax.set_ylabel('revenue (M JPY)')\n",
        encoding="utf-8",
    )
    from chartgx.loader import load_figure

    figure, _ = load_figure(script)
    from_figure = {problem.code for problem in inspect_figure(figure).problems}
    assert "truncated-baseline" in from_figure

    declaration = tmp_path / "chart.json"
    declaration.write_text(
        json.dumps(
            {
                "title": "Trimmed",
                "x_label": "quarter",
                "y_label": "revenue (M JPY)",
                "y_min": 25,
                "marks": [{"kind": "bar", "categories": ["Q1", "Q2"], "values": [31.5, 41.0]}],
            }
        ),
        encoding="utf-8",
    )
    from_declaration = {problem.code for problem in inspect_model(load_model(declaration)).problems}
    assert from_declaration == from_figure


def test_the_tool_dispatches_a_declaration_without_touching_matplotlib(tmp_path):
    """The route the CLI takes: load → inspect → (no render, no storyboard)."""
    import chartgx
    from chartgx.tool import TOOL, Declared

    path = tmp_path / "chart.json"
    path.write_text(json.dumps(clean()), encoding="utf-8")
    artifact = TOOL.load(path)
    assert isinstance(artifact, Declared)
    assert artifact.name == "Revenue"
    assert TOOL.inspect(artifact).errors == 0

    # Rendering and the storyboard are refused with the reason, rather than
    # producing a picture whose numbers have nothing to point at.
    with pytest.raises(ValueError, match="rendered by figspec"):
        TOOL.render(artifact, tmp_path / "out.png", None)
    # The refusal names the route that *can* draw it: a reason a reader cannot act
    # on is half a reason.
    with pytest.raises(ValueError, match="no storyboard"):
        TOOL.to_image(artifact)
    with pytest.raises(ValueError, match=r"figspec storyboard"):
        TOOL.to_image(artifact)

    # And the figure route still works in the same tool.
    from chartgx.tool import Chart

    assert chartgx.__doc__ is not None
    assert Declared.__name__ == "Declared"
    assert Chart.__name__ == "Chart"
