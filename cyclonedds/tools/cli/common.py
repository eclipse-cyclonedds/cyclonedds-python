from .discovery.type_discoverables import TypeDiscoveryData, DiscoveredType
from typing import Optional
from rich.syntax import Syntax
from rich.prompt import Prompt
from rich.console import Console
from cyclonedds.qos import Qos, Policy
from .qosformat import rich_qos
import random


def select_type(
    console: Console, data: Optional[TypeDiscoveryData], pick_random: bool
) -> Optional[DiscoveredType]:
    types = list(data.types.values())
    if data is None or len(types) == 0:
        console.print(
            "[bold red] :police_car_light: No types could be discovered over XTypes, no dynamism possible[/]"
        )
        return
    elif len(types) == 1:
        return types[0]
    elif pick_random:
        return random.choice(types)

    console.print(
        "[bold orange] :warning: Multiple type definitions exist, please pick one"
    )

    for i, dtype in enumerate(types):
        console.print(
            f"Type {i}, As defined in participant(s) [magenta]"
            + ", ".join(f"{p}" for p in dtype.participants)
        )
        console.print(Syntax(dtype.code, "omg-idl"))
        console.print()

    index = Prompt.ask(
        "Please pick a type",
        choices=[str(i) for i in range(len(types))],
    )
    index = int(index)
    return types[index]


def _filter_non_override(base_qos: Qos, override_qos: Qos) -> Qos:
    return Qos(
        *[p for p in override_qos.policies if p not in base_qos or base_qos[p] != p]
    )


def select_qos(
    console: Console,
    data: Optional[TypeDiscoveryData],
    for_writer: bool,
    pick_random: bool,
) -> Qos:
    topic_qos_shared, topic_qos_mix = data.split_qos(data.topic_qosses)

    if (for_writer and data.writer_qosses) or not data.reader_qosses:
        endpoint_qosses = data.writer_qosses
    else:
        endpoint_qosses = data.reader_qosses

    endpoint_qos_shared, endpoint_qos_mix = data.split_qos(endpoint_qosses)

    if len(topic_qos_mix) <= 1:
        topic_qos = topic_qos_shared
    elif pick_random:
        topic_qos = topic_qos_shared + random.choice(topic_qos_mix)
    else:
        console.print(
            "[bold orange] :warning: Multiple Topic QoS configurations, please pick one"
        )

        if topic_qos_shared:
            console.print("[bold green]Common Topic QoS")
            console.print(rich_qos(topic_qos_shared))

        console.print("[bold green]Variants")

        for i, qos in enumerate(topic_qos_mix):
            console.print(f"[bold bright_cyan]Variant {i}")
            console.print(rich_qos(qos))

        index = Prompt.ask(
            "Please pick a QoS variant",
            choices=[str(i) for i in range(len(topic_qos_mix))],
        )
        index = int(index)
        topic_qos = topic_qos_shared + topic_qos_mix[index]

    if len(endpoint_qos_mix) <= 1:
        return topic_qos, endpoint_qos_shared
    elif pick_random:
        return topic_qos, endpoint_qos_shared + random.choice(endpoint_qos_mix)

    console.print(
        "[bold orange] :warning: Multiple Endpoint QoS configurations, please pick one"
    )

    shared_qos = topic_qos + endpoint_qos_shared

    if shared_qos:
        console.print("[bold green]Common Endpoint QoS")
        console.print(rich_qos(shared_qos))

    console.print("[bold green]Variants")

    for i, qos in enumerate(endpoint_qos_mix):
        console.print(f"[bold bright_cyan]Variant {i}")
        console.print(rich_qos(_filter_non_override(shared_qos, qos)))

    index = Prompt.ask(
        "Please pick a QoS variant",
        choices=[str(i) for i in range(len(endpoint_qos_mix))],
    )
    index = int(index)

    return topic_qos, shared_qos + endpoint_qos_mix[index]
