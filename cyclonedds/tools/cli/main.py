import rich_click as click

from .settings import CONTEXT_SETTINGS
from .ls import ls
from .ps import ps
from .typeof import typeof
from .sub import subscribe
from .ddsperf import performance


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    # Initialize the CLI group
    pass


cli.add_command(ls)
cli.add_command(ps)
cli.add_command(typeof)
cli.add_command(subscribe)
cli.add_command(performance)

if __name__ == "__main__":
    cli()
