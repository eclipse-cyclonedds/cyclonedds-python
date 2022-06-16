import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Set

from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table


@dataclass
class Discoverable:
    pass


@dataclass
class PSystem:
    applications: List["PApplication"]

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        t = Table("Host", "Application", "Pid", "Participants", "Topics")
        for app in sorted(self.applications, key=lambda x: (x.hostname, x.pid)):
            r = app.row()
            if r:
                t.add_row(*r)
        yield t


@dataclass
class PApplication:
    hostname: str
    appname: str
    pid: str
    addresses: str
    participants: List["PParticipant"]

    def row(self) -> Sequence[RenderResult]:
        topics = [
            topic for topic in set().union(*(p.topics for p in self.participants))
        ]

        if not topics:
            return None

        return (
            self.hostname,
            self.appname,
            self.pid,
            "[bold magenta]" + "\n".join(str(p) for p in self.participants),
            "[bold bright_green]" + "\n".join(topics),
        )


@dataclass
class PParticipant(Discoverable):
    key: uuid.UUID
    topics: Set[str] = field(default_factory=set)
    name: Optional[str] = None

    def __str__(self):
        if self.name is not None:
            return f"{self.name} ({self.key})"
        return f"{self.key}"
