import rich_click as click
from rich.syntax import Syntax
from rich.console import Console

from .layout.ping import make_ping_layout, make_ping_updater
from .layout.pong import make_pong_layout, make_pong_updater
from .layout.subscribe import make_sub_layout, make_sub_updater
from .layout.publish import make_pub_layout, make_pub_updater
from .layout.app import DDSPerfApp
from .utils import TimeDeltaParamType, RateParamType, SizeParamType


@click.group()
@click.option(
    "-T",
    "--topic",
    default="KS",
    type=click.Choice(
        ["KS", "K32", "K256", "OU", "UK16", "UK1024", "S16", "S256", "S4k", "S32k"]
    ),
    help="""Topic (KS is default). Print topic information with [bold yellow]cyclonedds performance topics[/]""",
)
@click.option(
    "-n",
    "--num-keys",
    type=int,
    help="Number of key values to use for data (only for topics with a key value)",
)
@click.option(
    "-u", "--unreliable", is_flag=True, help="Use best-effort instead of reliable"
)
@click.option(
    "-k",
    "--keep",
    metavar="<all,n>",
    help="Keep-all or keep-last-N for data (ping/pong is always keep-last-1)",
)
@click.option(
    "-c", "--cpu", is_flag=True, help="Subscribe to CPU stats from peers and show them"
)
@click.option(
    "-d",
    "--device-load",
    metavar="<device:bandwidth>",
    help="Report network load for device DEV with nominal bandwidth BW in bits/s (e.g., eth0:1e9)",
)
@click.option(
    "-D",
    "--duration",
    type=TimeDeltaParamType(),
    help="Set max duration, integer number of seconds or timestring like '1h23m11s'",
)
@click.option(
    "-L",
    "--local-matching",
    is_flag=True,
    help="Allow matching with endpoints in the same process to get throughput/latency in the same ddsperf process",
)
@click.option(
    "-Q",
    "--success-criterion",
    multiple=True,
    help="""Set success criteria
  [bold yellow]rss:X%[/] max allowed increase in RSS, in %,
  [bold yellow]rss:X[/] max allowed increase in RSS, in MB,
  [bold yellow]samples:N[/] min received messages by "sub",
  [bold yellow]roundtrips:N[/] min roundtrips for "pong",
  [bold yellow]minmatch:N[/] require >= N matching participants,
  [bold yellow]initwait:DUR[/] wait for those participants before starting, abort if not within DUR seconds,
  [bold yellow]maxwait:DUR[/] require those participants to match within DUR seconds,
""",
)
@click.option(
    "-R",
    "--reference-time",
    metavar="<TREF>",
    help="Show timestamps in the output relative to TREF instead of process start",
)
@click.option(
    "-W",
    "--wait-match-max",
    type=TimeDeltaParamType(),
    help="""
Maximum waittime for the minimum required number of matching participants (set by [bold green]-Qminmatch:N[/])
to show up before starting reading/writing data, terminate with an error otherwise. This differs
from [bold green]-Qmaxwait:DUR[/] because that doesn't delay starting and doesn't terminate the process before doing
anything""",
)
@click.option(
    "-i",
    "--domain-id",
    metavar="<ID>",
    help="Use domain ID instead of the default domain",
)
@click.option(
    "--color",
    type=click.Choice(["auto", "standard", "256", "truecolor", "windows", "none"]),
    default="auto",
    help="""Force the command to output with/without terminal colors. By default output colours if the terminal supports it."
See the [underline blue][link=https://rich.readthedocs.io/en/stable/console.html#color-systems]Rich documentation[/link][/] for more info on what the options mean.""",
)
@click.option(
    # This option is used for the sake of documentation image generation.
    "--render-output-once-on-exit",
    hidden=True,
    is_flag=True,
)
@click.pass_context
def performance(
    ctx,
    local_matching,
    topic,
    num_keys,
    unreliable,
    keep,
    cpu,
    device_load,
    duration,
    success_criterion,
    reference_time,
    wait_match_max,
    domain_id,
    color,
    render_output_once_on_exit,
):
    """Run CycloneDDS performance tests on your system.\b

    [bold blue]Examples[/]

    [bold][bright_yellow]cyclonedds performance publisher[/] [green]--size[/] [red]1000[/]
    [bright_yellow]cyclonedds performance subscriber[/][/]

    -   [i]basic throughput test with 1024-byte samples[/]

    [bold][bright_yellow]cyclonedds performance ping
    cyclonedds performance pong[/][/]

    -   [i]basic latency test[/]
    """

    cmd = ["ddsperf", "-1", "-X"]

    if local_matching:
        cmd.append("-L")

    if topic is not None:
        cmd += ["-T", topic]

    if num_keys is not None:
        cmd += ["-n", f"{num_keys}"]

    if unreliable:
        cmd.append("-u")

    if keep is not None:
        cmd += ["-k", keep]

    if cpu:
        cmd.append("-c")

    if device_load is not None:
        cmd += ["-c", device_load]

    if duration is not None:
        cmd += ["-D", f"{duration.total_seconds()}"]

    for sct in success_criterion:
        cmd += [f"-Q{sct}"]

    if reference_time is not None:
        cmd += ["-R", reference_time]

    if wait_match_max is not None:
        cmd += ["-W", f"{wait_match_max.total_seconds()}"]

    if domain_id is not None:
        cmd += ["-i", str(domain_id)]

    ctx.ensure_object(dict)
    ctx.obj["ddsperf"] = cmd
    ctx.obj["color"] = color
    ctx.obj["render_output_once"] = render_output_once_on_exit


