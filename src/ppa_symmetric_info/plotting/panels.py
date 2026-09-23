"""Reusable panel primitives.

Figures are composed from these rather than each script hand-rolling its own
heatmap or slice plot, so that every panel in the paper shares tick conventions,
colour maps and annotation style.
"""

from __future__ import annotations

import numpy as np

from .soft_style import (
    CMAP_DIVERGING,
    CMAP_SEQUENTIAL,
    LINE_PALETTE,
    MULTILINE_PALETTE,
)

SLICE_COLOURS = [MULTILINE_PALETTE["teal"], LINE_PALETTE["blue"], "#1A5B81"]


def heatmap(
    ax,
    df,
    *,
    label,
    title=None,
    cmap=CMAP_SEQUENTIAL,
    center=None,
    fmt="{:.2f}",
    annotate=False,
    xlabel=None,
    ylabel=None,
):
    """Heatmap of a pivoted sweep grid. Rows are the y axis, columns the x axis."""
    data = df.to_numpy(dtype=float)
    kw = {}
    if center is not None:
        span = np.nanmax(np.abs(data - center))
        kw = dict(vmin=center - span, vmax=center + span, cmap=CMAP_DIVERGING)
    else:
        kw = dict(cmap=cmap)

    im = ax.imshow(data, origin="lower", aspect="auto", **kw)
    ax.set_xticks(range(len(df.columns)))
    ax.set_yticks(range(len(df.index)))
    ax.set_xticklabels([f"{float(c):.2g}" for c in df.columns], rotation=0)
    ax.set_yticklabels([f"{float(i):.2g}" for i in df.index])
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)

    if annotate:
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                if np.isfinite(data[i, j]):
                    ax.text(
                        j,
                        i,
                        fmt.format(data[i, j]),
                        ha="center",
                        va="center",
                        fontsize=6,
                    )

    cb = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label(label)
    return im


def slices(
    ax,
    df,
    *,
    at_columns,
    label_fmt,
    xlabel,
    ylabel,
    title=None,
    colours=None,
    xticks=None,
):
    """Line slices through a grid, one line per selected column value."""
    colours = colours or SLICE_COLOURS
    cols = np.array([float(c) for c in df.columns])
    x = np.array([float(i) for i in df.index])
    for k, target in enumerate(at_columns):
        j = int(np.argmin(np.abs(cols - target)))
        ax.plot(
            x,
            df.iloc[:, j].to_numpy(dtype=float),
            color=colours[k % len(colours)],
            marker="o",
            markersize=3,
            label=label_fmt.format(cols[j]),
        )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if xticks is not None:
        ax.set_xticks(xticks)
    if title:
        ax.set_title(title)
    ax.legend(frameon=False, fontsize=8)


def mark_cap(ax, value, *, text, orientation="h"):
    """Dashed reference line, e.g. the physical cap gamma = 1."""
    fn = ax.axhline if orientation == "h" else ax.axvline
    fn(value, color="#8B1515", linestyle="--", linewidth=1, alpha=0.8)
    if orientation == "h":
        ax.annotate(
            text,
            xy=(0.99, value),
            xycoords=("axes fraction", "data"),
            ha="right",
            va="bottom",
            fontsize=7,
            color="#8B1515",
        )
    else:
        ax.annotate(
            text,
            xy=(value, 0.99),
            xycoords=("data", "axes fraction"),
            ha="left",
            va="top",
            fontsize=7,
            color="#8B1515",
        )


def percentile_band(ax, x, lo, mid, hi, *, colour, label, alpha=0.22):
    """Central line with a shaded inter-percentile band."""
    ax.fill_between(x, lo, hi, color=colour, alpha=alpha, linewidth=0)
    ax.plot(x, mid, color=colour, linewidth=1.8, label=label)


def weighted_percentiles(df, probs, qs=(5, 25, 50, 75, 95)):
    """Probability-weighted percentiles per row (e.g. year) across scenario columns."""
    a = df.to_numpy(dtype=float)
    w = np.asarray(probs, dtype=float)
    w = w / w.sum()
    out = {}
    order = np.argsort(a, axis=1)
    for q in qs:
        vals = []
        for t in range(a.shape[0]):
            idx = order[t]
            cw = np.cumsum(w[idx])
            k = int(np.searchsorted(cw, q / 100.0))
            vals.append(a[t, idx[min(k, len(idx) - 1)]])
        out[q] = np.array(vals)
    return out


def spaghetti(
    ax,
    x,
    df,
    *,
    colour,
    median_colour,
    probs=None,
    alpha=0.05,
    linewidth=0.4,
    median_label="Median",
):
    """Every scenario trajectory in a translucent colour, with a median line
    (probability-weighted if `probs` is given) drawn on top."""
    data = df.to_numpy(dtype=float)
    ax.plot(x, data, color=colour, alpha=alpha, linewidth=linewidth)
    ax.plot(
        [],
        [],
        color=colour,
        alpha=0.6,
        linewidth=1.2,
        label=f"Scenarios (n={data.shape[1]})",
    )
    median = (
        weighted_percentiles(df, probs, qs=(50,))[50]
        if probs is not None
        else np.median(data, axis=1)
    )
    ax.plot(x, median, color=median_colour, linewidth=1.8, label=median_label)
