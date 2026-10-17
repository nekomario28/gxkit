"""A skipped test is not a passing test.

The family deliberately skips where a capability is absent: `framegx` needs
ffmpeg, `shadergx` needs a GL context, `chartgx` needs matplotlib. That is
documented behaviour, and on Windows CI 98 tests skip for it.

What must not happen is a skip on a machine that *has* the capability: that is how
a check gets disabled without anyone deciding to, and every runner would stay
green. `GXKIT_REQUIRE_ALL_CAPABILITIES=1` turns it into a failure, and the local
gate (`scripts/check.sh`) and the Linux CI job set it. Where a capability is
genuinely missing the variable stays unset and the documented behaviour holds.
"""

from __future__ import annotations

import os

_SKIPPED: list[str] = []


def pytest_runtest_logreport(report) -> None:  # noqa: ANN001 - pytest's type
    if not report.skipped:
        return
    reason = report.longrepr
    if isinstance(reason, tuple) and len(reason) == 3:
        reason = reason[2]
    _SKIPPED.append(f"{report.nodeid}: {reason}")


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ANN001 - pytest's type
    if not os.environ.get("GXKIT_REQUIRE_ALL_CAPABILITIES") or not _SKIPPED:
        return
    print(
        f"\nFailed: {len(_SKIPPED)} test(s) skipped although every capability is "
        "present — a check must not be disabled by skipping it:"
    )
    for entry in _SKIPPED:
        print(f"  {entry}")
    session.exitstatus = 1
