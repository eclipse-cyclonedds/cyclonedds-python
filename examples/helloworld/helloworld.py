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

from dataclasses import dataclass

from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.topic import Topic

from cyclonedds.idl import IdlStruct


# Define a HelloWorld datatype with one member, data, with as type 'string'
# In IDL this would be defined as "struct HelloWorld { string data; };"
@dataclass
class HelloWorld(IdlStruct):
    data: str


# Create a DomainParticipant, your entrypoint to DDS
# The default domain id is 0.
dp = DomainParticipant()

# Create a Topic with topic name "Hello" and as datatype "HelloWorld" structs.
tp = Topic(dp, "Hello", HelloWorld)

# Create a DataWriter that can send structs on the "Hello" topic
dw = DataWriter(dp, tp)

# Create a DataReader that can receive structs on the "Hello" topic
dr = DataReader(dp, tp)

# Create a HelloWorld sample and write it to the network
sample = HelloWorld(data='Hello, World!')
dw.write(sample)

# Read samples from the network and print the data in the first one
# This should print "Hello, World!"
sample = dr.read()[0]
print(sample.data)
