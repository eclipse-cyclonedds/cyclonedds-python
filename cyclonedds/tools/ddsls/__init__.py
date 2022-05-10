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

import sys
import json
import datetime
import argparse

from cyclonedds.domain import DomainParticipant
from cyclonedds.builtin import (BuiltinDataReader, BuiltinTopicDcpsParticipant,
                                BuiltinTopicDcpsSubscription, BuiltinTopicDcpsPublication)
from cyclonedds.util import duration
from cyclonedds.core import WaitSet, ReadCondition, ViewState, InstanceState, SampleState


class TopicManager:
    def __init__(self, reader, topic_type, args):
        self.reader = reader
        self.topic_type = topic_type
        self.console_print = not args.filename
        self.enable_json = args.json
        self.enable_view = args.verbose
        self.dp_key = reader.participant.guid
        self.tracked_entities = {}
        self.tracked_disposed_entities = {}
        self.qoses = {}
        self.strings = ""
        self.read_cond = ReadCondition(reader, ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        self.disposed_cond = ReadCondition(reader, ViewState.Any | InstanceState.NotAliveDisposed | SampleState.Any)

    # Read and print samples
    def poll(self):
        new_samples = []
        newly_disposed_samples = []

        while True:
            samples = self.reader.take(N=100, condition=self.read_cond)

            if not samples:
                break

            for sample in samples:
                if (
                    (self.topic_type == "PARTICIPANT" and sample.key != self.dp_key)
                    or (self.topic_type != "PARTICIPANT" and sample.participant_key != self.dp_key)
                ):
                    self.track_sample(sample)
                    if self.check_qos_changes(sample):
                        new_samples.append(sample)

        while True:
            disposed_samples = self.reader.take(N=100, condition=self.disposed_cond)

            if not disposed_samples:
                break

            for disposed_sample in disposed_samples:
                newly_disposed_samples.append(self.tracked_entities.get(str(disposed_sample.key), disposed_sample))
                self.untrack_sample(disposed_sample)

        if self.console_print and (new_samples or newly_disposed_samples):
            self.to_console(new_samples, newly_disposed_samples)

    # Add new samples to dict
    def track_sample(self, sample):
        self.tracked_entities[str(sample.key)] = sample

    # Collect disposed sample to a new dict and delete it from the original dict
    def untrack_sample(self, sample):
        if str(sample.key) in self.tracked_entities:
            self.tracked_disposed_entities[str(sample.key)] = self.tracked_entities[str(sample.key)]
            del self.tracked_entities[str(sample.key)]

    # Track qos changes
    def check_qos_changes(self, sample):
        key = sample.key
        if self.qoses.get(key, 0) == 0:
            self.qoses[key] = sample.qos
        elif self.qoses[key] != sample.qos:
            print(f"""\n\033[1mQos changed on topic '{sample.topic_name}' {self.topic_type.lower()}:\033[0m
                  \r key = {sample.key}""")
            for i in self.qoses[key]:
                if self.qoses[key][i] != sample.qos[i]:
                    print(f"\033[1m {str(self.qoses[key][i])} -> {str(sample.qos[i])}\033[0m")
            self.qoses[key] = sample.qos

            if not self.enable_view:  # If not verbose, don't print the qos changed sample data
                sample = None
        return sample

    # Wait for new / disposed samples
    def add_to_waitset(self, waitset):
        waitset.attach(self.read_cond)
        waitset.attach(self.disposed_cond)

    # Format sample value for console printing in JSON
    def format_value(self, sample):
        if self.topic_type == "PARTICIPANT":
            return {
                "key": str(sample.key),
            }
        else:
            return {
                "key": str(sample.key),
                "participant_key": str(sample.participant_key),
                "topic_name": str(sample.topic_name),
                "type_name": str(sample.type_name),
                "qos": sample.qos.asdict()
            }

    # Format sample for writing to file in JSON
    def as_dict(self):
        return {
            "New": {k: self.format_value(v) for k, v in self.tracked_entities.items()},
            "Disposed": {k: self.format_value(v) for k, v in self.tracked_disposed_entities.items()}
        }

    # Print to console in JSON or non-JSON format
    def to_console(self, new_samples, newly_disposed_samples):
        if self.enable_json:
            if new_samples:
                JsonWriter.write({
                    "type": self.topic_type,
                    "event": "new",
                    "value": [self.format_value(sample) for sample in new_samples]
                })
            if newly_disposed_samples:
                JsonWriter.write({
                    "type": self.topic_type,
                    "event": "disposed",
                    "value": [self.format_value(sample) for sample in newly_disposed_samples]
                })
        else:
            if new_samples:
                print(f"\n-- New {self.topic_type} --")
                for sample in new_samples:
                    print("\n".join(f" {item}: {sample.__dict__[item]}" for item in sample.__dict__
                          if item != "sample_info") + "\n")
            if newly_disposed_samples:
                print(f"\n-- Disposed {self.topic_type} --")
                for sample in newly_disposed_samples:
                    print("\n".join(f" {item}: {sample.__dict__[item]}" for item in sample.__dict__
                          if item != "sample_info") + "\n")


# Check the topic(s)
def parse_args(args):
    if args.topic:
        if args.topic == "dcpsparticipant":
            topic = [["PARTICIPANT", BuiltinTopicDcpsParticipant]]
        elif args.topic == "dcpssubscription":
            topic = [["SUBSCRIPTION", BuiltinTopicDcpsSubscription]]
        else:
            topic = [["PUBLICATION", BuiltinTopicDcpsPublication]]

    if args.all is True:
        topic = [["PARTICIPANT", BuiltinTopicDcpsParticipant],
                 ["SUBSCRIPTION", BuiltinTopicDcpsSubscription],
                 ["PUBLICATION", BuiltinTopicDcpsPublication]]
    return topic


def create_parser(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, help="Define the domain participant id", default=0)
    parser.add_argument("-f", "--filename", type=str, help="Write results to file in JSON format")
    parser.add_argument("-j", "--json", action="store_true", help="Print output in JSON format")
    parser.add_argument("-w", "--watch", action="store_true", help="Watch for data reader & writer & qoses changes")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="View the sample when Qos changes")
    parser.add_argument("-r", "--runtime", type=float, help="Limit the runtime of the tool, in seconds.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-a", "--all", action="store_true", help="for all topics")
    group.add_argument("-t", "--topic", choices=["dcpsparticipant", "dcpssubscription", "dcpspublication"],
                       help="for one specific topic")

    args = parser.parse_args(args)
    return args


