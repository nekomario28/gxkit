"""The same chart as bad_chart.py, with every error and warning fixed.

  * value axis from 0           -> no truncated-baseline
  * a short title that fits     -> no clipped-text
  * y-axis label added          -> no no-ylabel
  * readable tick font          -> no small-text
  * the twin axis is gone, and growth is a second panel instead of a second scale.
"""

import matplotlib.pyplot as plt

quarters = ["Q1", "Q2", "Q3", "Q4"]
revenue = [42, 51, 47, 63]
growth = [3.1, 21.4, -7.8, 34.0]

fig, (ax, ax2) = plt.subplots(2, 1, figsize=(6.4, 5.6), sharex=True)

ax.bar(quarters, revenue, color="#4C72B0")
ax.set_ylim(0, 70)
ax.set_title("Revenue and growth, 2025", fontsize=14)
ax.set_ylabel("Revenue (£m)")

ax2.plot(quarters, growth, color="#C44E52", marker="o")
ax2.axhline(0, color="#888888", linewidth=0.8)
ax2.set_xlabel("Quarter")
ax2.set_ylabel("Growth (%)")

fig.tight_layout()
