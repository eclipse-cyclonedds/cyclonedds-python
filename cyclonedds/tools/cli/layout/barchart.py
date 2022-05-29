import math
from typing import List, Optional

from rich.text import Text
from rich.panel import Panel
from rich.measure import Measurement
from rich.console import Console, ConsoleOptions, RenderResult


def nice_axis_range(minv, maxv):
    if maxv - minv <= 0:
        if maxv == minv:
            maxv += 1
        else:
            maxv, minv = minv, maxv
    exponent = int(round(math.log10(maxv - minv))) + 1

    if exponent <= 3:
        max_exponent = int(round(math.log10(math.fabs(maxv))))
        if max_exponent <= 2:
            return (minv, maxv, 0, 3 - exponent)

    shifted_maxv = math.ceil(maxv * 10 ** (exponent + 1))
    shifted_minv = math.floor(minv * 10 ** (exponent + 1))

    # make sure datarange is even
    r = shifted_maxv - shifted_minv
    shifted_maxv += r % 2

    unshifted_minv = shifted_minv * 10 ** -(exponent + 1)
    unshifted_maxv = shifted_maxv * 10 ** -(exponent + 1)
    reshifted_minv = unshifted_minv * 10**-exponent
    reshifted_maxv = unshifted_maxv * 10**-exponent

    if reshifted_maxv - reshifted_minv > 6:
        decimals = 0
    elif shifted_maxv - shifted_minv > 1:
        decimals = 1
    else:
        decimals = 2

    return (unshifted_minv, unshifted_maxv, exponent - 1, decimals)


def fit_x_labels(width, minv, maxv, exponent):
    minv = minv * 10**-exponent
    maxv = maxv * 10**-exponent
    rng = maxv - minv

    labels = [f"{minv:.1f}", f"{maxv:.1f}"]
    values = [minv, maxv]

    for i in range(4):
        nlabels = labels.copy()
        nvalues = values.copy()
        for j in range(2**i):
            v = minv + rng * (1 + 2 * j) / (2 ** (i + 1))
            nvalues.insert(1 + 2 * j, v)
            nlabels.insert(1 + 2 * j, f"{v:.1f}")

        if sum(len(k) + 2 for k in nlabels) >= width:
            break

        labels = nlabels
        values = nvalues

    line = ["─" for _ in range(width)]
    ticks = [" " for _ in range(width + len(labels[-1]))]
    for v, l in zip(values, labels):
        index = int(round((v - minv) / rng * (width - 1)))
        line[index] = "┬"
        for i, c in enumerate(l):
            ticks[index + i] = c

    return "".join(line), "".join(ticks).strip(), (len(ticks) - len(line)) // 2


def format_exponent(num):
    if num == 0:
        return "⁰"
    pre = ""
    if num < 0:
        pre = "⁻"
        num *= -1
    out = ""
    while num:
        c = num % 10
        num //= 10
        out += "⁰¹²³⁴⁵⁶⁷⁸⁹"[c]
    return pre + out[::-1]


