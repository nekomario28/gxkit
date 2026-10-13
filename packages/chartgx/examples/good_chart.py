"""A chart that should pass inspection.

Revenue by quarter, value axis from zero, titled, labelled with units.
"""

import matplotlib.pyplot as plt

quarters = ["Q1", "Q2", "Q3", "Q4"]
revenue = [42, 51, 47, 63]

fig, ax = plt.subplots(figsize=(6.4, 4.0))
ax.bar(quarters, revenue, color="#4C72B0")
ax.set_title("Revenue by quarter (2025)", fontsize=14)
ax.set_xlabel("Quarter")
ax.set_ylabel("Revenue (£m)")
ax.set_ylim(0, 70)
fig.tight_layout()
