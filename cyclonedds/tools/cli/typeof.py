from threading import Thread
import rich_click as click
from rich.console import Console
from rich.syntax import Syntax

from .utils import TimeDeltaParamType, LiveData, background_progress_viewer
from .discovery.main import type_discovery


@click.command(short_help="Fetch and display reconstructed IDL of a type over XTypes")
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
def typeof(topic, id, runtime, suppress_progress_bar, color):
    """Fetch and display reconstructed IDL of a type over XTypes"""
    console = Console(color_system=None if color == "none" else color)
    live = LiveData(console)

    thread = Thread(target=type_discovery, args=(live, id, runtime, topic))
    thread.start()

    console.print()
    background_progress_viewer(runtime, live, suppress_progress_bar)

    thread.join()

    if not live.result:
        console.print(
            "[bold red] :police_car_light: No types could be discovered over XTypes[/]"
        )
    elif len(live.result) > 1:
        console.print("[bold orange] :warning: Multiple type definitions exist")

    if live.result:
        for _, code, pp in live.result:
            console.print(
                f"As defined in participant(s) [magenta]"
                + ", ".join(f"{p}" for p in pp)
            )
            console.print(Syntax(code, "omg-idl"))
            console.print()