class RichChart:
    def __init__(
        self,
        height_scale: float = 0.5,
        height: Optional[int] = None,
        width: Optional[int] = None,
        title: Optional[str] = None,
    ):
        self.plotlines = []
        self.plots = []
        self.subplots = []
        self.width = width
        self.height = height
        self.title = title
        self.plot_width = None
        self.plot_height = None
        self.draw_width = None
        self.draw_height = None
        self.height_scale = height_scale

        self.xrange = None
        self.yrange = None

    def plot(self, x: List[float], y: List[float], c: str, index: Optional[int] = None):
        if index is not None and index < len(self.plots):
            self.plots[index] = ("plot", c, x, y)
        else:
            self.plots.append(("plot", c, x, y))

        if len(x) >= 2:
            if self.xrange:
                self.xrange = (min(self.xrange[0], min(x)), max(self.xrange[1], max(x)))
                self.yrange = (min(self.yrange[0], min(y)), max(self.yrange[1], max(y)))
            else:
                self.xrange = (min(x), max(x))
                self.yrange = (min(y), max(y))

            if self.xrange[0] == self.xrange[1]:
                self.xrange = (self.xrange[0], self.xrange[0] + 1)

            if self.yrange[0] == self.yrange[1]:
                self.yrange = (self.yrange[0], self.yrange[0] + 1)

    def hist(self, x: List[float], c: str, index: Optional[int] = None):
        if index is not None and index < len(self.plots):
            self.plots[index] = ("hist", c, x)
        else:
            self.plots.append(("hist", c, x))

        if len(x) >= 2:
            if self.xrange:
                self.xrange = (min(self.xrange[0], min(x)), max(self.xrange[1], max(x)))
                self.yrange = (min(self.yrange[0], 0), max(self.yrange[1], 1))
            else:
                self.xrange = (min(x), max(x))
                self.yrange = (0, 1)

            if self.xrange[0] == self.xrange[1]:
                self.xrange = (self.xrange[0], self.xrange[0] + 1)

    def xlim(self, xlim):
        self.xrange = xlim

        if self.xrange[0] == self.xrange[1]:
            self.xrange = (self.xrange[0], self.xrange[0] + 1)

    def ylim(self, ylim):
        self.yrange = ylim

        if self.yrange[0] == self.yrange[1]:
            self.yrange = (self.yrange[0], self.yrange[0] + 1)

    def _do_binning(self):
        self.subplots = []
        clamp = lambda x, l, u: l if x < l else u if x > u else x
        bin_width = self.plot_width + 1

        for plot in self.plots:
            if plot[0] == "plot":
                bins = [0] * bin_width
                binn = [0] * bin_width

                # binning
                for xp, yp in zip(plot[2], plot[3]):
                    qx = int(
                        (xp - self.xrange[0])
                        / float(self.xrange[1] - self.xrange[0])
                        * bin_width
                    )
                    qx = clamp(qx, 0, bin_width - 1)
                    bins[qx] += (
                        (yp - self.yrange[0])
                        / float(self.yrange[1] - self.yrange[0])
                        * (self.plot_height - 1)
                    )
                    binn[qx] += 1

                # smear bins with no data
                for i in range(0, len(binn)):
                    if binn[i] == 0:
                        if i == 0:
                            bins[i] = bins[i + 1]
                            binn[i] = binn[i + 1]
                        elif i == len(binn) - 1:
                            bins[i] = bins[i - 1]
                            binn[i] = binn[i - 1]
                        else:
                            bins[i] = bins[i - 1] + bins[i + 1]
                            binn[i] = binn[i - 1] + binn[i + 1]

                bin = [
                    clamp(int(round(s / float(n))), 0, self.plot_height - 1)
                    if n > 0
                    else 0
                    for s, n in zip(bins, binn)
                ]

            elif plot[0] == "hist":
                bin = [0] * bin_width
                # binning
                for xp in plot[2]:
                    qx = int(
                        (xp - self.xrange[0])
                        / float(self.xrange[1] - self.xrange[0])
                        * bin_width
                    )
                    qx = clamp(qx, 0, bin_width - 1)
                    bin[qx] += 1

                scale = max(bin)
                bin = [
                    clamp(int(b / scale * self.plot_height), 0, self.plot_height - 1)
                    for b in bin
                ]

            self.subplots.append((bin, plot[1]))

    def _add_plot(self, subplot):
        bin, color_str = subplot
        color_str = f"[{color_str}]"
        for i, (b1, b2) in enumerate(zip(bin[:-1], bin[1:])):
            if b1 == b2:
                if i == 0:
                    self.grid[b1][i] = f"{color_str}╶[/]"
                elif i == len(bin) - 2:
                    self.grid[b1][i] = f"{color_str}╴[/]"
                else:
                    self.grid[b1][i] = f"{color_str}─[/]"
            else:
                if b1 > b2:
                    # downslope
                    self.grid[b1][i] = f"{color_str}╮[/]"
                    for j in range(b1 - 1, b2, -1):
                        self.grid[j][i] = f"{color_str}│[/]"
                    self.grid[b2][i] = f"{color_str}╰[/]"
                else:
                    # upslope
                    self.grid[b1][i] = f"{color_str}╯[/]"
                    for j in range(b1 + 1, b2):
                        self.grid[j][i] = f"{color_str}│[/]"
                    self.grid[b2][i] = f"{color_str}╭[/]"

    def _draw_plots(self):
        self.grid = [
            [" " for _ in range(self.plot_width)] for __ in range(self.plot_height)
        ]

        for i, subplot in enumerate(self.subplots):
            self._add_plot(subplot)

        self.plotlines = ["".join(self.grid[i]) + "│" for i in range(self.plot_height)]
        self.plotlines.reverse()

    def _empty_plot(self):
        return Panel(
            "No data recorded...", width=self.draw_width, height=self.draw_height
        )

    def _too_small(self):
        return Panel(
            "Too small to display", width=self.draw_width, height=self.draw_height
        )

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":

        # Draw sizing
        self.draw_width = (
            options.max_width - 1
            if self.width is None
            else min(options.max_width - 1, self.width)
        )
        self.plot_width = self.draw_width - 10

        self.draw_height = (
            self.height
            if self.height is not None
            else int(self.draw_width * self.height_scale / 3)
        )  # approx terminal chars thrice as high as wide
        self.draw_height -= self.draw_height % 2
        self.plot_height = self.draw_height - 3  # top bar, axis, labels

        if self.plot_height < 3:
            yield self._too_small()
            return

        if not self.plots or not self.xrange or not self.yrange:
            yield self._empty_plot()
            return

        miny, maxy, yexponent, ydecimals = nice_axis_range(*self.yrange)
        yticks = [
            f"{miny * 10 ** -yexponent + ((maxy - miny) * 10 ** -yexponent) / (self.plot_height // 2) * i:.{ydecimals}f}"
            for i in range((self.plot_height - 1) // 2 + 1)
        ]
        yticks = [a.rjust(7)[:7] for a in yticks]

        minx, maxx, xexponent, xdecimals = nice_axis_range(*self.xrange)
        xline, xticks, xtickoffset = fit_x_labels(
            self.plot_width, minx, maxx, xexponent
        )
        topline = "─" * self.plot_width
        if self.title is not None:
            r = Text.from_markup(self.title)
            segment_len = (self.plot_width - len(r)) // 2 - 1
            segment_left = "─" * segment_len + "╴"
            segment_right = "╶" + "─" * (self.plot_width - len(r) - segment_len - 2)
            topline = f"{segment_left}{self.title}{segment_right}"

        self._do_binning()
        self._draw_plots()

        ytickexp = ""
        if yexponent != 0:
            ytickexp = f"⏨{format_exponent(yexponent)}"
        ytickexp = ytickexp.rjust(7)[:7]

        xtickexp = ""
        if xexponent != 0:
            xtickexp = f"⏨{format_exponent(xexponent)}"

        yticks = sum(([f"{ytick}┤", "       │"] for ytick in yticks), [])
        yticks.pop()
        yticks.reverse()
        assert len(yticks) == len(self.plotlines)
        lines = [f"{ytick}{line}" for ytick, line in zip(yticks, self.plotlines)]

        block = (
            f"{ytickexp}╭{topline}╮\n"
            + "\n".join(lines)
            + "\n"
            + f"╰{xline}╯\n".rjust(self.draw_width)
            + f"{xtickexp} {xticks}\n".rjust(self.draw_width)
        )

        # Build text grid
        yield Text.from_markup(block)

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        return Measurement(8, options.max_width)

    def draw(self):
        return self

    def update_chart_vars(
        self, height: Optional[int] = None, width: Optional[int] = None, **kwargs
    ):
        self.height = height or self.height
        self.width = width or self.width