# Format samples in JSON
class JsonWriter:
    first = True

    @classmethod
    def write(cls, data):
        if not cls.first:
            print(",")
        cls.first = False
        json.dump(data, sys.stdout, indent=4)

    @classmethod
    def reset(cls):
        cls.first = True


def main(sys_args):
    JsonWriter.reset()
    managers = []
    args = create_parser(sys_args)
    dp = DomainParticipant(args.id)
    topics = parse_args(args)
    waitset = WaitSet(dp)

    for topic_type, topic in topics:
        # Create TopicManager for each topic
        managers.append(TopicManager(BuiltinDataReader(dp, topic), topic_type, args))
        managers[-1].add_to_waitset(waitset)

    if not args.filename and args.json:
        print("[")

    # Watchmode
    if args.watch:
        try:
            time_start = datetime.datetime.now()
            v = True
            while v:
                for manager in managers:
                    waitset.wait(duration(milliseconds=20))
                    manager.poll()
                if args.runtime:
                    v = datetime.datetime.now() < time_start + datetime.timedelta(seconds=args.runtime)
        except KeyboardInterrupt:
            pass
    # Non-watchmode
    else:
        time_start = datetime.datetime.now()
        runtime = args.runtime or 1
        while datetime.datetime.now() < time_start + datetime.timedelta(seconds=runtime):
            for manager in managers:
                manager.poll()

    if not args.filename and args.json:
        print("]")

    # Write to file
    if args.filename:
        try:
            with open(args.filename, 'w') as f:
                data = {manager.topic_type: manager.as_dict() for manager in managers}
                json.dump(data, f, indent=4)
                print(f"\nResults have been written to file {args.filename}\n")
        except OSError:
            raise Exception(f"Could not open file {args.filename}")
    return 0


def command():
    main(sys.argv[1:])
