from dataclasses import dataclass
from cyclonedds.qos import Policy
from cyclonedds.internal import dds_infinity
from rich.pretty import Pretty
from rich.text import Text
from datetime import timedelta


def fmtime(nanoseconds: int) -> str:
    if nanoseconds == dds_infinity:
        return "infinity"
    if nanoseconds == 0:
        return "zero"

    microseconds = nanoseconds // 1000
    nanoseconds -= microseconds * 1000
    milliseconds = microseconds // 1000
    microseconds -= milliseconds * 1000
    seconds = milliseconds // 1000
    milliseconds -= seconds * 1000
    minutes = seconds // 60
    seconds -= minutes * 60
    hours = minutes // 60
    minutes -= hours * 60
    days = hours // 24
    hours -= days * 24

    ret = "" if days == 0 else f"{days} day{'s' if days > 0 else ''}, "
    ret += "" if hours == 0 else f"{hours} hour{'s' if hours > 0 else ''}, "
    ret += "" if minutes == 0 else f"{minutes} minute{'s' if minutes > 0 else ''}, "
    ret += "" if seconds == 0 else f"{seconds} second{'s' if seconds > 0 else ''}, "
    ret += (
        ""
        if milliseconds == 0
        else f"{milliseconds} millisecond{'s' if milliseconds > 0 else ''}, "
    )
    ret += (
        ""
        if microseconds == 0
        else f"{microseconds} microsecond{'s' if microseconds > 0 else ''}, "
    )
    ret += (
        ""
        if nanoseconds == 0
        else f"{nanoseconds} nanosecond{'s' if nanoseconds > 0 else ''}, "
    )

    ret = ret[:-2]

    return ret


@dataclass
class Property:
    key: str
    value: str


@dataclass
class BinaryProperty:
    key: str
    value: bytes


def rich_format_policy(policy: Policy):
    if policy.__scope__ in [
        "Durability",
        "Ownership",
        "DestinationOrder",
        "IgnoreLocal",
    ] or policy in [Policy.Reliability.BestEffort, Policy.History.KeepAll]:
        return f"[bold magenta]{policy.__class__.__name__}[/]"
    if isinstance(policy, Policy.Reliability.Reliable):
        return Pretty(
            Policy.Reliability.Reliable(
                max_blocking_time=fmtime(policy.max_blocking_time)
            )
        )
    if isinstance(policy, Policy.Lifespan):
        return Pretty(Policy.Lifespan(lifespan=fmtime(policy.lifespan)))
    if isinstance(policy, Policy.Deadline):
        return Pretty(Policy.Deadline(deadline=fmtime(policy.deadline)))
    if isinstance(policy, Policy.LatencyBudget):
        return Pretty(Policy.LatencyBudget(budget=fmtime(policy.budget)))
    if policy.__scope__ == "Liveliness":
        return Pretty(policy.__class__(lease_duration=fmtime(policy.lease_duration)))
    if isinstance(policy, Policy.TimeBasedFilter):
        return Pretty(Policy.TimeBasedFilter(filter_time=fmtime(policy.filter_time)))
    if isinstance(policy, Policy.ReaderDataLifecycle):
        return Pretty(
            Policy.ReaderDataLifecycle(
                autopurge_nowriter_samples_delay=fmtime(
                    policy.autopurge_nowriter_samples_delay
                ),
                autopurge_disposed_samples_delay=fmtime(
                    policy.autopurge_disposed_samples_delay
                ),
            )
        )
    if isinstance(policy, Policy.Property):
        return Pretty(Property(key=policy.key, value=policy.value))
    if isinstance(policy, Policy.BinaryProperty):
        return Pretty(BinaryProperty(key=policy.key, value=policy.value))
    return Pretty(policy)
