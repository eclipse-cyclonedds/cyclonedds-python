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

from cyclonedds.domain import DomainParticipant
from cyclonedds.builtin import BuiltinDataReader, BuiltinTopicDcpsParticipant
from cyclonedds.util import duration


# Create a DomainParticipant in the default domain
dp = DomainParticipant()

# Create a datareader that can read from the builtin participant topic
dr = BuiltinDataReader(dp, BuiltinTopicDcpsParticipant)


# Print samples received on the participant topic
# If we don't receive a sample for more than 10 milliseconds exit
for sample in dr.take_iter(timeout=duration(milliseconds=10)):
    print(sample)
