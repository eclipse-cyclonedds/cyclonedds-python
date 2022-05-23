from threading import Thread
import rich_click as click
from rich import print
from rich.syntax import Syntax
from rich.prompt import Prompt

from .utils import TimeDeltaParamType, LiveData, background_progress_viewer, background_printer
from .discovery.main import type_discovery
from .data import subscribe as data_subscribe


@click.command(short_help="Subscribe to an arbitrary topic")
@click.argument("topic")
@click.option('-i', '--id', '--domain-id', type=int, default=0, help="DDS Domain to inspect.")
@click.option('-r', '--runtime', type=TimeDeltaParamType(), default='1s', help="Duration of discovery scan.")
def subscribe(topic, id, runtime):
    """Subscribe to an arbitrary topic"""
    live = LiveData()

    thread = Thread(target=type_discovery, args=(live, id, runtime, topic))
    thread.start()

    print()
    background_progress_viewer(runtime, live)
    print()

    thread.join()

    if not live.result:
        print("[bold red] :police_car_light: No types could be discovered over XTypes, no dynamic subsciption possible[/]")
        return
    elif len(live.result) > 1:
        print("[bold orange] :warning: Multiple type definitions exist, please pick one")

        for i, (_, code, pp) in enumerate(live.result):
            print(f"Type {i}, As defined in participant(s) [magenta]"+ ", ".join(f"{p}" for p in pp))
            print(Syntax(code, 'omg-idl'))
            print()

        index = Prompt.ask("Please pick a type:", choices=[f"Type {i}" for i in range(len(live.result))])
        index = int(index[len("Type: "):])

        datatype = live.result[i][0]
    else:
        datatype = live.result[0][0]

    print("[bold green] Subscribing, CTRL-C to quit")

    thread = Thread(target=data_subscribe, args=(live, id, topic, datatype))
    thread.start()

    print()
    background_printer(live)
    print()

    thread.join()