@performance.command("ping", short_help="Send pings")
@click.option(
    "-r", "--rate", type=RateParamType(), help="The rate at which to send pings"
)
@click.option(
    "-s",
    "--size",
    type=SizeParamType(),
    help="May be set if the topic is KS, specifies the (total) payload size in bytes",
)
@click.option(
    "-m",
    "--triggering-mode",
    default="listener",
    type=click.Choice(["listener", "waitset"]),
)
@click.pass_context
def ping(ctx, rate, size, triggering_mode):
    """Send a ping upon receiving all expected pongs, or send a ping at
    rate R (optionally suffixed with Hz/kHz). The triggering mode is either
    a listener (default, unless [i]local matching[/] has been specified) or a waitset."""

    cmd = ["ping"]

    if rate is not None:
        cmd += [f"{rate}"]

    if size is not None:
        cmd += ["size", f"{size}"]

    if triggering_mode:
        cmd += [triggering_mode]

    DDSPerfApp(
        Console(color_system=None if ctx.obj["color"] == "none" else ctx.obj["color"]),
        ctx.obj["ddsperf"] + cmd,
        make_ping_layout,
        make_ping_updater,
    ).run(ctx.obj["render_output_once"])


@performance.command("pong", short_help="Send pongs")
@click.option(
    "-m",
    "--triggering-mode",
    default="listener",
    type=click.Choice(["listener", "waitset"]),
)
@click.pass_context
def pong(ctx, triggering_mode):
    """A "dummy" mode that serves two purposes: configuring the triggering.
    mode (but it is shared with ping's mode), and suppressing the 1Hz ping
    if no other options are selected.  It always responds to pings."""

    cmd = ["pong"]

    if triggering_mode:
        cmd += [triggering_mode]

    DDSPerfApp(
        Console(color_system=None if ctx.obj["color"] == "none" else ctx.obj["color"]),
        ctx.obj["ddsperf"] + cmd,
        make_pong_layout,
        make_pong_updater,
    ).run(ctx.obj["render_output_once"])


@performance.command("subscribe", short_help="Subscribe to data")
@click.option(
    "-m",
    "--triggering-mode",
    default="listener",
    type=click.Choice(["listener", "waitset", "polling"]),
)
@click.pass_context
def subscribe(ctx, triggering_mode):
    """Subscribe to data, with calls to take occurring either in a listener
    (default), when a waitset is triggered, or by polling at 1kHz."""

    cmd = ["sub"]

    if triggering_mode:
        cmd += [triggering_mode]

    DDSPerfApp(
        Console(color_system=None if ctx.obj["color"] == "none" else ctx.obj["color"]),
        ctx.obj["ddsperf"] + cmd,
        make_sub_layout,
        make_sub_updater,
    ).run(ctx.obj["render_output_once"])


@performance.command("publish", short_help="Publish data")
@click.option("-r", "--rate", type=RateParamType(), help="The rate at which to publish")
@click.option(
    "-s",
    "--size",
    type=SizeParamType(),
    help="May be set if the topic is KS, specifies the (total) payload size in bytes",
)
@click.option("-b", "--burst", type=int)
@click.option("-p", "--ping", type=int)
@click.pass_context
def pub(ctx, rate, size, burst, ping):
    """Publish bursts of data at a set rate or as fast as possible if unspecified.
    Each burst is a single sample by default, but can be set to larger value using
    "--burst N". Sample size is controlled using the size parameter when the KS topic
    is used, minimal size is used when unspecified.
    If desired, a fraction of the samples can be treated as if it were a
    ping, for this, specify a percentage with "--ping 50" for fifty percent."""

    cmd = ["pub"]

    if rate is not None:
        cmd += [f"{rate}"]

    if size is not None:
        cmd += ["size", f"{size}"]

    if burst is not None:
        cmd += ["burst", f"{burst}"]

    if ping is not None:
        cmd += ["ping", f"{ping}%"]

    DDSPerfApp(
        Console(color_system=None if ctx.obj["color"] == "none" else ctx.obj["color"]),
        ctx.obj["ddsperf"] + cmd,
        make_pub_layout,
        make_pub_updater,
    ).run(ctx.obj["render_output_once"])


