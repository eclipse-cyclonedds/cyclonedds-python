#!/usr/bin/env python3

import sys
import json
import argparse

from cyclonedds.domain import DomainParticipant
from cyclonedds.builtin import (BuiltinDataReader, BuiltinTopicDcpsParticipant,
                                BuiltinTopicDcpsSubscription,  BuiltinTopicDcpsPublication)
from cyclonedds.util import duration


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, help="define the domain participant id", default=0)
    parser.add_argument("--filename", type=str, help="write to file")
    parser.add_argument("--json", action="store_true", help="print output in JSON format")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-a", action="store_true", help="for all topics")
    group.add_argument("-t", "--topics", choices=["dcpsparticipant", "dcpssubscription", "dcpspublication"])
    args = parser.parse_args()
    return args


def manage_dcps_object(dp, topic_type, topic):
    dr = BuiltinDataReader(dp, topic)
    samples = dr.take_iter(timeout=duration(milliseconds=10))

    for sample in samples:
        if topic_type == 'PARTICIPANT':
            sample = {
                topic_type: [{
                    "key": str(sample.key)
                }]
            }
        else:
            sample = {
                topic_type: [{
                    "key": str(sample.key),
                    "participant_key": str(sample.participant_key),
                    "topic_name": sample.topic_name,
                    "qos": sample.qos.asdict()
                }]
            }
        return sample


def print_object(fp, obj, print_json):
    if print_json:
        json.dump(obj, fp, indent=4)
    else:
        fp.write(str(obj))


def main():
    args = create_parser()
    dp = DomainParticipant(args.id)
    obj = []

    if args.topics:
        if args.topics == "dcpsparticipant":
            type = "PARTICIPANT"
            topic = BuiltinTopicDcpsParticipant
        elif args.topics == "dcpssubscription":
            type = "SUBSCRIPTION"
            topic = BuiltinTopicDcpsSubscription
        else:
            type = "PUBLICATION"
            topic = BuiltinTopicDcpsPublication
        obj.append(manage_dcps_object(dp, type, topic))

    if args.a is True:
        type = ["PARTICIPANT", "SUBSCRIPTION", "PUBLICATION"]
        topic = [BuiltinTopicDcpsParticipant, BuiltinTopicDcpsSubscription, BuiltinTopicDcpsPublication]
        for i in range(len(type)):
            obj.append(manage_dcps_object(dp, type[i], topic[i]))

    if not args.filename:
        print_object(sys.stdout, obj, args.json)
    else:
        with open(args.filename, mode="w") as fp:
            try:
                print_object(fp, obj, args.json)
                fp.close()
                return 0
            except Exception:
                return 1


if __name__ == '__main__':
    sys.exit(main())
