#!/usr/bin/env python3
"""Rollback copy of the previous sparse voice-motion timelines.

Captured before converting voice_motion_demos.py to action-cluster scripts.
Latest user labeling at backup time:
- listening: 0df6af9bf4b0303177c7b607efc3e988-听.mp4
- thinking: 0b5c990939c341f348ffc253b333e121-思考.mp4
- answer: 25059b3751e232cdc7c054d3ce610046-答.mp4
"""

from __future__ import annotations


Pose = tuple[int, int, int, int]
Marker = tuple[float, Pose, str]


LISTENING_TIMELINE: tuple[Marker, ...] = (
    (0.00, (2048, 2056, 2036, 2048), "listen neutral"),
    (0.55, (2032, 2064, 2028, 2036), "tiny lean left"),
    (1.10, (2064, 2072, 2044, 2060), "tiny lean right"),
    (1.70, (2048, 2060, 2024, 2048), "soft nod down"),
    (2.35, (2048, 2076, 2068, 2048), "look up acknowledgement"),
    (3.05, (2024, 2064, 2032, 2028), "attentive left"),
    (3.75, (2072, 2068, 2040, 2068), "attentive right"),
    (4.45, (2048, 2056, 2024, 2048), "small listening dip"),
    (5.20, (2040, 2072, 2056, 2038), "curious micro tilt"),
    (6.00, (2056, 2064, 2032, 2060), "return and hold"),
    (6.80, (2048, 2056, 2048, 2048), "front calm"),
    (7.70, (2048, 2048, 2048, 2048), "neutral finish"),
)


THINKING_TIMELINE: tuple[Marker, ...] = (
    (0.00, (2048, 2072, 2036, 2048), "thinking start"),
    (0.70, (2016, 2088, 2012, 2018), "turn down left"),
    (1.55, (1988, 2100, 1992, 1996), "deeper left thought"),
    (2.45, (1988, 2092, 1984, 2004), "hold the thought"),
    (3.35, (2048, 2080, 2012, 2048), "slow return"),
    (4.15, (2096, 2096, 2000, 2092), "search right"),
    (5.05, (2112, 2104, 1988, 2108), "deeper right thought"),
    (5.95, (2072, 2084, 2020, 2076), "release"),
    (6.75, (2048, 2112, 2064, 2048), "idea lifts"),
    (7.45, (2024, 2092, 2024, 2028), "one more check"),
    (8.25, (2048, 2072, 2048, 2048), "readying answer"),
    (9.05, (2048, 2048, 2048, 2048), "neutral finish"),
)


ANSWER_TIMELINE: tuple[Marker, ...] = (
    (0.00, (2048, 2156, 2108, 2048), "pre-open lift"),
    (0.40, (2048, 2120, 2072, 2048), "en opening"),
    (0.88, (2012, 2132, 2056, 2016), "big meets little"),
    (1.35, (2084, 2148, 2096, 2080), "yang liu"),
    (1.90, (2048, 2116, 2024, 2048), "designed"),
    (2.42, (1996, 2168, 2108, 2008), "cute picture book"),
    (3.10, (2096, 2132, 2056, 2092), "warm settle"),
    (3.72, (2048, 2068, 2008, 2048), "period pause"),
    (4.20, (2048, 2128, 2076, 2048), "minimal icons"),
    (4.82, (2004, 2140, 2052, 2012), "contrast one"),
    (5.42, (2092, 2152, 2092, 2088), "adult child view"),
    (6.02, (2048, 2116, 2028, 2048), "family daily"),
    (6.62, (1992, 2148, 2088, 2012), "small nod"),
    (7.28, (2048, 2076, 2016, 2048), "pause"),
    (7.62, (2048, 2196, 2148, 2048), "warm and funny punch"),
    (8.02, (2112, 2172, 2056, 2108), "laugh sway right"),
    (8.40, (1984, 2184, 2132, 1988), "laugh sway left"),
    (8.82, (2048, 2084, 2012, 2048), "pause after punch"),
    (9.02, (2048, 2132, 2076, 2048), "video style"),
    (9.62, (2000, 2148, 2044, 2012), "clear at a glance"),
    (10.30, (2092, 2160, 2100, 2092), "knowledge video"),
    (11.08, (2048, 2132, 2032, 2048), "fits nicely"),
    (11.82, (2012, 2156, 2096, 2016), "oh ending"),
    (12.52, (2048, 2096, 2020, 2048), "audio tail"),
    (13.10, (2048, 2048, 2048, 2048), "neutral"),
)


DEMO_VIDEO_MAPPING = {
    "listening": "0df6af9bf4b0303177c7b607efc3e988-听.mp4",
    "thinking": "0b5c990939c341f348ffc253b333e121-思考.mp4",
    "answer": "25059b3751e232cdc7c054d3ce610046-答.mp4",
}
