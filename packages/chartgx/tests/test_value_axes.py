"""Value axes come from artists' semantics, not incomparable numeric dimensions."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pytest
from chartgx import inspect_figure
from matplotlib.transforms import Affine2D


@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
@pytest.mark.parametrize("negative", [False, True])
@pytest.mark.parametrize("truncated", [False, True])
@pytest.mark.parametrize("inverted", [False, True])
def test_bar_value_axis_is_independent_of_magnitude_and_direction(
    orientation, negative, truncated, inverted
):
    fig, ax = plt.subplots()
    try:
        values = [-0.4, -0.3] if negative else [0.3, 0.4]
        draw = ax.bar if orientation == "vertical" else ax.barh
        draw(["a", "b"], values)
        low, high = (-0.5, -0.2 if truncated else 0) if negative else (0.2 if truncated else 0, 0.5)
        limits = (high, low) if inverted else (low, high)
        setter = ax.set_ylim if orientation == "vertical" else ax.set_xlim
        setter(*limits)
        ax.set_title("Amounts")
        findings = [p for p in inspect_figure(fig).problems if p.code == "truncated-baseline"]
        assert bool(findings) is truncated
        if findings:
            axis = "y" if orientation == "vertical" else "x"
            assert f"{axis}=" in findings[0].message
    finally:
        plt.close(fig)


@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
@pytest.mark.parametrize("negative", [False, True])
def test_units_note_uses_the_same_native_bar_value_axis(orientation, negative):
    fig, ax = plt.subplots()
    try:
        values = [-0.4, -0.3] if negative else [0.3, 0.4]
        draw = ax.bar if orientation == "vertical" else ax.barh
        draw(["a", "b"], values)
        ax.set_xlabel("duration" if orientation == "horizontal" else "job")
        ax.set_ylabel("duration" if orientation == "vertical" else "job")
        findings = [p for p in inspect_figure(fig).problems if p.code == "no-units"]
        assert len(findings) == 1
        assert "'duration'" in findings[0].message
    finally:
        plt.close(fig)


def test_mixed_bar_value_axes_are_checked_and_identified_separately():
    fig, ax = plt.subplots()
    try:
        ax.bar([2], [0.3])
        ax.barh([2], [0.3])
        ax.set_xlim(0.1, 3)
        ax.set_ylim(0.1, 3)
        findings = [p for p in inspect_figure(fig).problems if p.code == "truncated-baseline"]
        assert len(findings) == 2
        assert {p.identity for p in findings} == {("x",), ("y",)}
    finally:
        plt.close(fig)


@pytest.mark.parametrize("kind", ["line", "scatter"])
@pytest.mark.parametrize("inverted", [False, True])
def test_data_clipping_uses_both_axes_and_order_independent_limits(kind, inverted):
    fig, ax = plt.subplots()
    try:
        draw = ax.plot if kind == "line" else ax.scatter
        draw([0.5, 1, 3], [0.5, 1, 3])
        limits = (2, 0) if inverted else (0, 2)
        ax.set_xlim(*limits)
        ax.set_ylim(*limits)
        findings = [p for p in inspect_figure(fig).problems if p.code == "clipped-data"]
        assert len(findings) == 2
        assert any("x-limits" in p.message for p in findings)
        assert any("y-limits" in p.message for p in findings)
        # All points fit when the view is widened, regardless of its direction.
        ax.set_xlim(*(4, 0) if inverted else (0, 4))
        ax.set_ylim(*(4, 0) if inverted else (0, 4))
        assert not any(p.code == "clipped-data" for p in inspect_figure(fig).problems)
    finally:
        plt.close(fig)


@pytest.mark.parametrize("kind", ["line", "scatter"])
def test_undrawn_masked_or_nonfinite_points_do_not_create_clipping(kind):
    fig, ax = plt.subplots()
    try:
        if kind == "scatter":
            ax.scatter([0.5, 100], np.ma.array([0.5, 100], mask=[False, True]))
            ax.scatter([], [])
        else:
            ax.plot([0.5, 100], [0.5, np.nan])
            ax.plot([], [])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        assert not any(p.code == "clipped-data" for p in inspect_figure(fig).problems)
    finally:
        plt.close(fig)


@pytest.mark.parametrize("axis", ["x", "y"])
def test_reference_line_is_checked_only_in_its_data_dimension(axis):
    fig, ax = plt.subplots()
    try:
        ax.plot([0.5, 1], [0.5, 1])
        (ax.axvline if axis == "x" else ax.axhline)(3)
        ax.set_xlim(0, 2)
        ax.set_ylim(0, 2)
        findings = [p for p in inspect_figure(fig).problems if p.code == "clipped-data"]
        assert len(findings) == 1
        assert f"{axis}-limits" in findings[0].message
    finally:
        plt.close(fig)


@pytest.mark.parametrize("kind", ["line", "scatter"])
def test_artist_coordinates_are_mapped_to_data_before_comparison(kind):
    fig, ax = plt.subplots()
    try:
        draw = ax.plot if kind == "line" else ax.scatter
        draw([0.2, 0.3], [0.2, 0.3], transform=Affine2D().translate(3, 0) + ax.transData)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        findings = [p for p in inspect_figure(fig).problems if p.code == "clipped-data"]
        assert len(findings) == 1
        assert "x-limits" in findings[0].message
    finally:
        plt.close(fig)


@pytest.mark.parametrize("kind", ["line", "scatter"])
def test_unclipped_artists_do_not_claim_data_is_cut_off(kind):
    fig, ax = plt.subplots()
    try:
        draw = ax.plot if kind == "line" else ax.scatter
        draw([0.5, 3], [0.5, 3], clip_on=False)
        ax.set_xlim(0, 2)
        ax.set_ylim(0, 2)
        assert not any(p.code == "clipped-data" for p in inspect_figure(fig).problems)
    finally:
        plt.close(fig)


def test_axes_relative_artists_are_not_compared_with_data_limits():
    fig, ax = plt.subplots()
    try:
        ax.plot([10, 15, 20], [10, 15, 20])
        ax.axhline(15)
        ax.axvline(15)
        ax.scatter([0.5, 1.2], [0.5, 1.2], transform=ax.transAxes)
        ax.set_xlim(9, 21)
        ax.set_ylim(9, 21)
        assert not any(p.code == "clipped-data" for p in inspect_figure(fig).problems)
    finally:
        plt.close(fig)
