"""
 * Copyright(c) 2021 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

from time import time_ns as _time_ns
from .core import Entity
from .internal import dds_infinity


def isgoodentity(v: object) -> bool:
    """Helper function that checks to see if an object is a valid :class:`Entity<cyclonedds.core.Entity>` returned from DDS.
    This function will never raise an exception.

    Parameters
    ----------
    v : object, optional
        The object to check

    Returns
    -------
    bool
        Whether this entity is a valid :class:`Entity<cyclonedds.core.Entity>`.
    """
    return \
        v is not None and \
        isinstance(v, Entity) and \
        hasattr(v, "_ref") and \
        type(v._ref) == int and \
        v._ref > 0


def duration(*, weeks: float = 0, days: float = 0, hours: float = 0, minutes: float = 0, seconds: float = 0,
             milliseconds: float = 0, microseconds: float = 0, nanoseconds: int = 0, infinite: bool = False) -> int:
    """Durations are always expressed in nanoseconds in DDS (dds_duration_t). This helper function lets
    you write time in a human readable format.

    Examples
    --------
    >>> duration(weeks=2, days=10, minutes=10)

    Parameters
    ----------
        weeks: float, default=0
        days: float, default=0
        hours: float, default=0
        minutes: float, default=0
        seconds: float, default=0
        milliseconds: float, default=0
        microseconds: float, default=0
        nanoseconds: int, default=0
        infinite: bool, default=False

    Returns
    -------
    int
        Duration expressed in nanoseconds.
    """

    if infinite:
        return dds_infinity

    days += weeks * 7
    hours += days * 24
    minutes += hours * 60
    seconds += minutes * 60
    milliseconds += seconds * 1000
    microseconds += milliseconds * 1000
    nanoseconds += microseconds * 1000
    return int(nanoseconds)


class timestamp:
    @staticmethod
    def now():
        """
        In DDS timestamps are typically expressed as nanoseconds since the Unix Epoch (dds_time_t). This helper function
        returns the current time in nanoseconds.

        Returns
        -------
        int
            Number of nanoseconds since the Unix Epoch.
        """
        return _time_ns()