@performance.command(
    "topics", short_help="Show information about the performance topic types."
)
@click.pass_context
def topics(ctx):
    """Show information about the performance topic types."""
    console = Console(
        color_system=None if ctx.obj["color"] == "none" else ctx.obj["color"]
    )

    # KS
    console.rule("KS, Keyed Sequence (default)")
    console.print(
        Syntax(
            """@final
struct KeyedSeq
{
  unsigned long seq;         // sequence number
  @key unsigned long keyval; // key
  sequence<octet> baggage;   // variable-sized content
};""",
            "omg-idl",
        )
    )

    # K32
    console.rule("K32, Keyed 32 bytes")
    console.print(
        Syntax(
            """@final
struct Keyed32
{
  unsigned long seq;         // sequence number
  @key unsigned long keyval; // key
  octet baggage[24];         // content
};""",
            "omg-idl",
        )
    )

    # K256
    console.rule("K256, Keyed 256 bytes")
    console.print(
        Syntax(
            """@final
struct Keyed256
{
  unsigned long seq;         // sequence number
  @key unsigned long keyval; // key
  octet baggage[248];        // content
};""",
            "omg-idl",
        )
    )

    # OU
    console.rule("OU, One ULong")
    console.print(
        Syntax(
            """@final
struct OneULong
{
  unsigned long seq;         // sequence number
};""",
            "omg-idl",
        )
    )

    # UK16
    console.rule("UK16, Unkeyed 16 bytes")
    console.print(
        Syntax(
            """@final
struct Unkeyed16
{
  unsigned long seq; // sequence number
  octet baggage[12]; // content
};""",
            "omg-idl",
        )
    )

    # UK1024
    console.rule("UK1024, Unkeyed 1024 bytes")
    console.print(
        Syntax(
            """@final
struct Unkeyed1024
{
  unsigned long seq;   // sequence number
  octet baggage[1020]; // content
};""",
            "omg-idl",
        )
    )

    # S16
    console.rule("S16, Keyed, 16 octets")
    console.print(
        Syntax(
            """@final
struct Struct16 {
  octet struct0;
  octet struct1;
  octet struct2;
  octet struct3;
  octet struct4;
  octet struct5;
  octet struct6;
  octet struct7;
  octet struct8;
  octet struct9;
  octet structa;
  octet structb;
  octet structc;
  octet structd;
  octet structe;
  octet structf;
  long long junk;
  unsigned long seq;
  @key unsigned long keyval;
};""",
            "omg-idl",
        )
    )

    # S256
    console.rule("S256, Keyed, 16 Struct16's")
    console.print(
        Syntax(
            """@final
struct Struct256 {
  Struct16 struct160;
  Struct16 struct161;
  Struct16 struct162;
  Struct16 struct163;
  Struct16 struct164;
  Struct16 struct165;
  Struct16 struct166;
  Struct16 struct167;
  Struct16 struct168;
  Struct16 struct169;
  Struct16 struct16a;
  Struct16 struct16b;
  Struct16 struct16c;
  Struct16 struct16d;
  Struct16 struct16e;
  Struct16 struct16f;
  long long junk;
  unsigned long seq;
  @key unsigned long keyval;
};""",
            "omg-idl",
        )
    )

    # S4k
    console.rule("S4k, Keyed, 16 Struct256's")
    console.print(
        Syntax(
            """@final
struct Struct4k {
  Struct256 struct2560;
  Struct256 struct2561;
  Struct256 struct2562;
  Struct256 struct2563;
  Struct256 struct2564;
  Struct256 struct2565;
  Struct256 struct2566;
  Struct256 struct2567;
  Struct256 struct2568;
  Struct256 struct2569;
  Struct256 struct256a;
  Struct256 struct256b;
  Struct256 struct256c;
  Struct256 struct256d;
  Struct256 struct256e;
  Struct256 struct256f;
  long long junk;
  unsigned long seq;
  @key unsigned long keyval;
};""",
            "omg-idl",
        )
    )

    # S32k
    console.rule("S32k, Keyed, 8 Struct4k's")
    console.print(
        Syntax(
            """@final
struct Struct32k {
  Struct4k struct4k0;
  Struct4k struct4k1;
  Struct4k struct4k2;
  Struct4k struct4k3;
  Struct4k struct4k4;
  Struct4k struct4k5;
  Struct4k struct4k6;
  Struct4k struct4k7;
  long long junk;
  unsigned long seq;
  @key unsigned long keyval;
};""",
            "omg-idl",
        )
    )

    return None
