"""
 * Copyright(c) 2021 to 2022 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

class EntityQosMapper():
    topic = {
        "Policy.Deadline",
        "Policy.DestinationOrder",
        "Policy.Durability",
        "Policy.DurabilityService",
        "Policy.History",
        "Policy.IgnoreLocal",
        "Policy.LatencyBudget",
        "Policy.Lifespan",
        "Policy.Liveliness",
        "Policy.Ownership",
        "Policy.Reliability",
        "Policy.ResourceLimits",
        "Policy.Topicdata",
        "Policy.TransportPriority"
    }

    pubsub = {
        "Policy.Groupdata",
        "Policy.IgnoreLocal",
        "Policy.Partition",
        "Policy.PresentationAccessScope"
    }

    writer = {
        "Policy.Deadline",
        "Policy.DestinationOrder",
        "Policy.Durability",
        "Policy.DurabilityService",
        "Policy.History",
        "Policy.IgnoreLocal",
        "Policy.LatencyBudget",
        "Policy.Lifespan",
        "Policy.Liveliness",
        "Policy.Ownership",
        "Policy.OwnershipStrength",
        "Policy.Reliability",
        "Policy.ResourceLimits",
        "Policy.TransportPriority",
        "Policy.Userdata",
        "Policy.WriterDataLifecycle"
    }

    reader = {
        "Policy.Deadline",
        "Policy.DestinationOrder",
        "Policy.Durability",
        "Policy.History",
        "Policy.IgnoreLocal",
        "Policy.LatencyBudget",
        "Policy.Liveliness",
        "Policy.Ownership",
        "Policy.ReaderDataLifecycle",
        "Policy.Reliability",
        "Policy.ResourceLimits",
        "Policy.TimeBasedFilter",
        "Policy.Userdata"
    }
