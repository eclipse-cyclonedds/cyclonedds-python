import uuid
from cyclonedds.builtin import DcpsEndpoint, DcpsParticipant
from cyclonedds.core import Qos, Policy
from cyclonedds.idl._typesupport.DDS.XTypes import TypeIdentifier, EK_COMPLETE
from dataclasses import dataclass
from typing import List, Optional

from rich.console import Console, ConsoleOptions, RenderResult, Group, NewLine, group
from rich.panel import Panel
from rich.pretty import Pretty
from rich.padding import Padding
from rich.columns import Columns
from rich.table import Table, Column

from ..qosformat import rich_format_policy


def fmt_ident(tid: TypeIdentifier) -> str:
    if tid is None:
        return f"unset"

    if tid.discriminator == EK_COMPLETE:
        return f"COMPLETE {tid.equivalence_hash.hex().upper()}"
    else:
        return f"MINIMAL {tid.equivalence_hash.hex().upper()}"


@group()
def rich_qos(qos):
    for policy in qos:
        yield rich_format_policy(policy)


@dataclass
class Discoverable:
    pass


@dataclass
class DParticipant(Discoverable):
    sample: DcpsParticipant
    topics: List["DTopic"]
    is_self: bool = False

    def name(self):
        if Policy.EntityName in self.sample.qos:
            return self.sample.qos[Policy.EntityName].name
        return None

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        name = self.name()
        title = (
            f"[bold magenta]{name}[/] ([bold magenta]{self.sample.key}[/])"
            if name
            else f"[bold magenta]{self.sample.key}[/]"
        )
        yield Panel.fit(
            self.get_subcontent(console, options), title=f"Participant {title}"
        )

    @group()
    def get_subcontent(self, console: Console, options: ConsoleOptions) -> Group:
        yield ""

        qos = self.sample.qos
        name = None
        if Policy.EntityName in qos:
            name = qos[Policy.EntityName]
            qos = qos - Qos(name)
            name = name.name

        if qos.policies:
            yield Panel.fit(
                rich_qos(qos), border_style="cyan", title="[bold bright_cyan] QoS"
            )
            yield ""

        for topic in self.topics:
            yield from topic.__rich_console__(console, options)


@dataclass
class DPubSub:
    name: Optional[str]
    endpoint: DcpsEndpoint
    qos: Qos  # without EntityName


