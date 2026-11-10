"""An MPRIS player, as one real application serves it.

Adapted from Melba's own gate model (github.com/nekomario28/melba,
``ci/models/mpris.py``), where it caught a method added to a D-Bus interface
without a transition the moment it was written — before CI ran. The useful part
for this corpus is the shape: a media player is a small state machine whose
messages are bus calls, and "declared but never handled" is exactly the fault a
regression introduces.

It stays here as a realistic example rather than a fixture: four states,
eighteen requests, and the transitions that make them reachable.
"""

# org.mpris.MediaPlayer2.Player + root — message surface of `melbad serve`.
# Every declared message must have a handler transition; models player.rs.
# Signals (PropertiesChanged/Seeked) are fire-and-forget, not modeled here.
import protogx as p

protocol = p.Protocol(
    states=["Stopped", "Playing", "Paused", "Ended"],
    start="Stopped",
    terminal=["Ended"],
    messages=[
        "Play", "Pause", "PlayPause", "Stop", "Next", "Previous",
        "Seek", "SetPosition", "OpenUri", "MelbaGoTo", "MelbaEnqueue",
        "MelbaQueueReorder", "MelbaQueueClear", "MelbaQueueEmpty",
        "MelbaSetDevice",
        "MelbaAudioDevices", "MelbaSetAudioDevice",
        "Raise", "Quit", "TrackEnd",
    ],
    transitions=[
        ("Stopped", "Playing", "Play"),
        ("Stopped", "Playing", "PlayPause"),
        ("Stopped", "Playing", "OpenUri"),     # enqueue + play-now
        ("Stopped", "Playing", "MelbaGoTo"),     # queue jump wakes a stopped queue
        ("Stopped", "Stopped", "Raise"),
        # queue/device mutations are state-preserving in every state
        ("Stopped", "Stopped", "MelbaEnqueue"),
        ("Stopped", "Stopped", "MelbaQueueReorder"),
        ("Stopped", "Stopped", "MelbaQueueClear"),
        ("Stopped", "Stopped", "MelbaQueueEmpty"),
        ("Stopped", "Stopped", "MelbaSetDevice"),
        ("Stopped", "Stopped", "MelbaAudioDevices"),
        ("Stopped", "Stopped", "MelbaSetAudioDevice"),
        ("Stopped", "Ended", "Quit"),
        ("Playing", "Paused", "Pause"),
        ("Playing", "Paused", "PlayPause"),
        ("Playing", "Stopped", "Stop"),
        ("Playing", "Playing", "Next"),
        ("Playing", "Playing", "Previous"),    # pending_idx → previous track
        ("Playing", "Playing", "Seek"),
        ("Playing", "Playing", "SetPosition"),
        ("Playing", "Playing", "OpenUri"),
        ("Playing", "Playing", "MelbaGoTo"),
        ("Playing", "Playing", "MelbaEnqueue"),
        ("Playing", "Playing", "MelbaQueueReorder"),
        ("Playing", "Playing", "MelbaQueueClear"),
        ("Playing", "Stopped", "MelbaQueueEmpty"),
        ("Playing", "Playing", "MelbaSetDevice"),
        ("Playing", "Playing", "MelbaAudioDevices"),
        ("Playing", "Playing", "MelbaSetAudioDevice"),
        ("Playing", "Stopped", "TrackEnd"),
        ("Playing", "Ended", "Quit"),
        ("Paused", "Playing", "Play"),
        ("Paused", "Playing", "PlayPause"),
        ("Paused", "Playing", "Next"),
        ("Paused", "Playing", "Previous"),
        ("Paused", "Playing", "Seek"),
        ("Paused", "Playing", "SetPosition"),
        ("Paused", "Playing", "OpenUri"),
        ("Paused", "Playing", "MelbaGoTo"),
        ("Paused", "Playing", "MelbaEnqueue"),
        ("Paused", "Playing", "MelbaQueueReorder"),
        ("Paused", "Playing", "MelbaQueueClear"),
        ("Paused", "Stopped", "MelbaQueueEmpty"),
        ("Paused", "Playing", "MelbaSetDevice"),
        ("Paused", "Paused", "MelbaAudioDevices"),
        ("Paused", "Playing", "MelbaSetAudioDevice"),
        ("Paused", "Stopped", "Stop"),
        ("Paused", "Stopped", "TrackEnd"),
        ("Paused", "Ended", "Quit"),
    ],
    requests=[
        "Play", "Pause", "PlayPause", "Stop", "Next", "Previous",
        "Seek", "SetPosition", "OpenUri", "MelbaGoTo", "MelbaEnqueue",
        "MelbaQueueReorder", "MelbaQueueClear", "MelbaSetDevice",
        "MelbaQueueReorder", "MelbaQueueEmpty", "MelbaSetDevice",
        "MelbaAudioDevices", "MelbaSetAudioDevice",
        "Raise", "Quit",
    ],
    responses={},  # MPRIS methods return empty bodies; no reply discipline to model
)
