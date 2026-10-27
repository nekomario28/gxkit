"""A request/reply RPC surface that should pass.

Not every protocol is a handshake. A daemon that answers commands over a
socket is better drawn as "one pending slot": each request moves Idle ->
Pending, its reply moves Pending -> Idle, and fire-and-forget commands are
self-loops. `requests`/`responses` then do the real work: a declared request
whose reply is never handled is `missing-response`, and a message nothing
carries is `unhandled-message` — the two faults a plain state check cannot
see. Keep the variant names as quoted literals so a CI grep can prove the
model still mirrors the enum it was written from.
"""

import protogx as p

NAME = "RPC surface"

ANSWERED = {
    "GetQueue": "Queue",
    "GetTrack": "Track",
    "AddToQueue": "Added",
    "Search": "Results",
}

# Commands the app sends but the daemon deliberately never answers —
# optimistic playback control where the client already knows the effect.
UNANSWERED = ["Seek", "SetVolume"]

requests = sorted(ANSWERED)
replies = sorted(set(ANSWERED.values()))

protocol = p.Protocol(
    states=["Idle", "Pending", "Shutdown"],
    start="Idle",
    terminal=["Shutdown"],
    messages=([f"q.{q}" for q in requests + UNANSWERED] + [f"a.{a}" for a in replies] + ["Quit"]),
    transitions=(
        [("Idle", "Pending", f"q.{q}") for q in requests]
        + [("Idle", "Idle", f"q.{q}") for q in UNANSWERED]
        + [("Pending", "Idle", f"a.{a}") for a in replies]
        + [("Idle", "Shutdown", "Quit")]
    ),
    requests=[f"q.{q}" for q in requests],
    responses={f"q.{q}": f"a.{a}" for q, a in ANSWERED.items()},
)