@dataclass
class DTopic(Discoverable):
    name: str
    publications: List[DPubSub]
    subscriptions: List[DPubSub]

    def shared_qos(self, entities: List[DPubSub]) -> Qos:
        if not entities:
            return Qos()

        if len(entities) == 1:
            return entities[0].qos

        head, tail = entities[0], entities[1:]
        shared = []

        for policy in head.qos:
            for other in tail:
                if policy not in other.qos:
                    break
            else:
                shared.append(policy)

        return Qos(*shared)

    def unshared_qos(self, shared_qos: Qos, entities: List[DPubSub]) -> List[Qos]:
        return [Qos(*[p for p in h.qos if p not in shared_qos]) for h in entities]

    @group()
    def render(self):
        pubsub = self.subscriptions + self.publications

        if not pubsub:
            return

        common_qos = self.shared_qos(pubsub)
        common_writer_qos = (
            self.shared_qos(self.publications) if self.publications else common_qos
        )
        common_reader_qos = (
            self.shared_qos(self.subscriptions) if self.subscriptions else common_qos
        )
        writer_qos = self.unshared_qos(common_writer_qos, self.publications)
        reader_qos = self.unshared_qos(common_reader_qos, self.subscriptions)
        common_writer_qos = common_writer_qos - common_qos
        common_reader_qos = common_reader_qos - common_qos
        writer_qos_consistent = all(not q.policies for q in writer_qos)
        reader_qos_consistent = all(not q.policies for q in reader_qos)

        typename = pubsub[0].endpoint.type_name
        if not all(t.endpoint.type_name == typename for t in pubsub):
            typename = ":police_car_light: [bold red]Inconsistent, see below[/]"
            typename_consistent = False
        else:
            typename = f"[bold magenta]{typename}[/]"
            typename_consistent = True

        type_id = pubsub[0].endpoint.type_id
        if not all(t.endpoint.type_id == type_id for t in pubsub):
            type_id = ":police_car_light: [bold orange]Inconsistent, see below[/]"
            type_id_consistent = False
        else:
            type_id = f"[bold magenta]{fmt_ident(type_id)}[/]"
            type_id_consistent = True

        properties = Table(show_header=False)
        properties.add_column("Key", justify="left", no_wrap=True)
        properties.add_column("Value", justify="right", no_wrap=True)
        properties.add_row("Typename", typename)
        properties.add_row("XTypes Type ID", type_id)

        if not common_writer_qos and not common_reader_qos:
            qos_display = Panel.fit(
                rich_qos(common_qos),
                border_style="cyan",
                title="[bold bright_cyan]Common QoS[/]",
            )
        else:
            qos_display = Table.grid()
            qos_display.add_column()
            qos_display.add_column()
            qos_display.add_column()
            qos_display.add_row(
                Panel.fit(
                    rich_qos(common_qos),
                    border_style="cyan",
                    title="[bold bright_cyan]Common QoS[/]",
                ),
                Panel.fit(
                    rich_qos(common_writer_qos),
                    border_style="cyan",
                    title="[bold bright_cyan]Common Writer QoS[/]",
                ),
                Panel.fit(
                    rich_qos(common_reader_qos),
                    border_style="cyan",
                    title="[bold bright_cyan]Common Reader QoS[/]",
                ),
            )

        pub_display = None
        sub_display = None

        if self.publications:
            pub_display = Table(title="Publications")
            pub_display.add_column("GUID", no_wrap=True)

            if not typename_consistent or not type_id_consistent:
                pub_display.add_column("Properties")

            if not writer_qos_consistent:
                pub_display.add_column("QoS")

            for pub, qos in zip(self.publications, writer_qos):
                if pub.name:
                    row = [f"[bold blue]{pub.name} ({pub.endpoint.key})[/]"]
                else:
                    row = [f"[bold blue]{pub.endpoint.key}[/]"]

                if not typename_consistent or not type_id_consistent:
                    props = []

                    if pub.endpoint.type_name != typename:
                        props.append(
                            f"Typename: [bold magenta]{pub.endpoint.type_name}[/]"
                        )

                    if pub.endpoint.type_id != type_id:
                        props.append(
                            f"XTypes Type ID: [bold magenta]{fmt_ident(pub.endpoint.type_id)}[/]"
                        )

                    if not props:
                        row.append("")
                    elif len(props) == 1:
                        row.append(props[0])
                    else:
                        row.append(Group(*props))

                if not writer_qos_consistent and qos:
                    row.append(rich_qos(qos))

                pub_display.add_row(*row)

        if self.subscriptions:
            sub_display = Table(title="Subscriptions")
            sub_display.add_column("GUID", no_wrap=True)

            if not typename_consistent or not type_id_consistent:
                sub_display.add_column("Properties")

            if not reader_qos_consistent:
                sub_display.add_column("QoS")

            for sub, qos in zip(self.subscriptions, reader_qos):
                if sub.name:
                    row = [f"[bold blue]{sub.name} ({sub.endpoint.key})[/]"]
                else:
                    row = [f"[bold blue]{sub.endpoint.key}[/]"]

                if not typename_consistent or not type_id_consistent:
                    props = []

                    if sub.endpoint.type_name != typename:
                        props.append(
                            f"Typename: [bold magenta]{sub.endpoint.type_name}[/]"
                        )

                    if sub.endpoint.type_id != type_id:
                        props.append(
                            f"XTypes Type ID: [bold magenta]{fmt_ident(sub.endpoint.type_id)}[/]"
                        )

                    if not props:
                        row.append("")
                    elif len(props) == 1:
                        row.append(props[0])
                    else:
                        row.append(Group(*props))

                if not reader_qos_consistent and qos:
                    row.append(rich_qos(qos))

                sub_display.add_row(*row)

        # render
        yield qos_display
        yield properties

        if pub_display:
            yield pub_display

        if sub_display:
            yield sub_display

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield Panel.fit(self.render(), title=f"[bold green]{self.name}[/]")
