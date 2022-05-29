import re
from datetime import datetime, timedelta
from rich.layout import Layout
from rich.text import Text

from .app import Header, CPUGraph, ScrollGraph, MultiScrollGraph, PeerPanel
from .barchart import RichChart


def make_ping_layout(cmd) -> Layout:
    layout = Layout(name="ddsperf_app")

    layout.split(Layout(name="header", size=3), Layout(name="main", ratio=1))
    layout["main"].split_row(
        Layout(name="latencies_perhost", ratio=1), Layout(name="others", ratio=1)
    )
    layout["others"].split_column(
        Layout(name="top_others", ratio=1), Layout(name="bottom_others", ratio=1)
    )
    layout["top_others"].split_row(
        Layout(name="latencies_combined", ratio=2), Layout(name="peers", ratio=1)
    )
    layout["bottom_others"].split_row(
        Layout(name="mini1", ratio=1),
        Layout(name="mini2", ratio=1),
        Layout(name="mini3", ratio=1),
    )
    layout["mini1"].split_column(Layout(name="maxrss"), Layout(name="discarded"))
    layout["mini2"].split_column(Layout(name="rexmit"), Layout(name="trexmit"))
    layout["mini3"].split_column(Layout(name="tthrottle"), Layout(name="nthrottle"))

    layout["header"].update(Header(" ".join(cmd)))
    layout["latencies_perhost"].update(Text(""))
    layout["latencies_combined"].update(Text(""))
    layout["peers"].update(Text(""))
    layout["maxrss"].update(Text(""))
    layout["discarded"].update(Text(""))
    layout["rexmit"].update(Text(""))
    layout["trexmit"].update(Text(""))
    layout["tthrottle"].update(Text(""))
    layout["nthrottle"].update(Text(""))
    return layout


def make_ping_updater():
    data_re = re.compile(
        r"\[\d*\] [\d\.]+\s+([^\s:]+):(\d+) size \d+ mean ([\d\.]+)(n|u|m|s)s min ([\d\.]+)(n|u|m|s)s 50% ([\d\.]+)(n|u|m|s)s 90% ([\d\.]+)(n|u|m|s)s 99% ([\d\.]+)(n|u|m|s)s max (?:[\d\.]+)(?:n|u|m|s)s cnt (\d+)"
    )
    peer_re = re.compile(r"\[\d+\] participant ([^:]+):(\d+): (.*)$")
    rss_re = re.compile(r"rss:([\d\.]+)(kb|MB)")
    discarded_re = re.compile(r"discarded ([\d\.]+)")
    rexmit_re = re.compile(r" rexmit ([\d\.]+)")
    trexmit_re = re.compile(r" Trexmit ([\d\.]+)")
    tthrottle_re = re.compile(r" Tthrottle ([\d\.]+)")
    nthrottle_re = re.compile(r" Nthrottle ([\d\.]+)")

    cols = ["green", "blue", "magenta", "cyan", "white", "red"]

    graphs = {}
    graphs["peers"] = PeerPanel(True)
    graphs["latencies_perhost"] = ScrollGraph(
        "Latency per host (waiting for data)", 10, "bright_cyan"
    )
    graphs["latencies_combined"] = MultiScrollGraph("Mean Ping latency (µs)", 20)
    graphs["maxrss"] = ScrollGraph("MaxRSS", 10, "bright_cyan")
    graphs["discarded"] = ScrollGraph("Discarded msg", 10, "bright_green", delta=True)
    graphs["rexmit"] = ScrollGraph("Rexmit", 10, "bright_green", delta=True)
    graphs["trexmit"] = ScrollGraph("TRexmit", 10, "bright_green")
    graphs["tthrottle"] = ScrollGraph("Tthrottle", 10, "bright_green")
    graphs["nthrottle"] = ScrollGraph("Nthrottle", 10, "bright_green", delta=True)

    latency_graphs = []
    host_index = {}
    categories = ["mean", "min", "50%", "90%", "99%"]  # , "max"]
    data = [0] * len(categories)
    mult = {"n": 0.001, "u": 1, "m": 1000, "s": 1000000}

    counter = 0
    timepoint = datetime.now()

    def updater(line):
        nonlocal timepoint, counter
        updated = set()

        if datetime.now() - timepoint > timedelta(seconds=3):
            timepoint = datetime.now()
            if len(latency_graphs) > 1:
                counter = (counter + 1) % len(latency_graphs)
                updated.add("latencies_perhost")
                latency_graphs[counter].update_chart_vars(
                    **graphs["latencies_perhost"]._chart_kwargs
                )
                graphs["latencies_perhost"] = latency_graphs[counter]

        m = data_re.match(line)
        if m:
            updated.add("latencies_perhost")
            updated.add("latencies_combined")
            host, pid = m.group(1, 2)
            for i in range(len(categories)):
                data[i] = float(m.group(3 + 2 * i)) * mult[m.group(4 + 2 * i)]
            # count = m.group(15)

            key = f"{host}:{pid}"
            if key not in host_index:
                color = graphs["peers"].get_peer_color(host, pid)
                index = graphs["latencies_combined"].add_new_line(color)
                host_index[key] = index

                counter = len(latency_graphs)
                latency_graphs.append(
                    MultiScrollGraph(f"[bold][{color}]{host}[/]:{pid}[/]", 20)
                )
                latency_graphs[-1].update_chart_vars(
                    **graphs["latencies_perhost"]._chart_kwargs
                )
                graphs["latencies_perhost"] = latency_graphs[-1]
                for i in range(len(categories)):
                    latency_graphs[-1].add_new_line(cols[i])

            index = host_index[key]
            for i in range(len(categories)):
                latency_graphs[index].add_point(i, data[i])
            graphs["latencies_combined"].add_point(index, data[0])

        rss = rss_re.search(line)
        if rss:
            updated.add("maxrss")
            graphs["maxrss"].add_point(
                float(rss.group(1)) * (1000000 if rss.group(2) == "MB" else 1000)
            )

        discarded_m = discarded_re.search(line)
        if discarded_m:
            updated.add("discarded")
            graphs["discarded"].add_point(int(discarded_m.group(1)))

        rexmit_m = rexmit_re.search(line)
        if rexmit_m:
            updated.add("rexmit")
            graphs["rexmit"].add_point(int(rexmit_m.group(1)))

        trexmit_m = trexmit_re.search(line)
        if trexmit_m:
            updated.add("trexmit")
            graphs["trexmit"].add_point(int(trexmit_m.group(1)))

        tthrottle_m = tthrottle_re.search(line)
        if tthrottle_m:
            updated.add("tthrottle")
            graphs["tthrottle"].add_point(int(tthrottle_m.group(1)))

        nthrottle_m = nthrottle_re.search(line)
        if nthrottle_m:
            updated.add("nthrottle")
            graphs["nthrottle"].add_point(int(nthrottle_m.group(1)))

        peer_m = peer_re.match(line)
        if peer_m:
            updated.add("peers")
            host, pid, action = peer_m.group(1), peer_m.group(2), peer_m.group(3)
            if action == "new (self)":
                graphs["peers"].set_own(host, pid)
            elif action == "new":
                graphs["peers"].add_peer(host, pid)
            elif action == "gone":
                graphs["peers"].remove_peer(host, pid)

        return updated

    return updater, graphs
