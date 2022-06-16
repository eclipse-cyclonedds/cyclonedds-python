import re
from rich.layout import Layout
from rich.text import Text

from .app import Header, CPUGraph, ScrollGraph, PeerPanel
from .barchart import RichChart


def make_sub_layout(cmd) -> Layout:
    layout = Layout(name="ddsperf_app")

    layout.split(
        Layout(name="header", size=3),
        Layout(name="main1", ratio=1),
        Layout(name="main2", ratio=1),
    )
    layout["main1"].split_row(
        Layout(name="samplerate", ratio=3),
        Layout(name="hist", ratio=2),
        Layout(name="peers", ratio=1),
    )
    layout["main2"].split_row(
        Layout(name="cpu", ratio=2),
        Layout(name="cpu_legend", ratio=1),
        Layout(name="mini1", ratio=1),
        Layout(name="mini2", ratio=1),
        Layout(name="mini3", ratio=1),
    )
    layout["mini1"].split_column(Layout(name="maxrss"), Layout(name="discarded"))
    layout["mini2"].split_column(Layout(name="rexmit"), Layout(name="trexmit"))
    layout["mini3"].split_column(Layout(name="tthrottle"), Layout(name="nthrottle"))

    layout["header"].update(Header(" ".join(cmd)))
    layout["cpu"].update(Text(""))
    layout["cpu_legend"].update(Text(""))
    layout["samplerate"].update(Text(""))
    layout["hist"].update(Text(""))
    layout["peers"].update(Text(""))
    layout["maxrss"].update(Text(""))
    layout["discarded"].update(Text(""))
    layout["rexmit"].update(Text(""))
    layout["trexmit"].update(Text(""))
    layout["tthrottle"].update(Text(""))
    layout["nthrottle"].update(Text(""))
    return layout


def make_sub_updater():
    data_re = re.compile(
        r"\[\d*\] [\d\.]+  size \d+ total \d+ lost \d+ delta \d+ lost \d+ rate ([\d\.]+) kS/s ([\d\.]+)"
    )
    csw_cpu_re = re.compile(r"vcsw:(\d+) ivcsw:(\d+)((?: \w+:\d+%\+\d+%)*)")
    cpu_singlet_re = re.compile(r"(\w+):(\d+)%\+(\d+)%")
    peer_re = re.compile(r"\[\d+\] participant ([^:]+):(\d+): (.*)$")
    rss_re = re.compile(r"rss:([\d\.]+)(kb|MB)")
    discarded_re = re.compile(r"discarded ([\d\.]+)")
    rexmit_re = re.compile(r" rexmit ([\d\.]+)")
    trexmit_re = re.compile(r" Trexmit ([\d\.]+)")
    tthrottle_re = re.compile(r" Tthrottle ([\d\.]+)")
    nthrottle_re = re.compile(r" Nthrottle ([\d\.]+)")

    y = []
    graphs = {}
    graphs["cpu"] = CPUGraph(10)
    graphs["peers"] = PeerPanel()
    graphs["samplerate"] = ScrollGraph("Samplerate(S/s)", 20, "bright_red")
    graphs["maxrss"] = ScrollGraph("MaxRSS", 10, "bright_cyan")
    graphs["discarded"] = ScrollGraph("Discarded msg", 10, "bright_green", delta=True)
    graphs["rexmit"] = ScrollGraph("Rexmit", 10, "bright_green", delta=True)
    graphs["trexmit"] = ScrollGraph("TRexmit", 10, "bright_green")
    graphs["tthrottle"] = ScrollGraph("Tthrottle", 10, "bright_green")
    graphs["nthrottle"] = ScrollGraph("Nthrottle", 10, "bright_green", delta=True)
    graphs["hist"] = RichChart(title="Samplerate histogram")

    def updater(line):
        updated = set()

        m = data_re.match(line)
        if m:
            updated.add("samplerate")
            updated.add("hist")
            y.append(float(m.group(1)) * 1000.0)
            if len(y) > 10000:
                y.pop(0)
            graphs["samplerate"].add_point(float(m.group(1)) * 1000.0)
            graphs["hist"].hist(y, "bright_red", index=0)

        m2 = csw_cpu_re.search(line)
        if m2:
            updated.add("cpu")
            graphs["cpu"].next_data(int(m2.group(1)), int(m2.group(2)))
            for m3 in cpu_singlet_re.finditer(m2.group(3)):
                name, user, system = m3.group(1), int(m3.group(2)), int(m3.group(3))
                graphs["cpu"].report_stats(name, user, system)

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
