from threading import Thread
import rich_click as click
from rich import print
from rich.syntax import Syntax

from .utils import TimeDeltaParamType, LiveData, background_progress_viewer
from .discovery.main import type_discovery


@click.command(short_help="Fetch and display reconstructed IDL of a type over XTypes")
@click.argument("topic")
@click.option('-i', '--id', '--domain-id', type=int, default=0, help="DDS Domain to inspect.")
@click.option('-r', '--runtime', type=TimeDeltaParamType(), default='1s', help="Duration of discovery scan.")
def typeof(topic, id, runtime):
    """Fetch and display reconstructed IDL of a type over XTypes"""
    live = LiveData()

    thread = Thread(target=type_discovery, args=(live, id, runtime, topic))
    thread.start()

    print()
    background_progress_viewer(runtime, live)
    print()

    thread.join()

    if not live.result:
        print("[bold red] :police_car_light: No types could be discovered over XTypes[/]")
    elif len(live.result) > 1:
        print("[bold orange] :warning: Multiple type definitions exist")

    if live.result:
        for _, code, pp in live.result:
            print(f"As defined in participant(s) [magenta]"+ ", ".join(f"{p}" for p in pp))
            print(Syntax(code, 'omg-idl'))
            print()
