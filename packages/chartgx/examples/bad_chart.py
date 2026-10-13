"""A chart with problems injected on purpose — the inspector must catch them.

  * bar baseline truncated at y=40  -> truncated-baseline (error)
  * the title is far too long and runs off both edges -> clipped-text (error)
  * the y-axis label is missing    -> no-ylabel (warn)
  * the x tick labels are tiny     -> small-text (info)
  * a second y-axis shares the plot-> dual-axis (warn)
"""

import matplotlib.pyplot as plt

quarters = ["Q1", "Q2", "Q3", "Q4"]
revenue = [42, 51, 47, 63]
growth = [3.1, 21.4, -7.8, 34.0]

fig, ax = plt.subplots(figsize=(6.4, 4.0))
ax.bar(quarters, revenue, color="#4C72B0")

# Truncated baseline: bars no longer show amounts.
ax.set_ylim(40, 65)

ax.set_title(
    "Quarterly revenue and year-on-year growth rate, internal review draft, "
    "confidential — do not distribute before the board meeting on the 14th",
    fontsize=9,
)
ax.set_xlabel("Quarter")
for lbl in ax.get_xticklabels():
    lbl.set_fontsize(6)

ax2 = ax.twinx()
ax2.plot(quarters, growth, color="#C44E52", marker="o")
ax2.set_ylabel("Growth (%)")

fig.tight_layout()
