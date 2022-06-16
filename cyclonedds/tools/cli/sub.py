from threading import Thread
import rich_click as click
from rich import print
from rich.syntax import Syntax
from rich.prompt import Prompt
from rich.console import Console

from .utils import (
    TimeDeltaParamType,
    LiveData,
    background_progress_viewer,
    background_printer,
)
from .discovery.main import type_discovery
from .data import subscribe as data_subscribe


@click.command(short_help="Subscribe to an arbitrary topic")
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
def subscribe(topic, id, runtime, suppress_progress_bar, color):
    """Subscribe to an arbitrary topic"""
    console = Console(color_system=None if color == "none" else color)
    live = LiveData(console)

    thread = Thread(target=type_discovery, args=(live, id, runtime, topic))
    thread.start()

    console.print()
    background_progress_viewer(runtime, live, suppress_progress_bar)

    thread.join()

    if not live.result:
        console.print(
            "[bold red] :police_car_light: No types could be discovered over XTypes, no dynamic subsciption possible[/]"
        )
        return
    elif len(live.result) > 1:
        console.print(
            "[bold orange] :warning: Multiple type definitions exist, please pick one"
        )

        for i, (_, code, pp) in enumerate(live.result):
            console.print(
                f"Type {i}, As defined in participant(s) [magenta]"
                + ", ".join(f"{p}" for p in pp)
            )
            console.print(Syntax(code, "omg-idl"))
            console.print()

        index = Prompt.ask(
            "Please pick a type:",
            choices=[f"Type {i}" for i in range(len(live.result))],
        )
        index = int(index[len("Type: ") :])

        datatype = live.result[i][0]
    else:
        datatype = live.result[0][0]

    console.print("[bold green] Subscribing, CTRL-C to quit")

    thread = Thread(target=data_subscribe, args=(live, id, topic, datatype))
    thread.start()

    console.print()
    background_printer(live)
    console.print()

    thread.join()
