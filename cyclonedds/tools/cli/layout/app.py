import asyncio
import re
import asyncio.subprocess as asp
from typing import Optional

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

from .barchart import RichChart


class Header:
    """Display header with clock."""

    def __init__(self, title) -> None:
        self.title = title

    def __rich__(self) -> Panel:
        return Panel(self.title, style="bold bright_blue")


class CPUGraph:
    _colors = ["green", "blue", "magenta", "cyan", "white", "red"]

    def __init__(self, history_size, **kwargs) -> None:
        self.vcsw = 0
        self.ivcsw = 0
        self._thread_stats = {}
        self._color_index = 0
        self._history_size = history_size
        self._chart_kwargs = kwargs

    def update_chart_vars(self, **kwargs):
        self._chart_kwargs.update(kwargs)

    def report_stats(self, name, user_value, system_value):
        if name not in self._thread_stats:
            self._init_thread(name)
        self._thread_stats[name][1][self._history_size - 1] = user_value
        self._thread_stats[name][2][self._history_size - 1] = system_value

    def next_data(self, vcsw, ivcsw):
        self.vcsw = vcsw
        self.ivcsw = ivcsw
        for name in self._thread_stats.keys():
            for i in range(self._history_size - 1):
                self._thread_stats[name][1][i] = self._thread_stats[name][1][i + 1]
                self._thread_stats[name][2][i] = self._thread_stats[name][2][i + 1]
            self._thread_stats[name][1][self._history_size - 1] = 0.0
            self._thread_stats[name][2][self._history_size - 1] = 0.0

    def _init_thread(self, name):
        self._thread_stats[name] = [
            [],
            [0.0] * self._history_size,
            [0.0] * self._history_size,
            self._colors[self._color_index]
            if self._color_index < len(self._colors)
            else "blue",
        ]
        self._color_index += 1
        for i, value in enumerate(self._thread_stats.values()):
            value[0] = [
                j + i / 2 / float(self._color_index) for j in range(self._history_size)
            ]

    def draw(self):
        chart = RichChart(title="[bold]CPU(%thread)[/]", **self._chart_kwargs)
        for values in self._thread_stats.values():
            chart.plot(values[0], values[1], "bright_" + values[3])
            chart.plot(values[0], values[2], "dark_" + values[3])
        chart.ylim((0, 100))
        return chart

    def legend(self):
        return Text.from_markup(
            "\n"
            + "\n".join(
                f"[bold][bright_{v[3]}]{k} user[/]/[dark_{v[3]}]{k} system[/][/]"
                for k, v in self._thread_stats.items()
            )
            + f"\n\n[bold cornflower_blue]Context switches[/]\n[bold]Voluntary: {self.vcsw}\nInvoluntary: {self.ivcsw}"
        )


class ScrollGraph:
    def __init__(
        self, title, history_size, color, delta: bool = False, **kwargs
    ) -> None:
        self._title = title
        self._history_size = history_size
        self._color = color
        self._data = [0.0] * history_size
        self._limits = None
        self._chart_kwargs = kwargs
        self._delta = delta
        self._time = [i for i in range(history_size)]

    def add_point(self, value):
        if self._delta:
            value = value - self._data[self._history_size - 2]

        if not self._limits:
            self._limits = [value, value]
        else:
            self._limits[0] = min(self._limits[0], value)
            self._limits[1] = max(self._limits[1], value)

        for i in range(self._history_size - 1):
            self._data[i] = self._data[i + 1]
        self._data[self._history_size - 1] = value

    def draw(self):
        chart = RichChart(
            title=f"[bold {self._color}]{self._title}[/]", **self._chart_kwargs
        )
        chart.plot(self._time, self._data, self._color)
        if self._limits:
            chart.ylim(self._limits)
        return chart

    def update_chart_vars(self, **kwargs):
        self._chart_kwargs.update(kwargs)


class MultiScrollGraph:
    _default_colors = [
        "bright_green",
        "bright_blue",
        "bright_magenta",
        "bright_cyan",
        "bright_white",
        "bright_red",
    ]

    def __init__(self, title, history_size, delta: bool = False, **kwargs) -> None:
        self._title = title
        self._history_size = history_size
        self._colors = []
        self._data = []
        self._limits = None
        self._chart_kwargs = kwargs
        self._delta = delta
        self._time = [i for i in range(history_size)]

    def add_new_line(self, color: Optional[str] = None):
        color = color or self._default_colors[len(self._data)]
        self._data.append([0.0] * self._history_size)
        self._colors.append(color)
        return len(self._colors) - 1

    def add_point(self, index, value):
        if self._delta:
            value = value - self._data[index][self._history_size - 2]

        if not self._limits:
            self._limits = [value, value]
        else:
            self._limits[0] = min(self._limits[0], value)
            self._limits[1] = max(self._limits[1], value)

        for i in range(self._history_size - 1):
            self._data[index][i] = self._data[index][i + 1]
        self._data[index][self._history_size - 1] = value

    def draw(self):
        chart = RichChart(title=self._title, **self._chart_kwargs)
        for i in range(len(self._data)):
            chart.plot(self._time, self._data[i], self._colors[i])
        if self._limits:
            chart.ylim(self._limits)
        return chart

    def update_chart_vars(self, **kwargs):
        self._chart_kwargs.update(kwargs)


