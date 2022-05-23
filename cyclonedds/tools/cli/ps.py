from threading import Thread
import rich_click as click
from rich import print

from .utils import TimeDeltaParamType, LiveData, background_progress_viewer
from .discovery.main import ps_discovery


@click.command(short_help="Scan and display DDS applications in your network")
@click.option('-i', '--id', '--domain-id', type=int, default=0, help="DDS Domain to inspect.")
@click.option('-r', '--runtime', type=TimeDeltaParamType(), default='1s', help="Duration of discovery scan.")
@click.option('-t', '--topic', type=str, help="Filter which entity types to display by topic name (supports regex)", default=".*")
@click.option('--show-self', type=bool, is_flag=True, help="Show the tools own application.")
def ps(id, runtime, topic, show_self):
    """Scan and display DDS applications in your network"""
    live = LiveData()

    thread = Thread(target=ps_discovery, args=(live, id, runtime, show_self, topic))
    thread.start()

    print()
    background_progress_viewer(runtime, live)
    print()

    thread.join()

    if live.result:
        live.result.show_self = show_self
        print(live.result)
