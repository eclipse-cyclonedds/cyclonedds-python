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

from cyclonedds.core import Listener, Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.util import duration

from vehicles import Vehicle


# This is the subscriber in the Vehicle Demo. It publishes a randomly moving
# vehicle updated every 0.1-1.0 seconds randomly. The 'Vehicle' class was
# generated from the vehicle.idl file with `idlc -l py vehicle.idl`

class MyListener(Listener):
    def on_liveliness_changed(self, reader, status):
        print(">> Liveliness event")


listener = MyListener()
qos = Qos(
    Policy.Reliability.BestEffort,
    Policy.Deadline(duration(microseconds=10)),
    Policy.Durability.TransientLocal,
    Policy.History.KeepLast(10)
)

domain_participant = DomainParticipant()
topic = Topic(domain_participant, 'Vehicle', Vehicle, qos=qos)
subscriber = Subscriber(domain_participant)
reader = DataReader(domain_participant, topic, listener=listener)


for sample in reader.take_iter(timeout=duration(seconds=10)):
    print(sample)
