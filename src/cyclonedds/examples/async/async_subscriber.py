"""
 * Copyright(c) 2021 ADLINK Technology Limited and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""
import asyncio

from cyclonedds.core import Listener, WaitSet, ReadCondition, ViewState, SampleState, InstanceState, Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.util import duration

from vehicles import Vehicle


class MyListener(Listener):
    def on_liveliness_changed(self, reader, status):
        print(">> Liveliness event")


listener = MyListener()
qos = Qos(
    Policy.Reliability.BestEffort,
    Policy.Deadline(duration(microseconds=10)),
    Policy.Durability.Transient,
    Policy.History.KeepLast(10)
)

domain_participant = DomainParticipant(0)
topic = Topic(domain_participant, 'Vehicle', Vehicle, qos=qos)
subscriber = Subscriber(domain_participant)
reader = DataReader(domain_participant, topic, listener=listener)


async def task1(reader):
    async for sample in reader.take_aiter(timeout=duration(seconds=2)):
        print(sample)

async def task2():
    while True:
        print("Alive!")
        await asyncio.sleep(1.0)

async def collect(reader):
    t1 = asyncio.ensure_future(task1(reader))
    t2 = asyncio.ensure_future(task2())
    done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()

asyncio.run(collect(reader))