class PeerPanel:
    _colors = [
        "bright_green",
        "bright_blue",
        "bright_magenta",
        "bright_cyan",
        "bright_white",
        "bright_red",
    ]

    def __init__(self, coloured: bool = False):
        self.my_peer = None
        self.peers = []
        self.historic_peers = []
        self.colored = coloured
        self.colors = {}

    def add_peer(self, host, pid):
        if (host, pid) in self.historic_peers:
            self.historic_peers.remove((host, pid))
        self.peers.append((host, pid))

    def remove_peer(self, host, pid):
        peer = (host, pid)
        self.peers.remove(peer)
        if self.colored and peer in self.colors:
            del self.colors[peer]
        self.historic_peers.append(peer)

    def set_own(self, host, pid):
        self.my_peer = (host, pid)

    def get_peer_color(self, host, pid):
        peer = (host, pid)
        if not self.colored:
            return "bright_cyan"

        if peer in self.colors:
            return self.colors[peer]

        used = set(self.colors.values())
        for c in self._colors:
            if c not in used:
                self.colors[peer] = c
                return c

        self.colors[peer] = "bright_yellow"
        return "bright_yellow"

    def draw(self):
        if not self.my_peer:
            return Panel("waiting for data")

        txt = f"[bold]╶── Self ──╴\n[{self.get_peer_color(*self.my_peer)}]{self.my_peer[0]}[/]:{self.my_peer[1]}[/]\n\n[bold]╶── Others ──╴[/]\n"

        txt += "\n".join(
            f"[{self.get_peer_color(*e)}]{e[0]}[/]:{e[1]}" for e in self.peers
        )

        if self.historic_peers:
            txt += "\n\n[bold]╶── Gone ──╴[/]\n"
            txt += "\n".join(f"[magenta]{e[0]}[/]:{e[1]}" for e in self.historic_peers)

        return Panel(txt, title="Peers")

    def update_chart_vars(self, **kwargs):
        pass


class DDSPerfApp:
    def __init__(self, console, cmd, layout_maker, update_maker) -> None:
        self.updater, self.graphs = update_maker()
        self.layout = layout_maker(cmd)
        self.cmd = cmd
        self.ph = 0
        self.console = console
        self.to_update = set()
        self.proc = None

    def add(self, a_set):
        self.to_update.update(a_set)

    def height_adjust(self):
        if self.ph == self.console.height:
            return

        self.ph = self.console.height
        render = self.layout.render(self.console, self.console.options)
        for graph in self.graphs.keys():
            if hasattr(self.graphs[graph], "update_chart_vars"):
                self.graphs[graph].update_chart_vars(
                    height=render[self.layout.get(graph)].region.height
                )
            self.add({graph})

    def refresh(self):
        for graph in self.to_update:
            if graph == "cpu":
                self.layout["cpu_legend"].update(self.graphs["cpu"].legend())
            self.layout[graph].update(
                self.graphs[graph].draw()
                if hasattr(self.graphs[graph], "draw")
                else self.graphs[graph]
            )
        self.to_update = set()
        self.height_adjust()

    async def _iter_output(self):
        while True:
            line = (await self.proc.stdout.readline()).decode().strip()
            self.add(self.updater(line))

    async def _cancel_on_quit(self, task):
        await self.proc.wait()
        task.cancel()

    async def process_ddsperf(self):
        self.proc = await asp.create_subprocess_shell(
            cmd=" ".join(self.cmd), stdout=asp.PIPE
        )
        t1 = asyncio.create_task(self._iter_output())
        t2 = asyncio.create_task(self._cancel_on_quit(t1))
        await asyncio.wait((t1, t2), return_when=asyncio.FIRST_COMPLETED)

    async def screen_refresh(self, live):
        while True:
            await asyncio.sleep(0.5)
            self.refresh()
            live.refresh()

    def run(self, render_once_on_exit):
        try:
            asyncio.run(self.run_inner(render_once_on_exit))
        except KeyboardInterrupt:
            pass

    async def run_inner(self, render_once_on_exit):
        if render_once_on_exit:
            await self.process_ddsperf()
            self.height_adjust()
            self.refresh()
            self.console.print(self.layout)
            return

        self.height_adjust()
        with Live(
            self.layout, console=self.console, auto_refresh=False, screen=True
        ) as live:
            try:
                done, pending = await asyncio.wait(
                    (
                        self.screen_refresh(live),
                        self.process_ddsperf(),
                    ),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for p in pending:
                    p.cancel()
            except KeyboardInterrupt:
                self.proc.terminate()
                await self.proc.wait()
