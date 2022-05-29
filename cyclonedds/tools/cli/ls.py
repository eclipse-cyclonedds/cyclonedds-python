from threading import Thread
import rich_click as click
from rich.console import Console

from .utils import TimeDeltaParamType, LiveData, background_progress_viewer
from .discovery.main import ls_discovery


@click.command(short_help="Scan and display DDS entities in your network")
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
    "-t",
    "--topic",
    type=str,
    help="Filter which entity types to display by topic name (supports regex)",
    default=".*",
)
@click.option(
    "--show-self",
    type=bool,
    is_flag=True,
    help="Show the tools own participant and subscriptions.",
)
@click.option(
    "--suppress-progress-bar",
    type=bool,
    is_flag=True,
    help="Suppress the output of the progress bar",
)
@click.option(
    "--force-color-mode",
    is_flag=True,
    help="Force the command to output with terminal colors, even if no support is detected.",
)
def ls(topic, id, runtime, show_self, suppress_progress_bar, force_color_mode):
    """Scan and display DDS entities in your network."""
    console = Console(color_system="auto" if force_color_mode else "truecolor")
    live = LiveData(console)

    thread = Thread(target=ls_discovery, args=(live, id, runtime, topic))
    thread.start()

    console.print()
    background_progress_viewer(runtime, live, suppress_progress_bar)

    thread.join()

    if live.result:
        for p in live.result:
            if p.is_self and not show_self:
                continue

            console.print(p)
            console.print()
