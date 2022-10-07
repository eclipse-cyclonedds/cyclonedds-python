from threading import Thread
from code import InteractiveConsole
import rich_click as click
import json
from rich import print
from rich.syntax import Syntax
from rich.prompt import Prompt
from rich.console import Console
from cyclonedds import domain, pub, topic as cyclone_topic
from cyclonedds.qos import Qos

try:
    import readline
except ImportError:
    pass

from .utils import (
    TimeDeltaParamType,
    LiveData,
    background_progress_viewer,
    background_printer,
)
from .discovery.main import type_discovery
from .data import subscribe as data_subscribe
from .common import select_type, select_qos


@click.command(short_help="Publish to an arbitrary topic")
@click.argument("topic")
@click.option(
    "-i", "--id", "--domain-id", type=int, default=0, help="DDS Domain to inspect."
)
@click.option(
    "-r",
    "--runtime",
    type=TimeDeltaParamType(),
    default="1s",
    help="Duration of discovery scan.",
)
@click.option(
    "--suppress-progress-bar",
    type=bool,
    is_flag=True,
    help="Suppress the output of the progress bar",
)
@click.option(
    "--color",
    type=click.Choice(["auto", "standard", "256", "truecolor", "windows", "none"]),
    default="auto",
    help="""Force the command to output with/without terminal colors. By default output colours if the terminal supports it."
See the [underline blue][link=https://rich.readthedocs.io/en/stable/console.html#color-systems]Rich documentation[/link][/] for more info on what the options mean.""",
)
@click.option(
    "--qos",
    type=click.Choice(["scan", "scan-random", "dds-default", "json"]),
    default="scan",
    help="""Method to determine the QoS settings of the writer. With "scan" the network is scanned for existing QoS used.
"scan-random" functions the same way but does not prompt for input, but simply picks a random QoS in case of conflicts.
With "dds-default" the default QoS from the DDS specification is used and with  "json" your first line of input should be a
json string with the QoS settings, defined by the output of `cyclonedds.qos.Qos.asdict()`.""",
)
@click.option(
    "--type",
    type=click.Choice(["scan", "scan-random"]),
    default="scan",
    help="""Method to determine the datatype of the writer. With "scan" the network is scanned for existing types using XTypes.
"scan-random" functions the same way but does not prompt for input, but simply picks a random datatype in case of conflicts.""",
)
def publish(topic, id, runtime, suppress_progress_bar, color, qos, type):
    """Publish to an arbitrary topic"""

    if qos == "json":
        try:
            qos_endpoint = Qos.fromdict(json.loads(input()))
            qos_topic = qos_endpoint
        except:
            return 1

    console = Console(color_system=None if color == "none" else color)
    live = LiveData(console)

    thread = Thread(target=type_discovery, args=(live, id, runtime, topic))
    thread.start()

    background_progress_viewer(runtime, live, suppress_progress_bar)

    thread.join()

    if qos in ["scan", "scan-random"]:
        qos_topic, qos_endpoint = select_qos(
            console, live.result, True, qos == "scan-random"
        )
    elif qos == "dds-default":
        qos_topic, qos_endpoint = Qos(), Qos()

    discovered_type = select_type(console, live.result, type == "scan-random")

    if not discovered_type:
        return

    console.print("Your datatypes are:")

    console.print(Syntax(discovered_type.code, "omg-idl"))
    console.print(
        "Available in your python REPL: [bold green]participant, topic, writer, [bold magenta]"
        + ", ".join(discovered_type.nested_dtypes.keys())
    )
    console.print("[bold green] Publishing, run exit() to quit")

    dp = domain.DomainParticipant(id)
    tp = cyclone_topic.Topic(dp, topic, discovered_type.dtype, qos=qos_topic)
    dw = pub.DataWriter(dp, tp, qos=qos_endpoint)

    vars = {"participant": dp, "topic": tp, "writer": dw}
    vars.update(discovered_type.nested_dtypes)

    repl = InteractiveConsole(locals=vars)
    repl.push("from rich import pretty; pretty.install()")
    repl.interact(banner="")
