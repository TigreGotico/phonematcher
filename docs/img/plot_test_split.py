"""Draw docs/img/test-split.svg: each system's test-split estimate and 95% interval, by task.

Run from the repo root: python docs/img/plot_test_split.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "benchmarks"), str(ROOT / "docs" / "img")]
from plot_style import save  # noqa: E402
from render import README_COLUMNS, README_SYSTEMS, RESULTS  # noqa: E402

SHIPPED = "pm-P5"
intervals = {task: json.loads((RESULTS / f"{task}-test.json").read_text(encoding="utf8"))["intervals"]
             for task, _ in README_COLUMNS}


def draw(fig, theme):
    axes = fig.subplots(1, len(README_COLUMNS), sharey=True)
    labels = [label for _, label in README_SYSTEMS]
    y = range(len(README_SYSTEMS))
    for ax, (task, title) in zip(axes, README_COLUMNS):
        for i, (system, _) in enumerate(README_SYSTEMS):
            cell = intervals[task].get(system)
            if cell is None:
                ax.text(0.02, i, "does not run", va="center", fontsize=8, color=theme["muted"])
                continue
            ax.barh(i, cell["estimate"], height=0.6,
                    color=theme["series"][0] if system == SHIPPED else theme["grid"])
            ax.errorbar(cell["estimate"], i, xerr=[[cell["estimate"] - cell["low"]], [cell["high"] - cell["estimate"]]],
                        fmt="none", ecolor=theme["text"], elinewidth=1, capsize=2)
            ax.text(cell["high"] + 0.02, i, f"{cell['estimate']:.2f}", va="center", fontsize=8, color=theme["text"])
        ax.set_xlim(0, 1.12)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
        ax.set_title(title.replace(", ", "\n"), fontsize=9)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(list(y), labels, fontsize=8)
    axes[0].invert_yaxis()
    fig.suptitle("Test split: estimate and 95% interval, shipped library in colour",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")


save(str(ROOT / "docs" / "img" / "test-split"), draw, width=10, height=3.6)
