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

from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.topic import Topic

from pycdr import cdr


@cdr
class HelloWorld:
    data: str


dp = DomainParticipant()
tp = Topic(dp, "Hello", HelloWorld)

pub = Publisher(dp)
dw = DataWriter(pub, tp)

sub = Subscriber(dp)
dr = DataReader(sub, tp)


dw.write(HelloWorld(data='Hello, World!'))
sample = dr.read()[0]
print(sample.data)