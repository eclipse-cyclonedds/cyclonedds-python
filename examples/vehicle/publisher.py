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

import time
import random

from cyclonedds.core import Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.topic import Topic
from cyclonedds.util import duration

from vehicles import Vehicle


# This is the publisher in the Vehicle Demo. It publishes a randomly moving
# vehicle updated every 0.1-1.0 seconds randomly. The 'Vehicle' class was
# generated from the vehicle.idl file with `idlc -l py vehicle.idl`


qos = Qos(
    Policy.Reliability.BestEffort,
    Policy.Deadline(duration(microseconds=10)),
    Policy.Durability.Transient,
    Policy.History.KeepLast(10)
)

domain_participant = DomainParticipant(0)
topic = Topic(domain_participant, 'Vehicle', Vehicle, qos=qos)
publisher = Publisher(domain_participant)
writer = DataWriter(publisher, topic)


vehicle = Vehicle(name="Dallara IL-15", x=200, y=200)


while True:
    vehicle.x += random.choice([-1, 0, 1])
    vehicle.y += random.choice([-1, 0, 1])
    writer.write(vehicle)
    print(">> Wrote vehicle")
    time.sleep(random.random() * 0.9 + 0.1)
