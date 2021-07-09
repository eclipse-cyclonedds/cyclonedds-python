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
