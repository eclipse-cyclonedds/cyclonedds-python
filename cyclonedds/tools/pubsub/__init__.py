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

import os
import sys
import datetime
import typing
import argparse
import json
from threading import Thread, Event

from .check_entity_qos import QosPerEntity
from .parse_qos import QosParser
from .topic_manager import TopicManager

from cyclonedds.core import WaitSet
from cyclonedds.domain import DomainParticipant
from cyclonedds.util import duration
from cyclonedds.qos import Qos
from dataclasses import fields


def create_parser(args):
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-T", "--topic", type=str, help="The name of the topic to publish/subscribe to")
    group.add_argument("-D", "--dynamic", type=str, help="Dynamically publish/subscribe to a topic")
    parser.add_argument("-f", "--filename", type=str, help="Write results to file in JSON format")
    parser.add_argument("-eqos", "--entityqos", choices=["all", "topic", "publisher", "subscriber",
                        "datawriter", "datareader"], default=None, help="""Select the entites to set the qos.
Choose between all entities, topic, publisher, subscriber, datawriter and datareader. (default: all).
Inapplicable qos will be ignored.""")
    parser.add_argument("-q", "--qos", nargs="+",
                        help="Set QoS for entities, check '--qoshelp' for available QoS and usage\n")
    parser.add_argument("-r", "--runtime", type=float, help="Limit the runtime of the tool, in seconds.")
    group.add_argument("--qoshelp", action="store_true", help=qos_help_msg)

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)

    args = parser.parse_args(args)

    if args.qoshelp:
        print(qos_help_msg)
        sys.exit(0)
    if args.entityqos and not args.qos:  # Error when selecting entity qos without defining qos policy
        raise Exception("The following argument is required: -q/--qos")
    return args


def qos_help():
    name_map = {
        int: "integer",
        str: "string",
        float: "float",
        bool: "boolean",
        bytes: "bytes"
    }
    qos_help = []
    for name, policy in Qos._policy_mapper.items():
        policy_name = name.replace("Policy.", "")
        _fields = fields(policy)
        if len(_fields) == 0:
            qos_help.append("--qos " f"{policy_name}\n")
        else:
            out = []
            for f in _fields:
                if f.type in name_map:
                    out.append(f"[{f.name}<{name_map[f.type]}>]")
                else:
                    if f.type.__origin__ is typing.Union:
                        out.append("[History.KeepAll / History.KeepLast [depth<integer>]]")
                    elif f.type is typing.Sequence[str]:
                        out.append(f"[{f.name}<Sequence[str]>]")
                    else:
                        out.append(f"[{f.name}<{f.type}>]")
            qos_help.append("--qos " f"{policy_name} {', '.join(out)}\n")
    return qos_help


qos_help_msg = str(f"""e.g.:
    --qos Durability.TransientLocal
    --qos History.KeepLast 10
    --qos ReaderDataLifecycle 10, 20
    --qos Partition [a, b, 123]
    --qos PresentationAccessScope.Instance False, True
    --qos DurabilityService 1000, History.KeepLast 10, 100, 10, 10
    --qos Durability.TransientLocal History.KeepLast 10\n
Available QoS and usage are:\n {' '.join(map(str, qos_help()))}\n""")


class Worker:
    def __init__(self, work_fn):
        self.txt = None
        self.quit_e = Event()
        self.read_e = Event()
        self.work = Thread(target=work_fn, args=(self,))
        self.work.start()

    def is_stopped(self):
        return self.quit_e.is_set()

    def get_input(self):
        if self.txt is not None:
            txt = self.txt
            self.txt = None
            self.read_e.set()
            return txt
        return None

    def put_input(self, txt):
        self.read_e.clear()
        self.txt = txt
        self.read_e.wait()

    def stop(self):
        self.quit_e.set()
        self.work.join()


def make_work_function(manager, waitset, args):
    def work_fn(worker):
        time_start = datetime.datetime.now()
        v = True
        while v and not worker.is_stopped():
            txt = worker.get_input()
            if txt:
                try:  # Integer or list
                    text = eval(txt)
                    manager.write(text)
                except NameError:  # String
                    manager.write(txt.rstrip("\n"))
                except SyntaxError:
                    raise Exception("Input unrecognizable, please check your input.")
            manager.read()
            waitset.wait(duration(microseconds=20))
            if args.runtime:
                v = datetime.datetime.now() < time_start + datetime.timedelta(seconds=args.runtime)

        # Write to file
        if args.filename:
            try:
                with open(args.filename, 'w') as f:
                    json.dump(manager.track_samples, f, indent=4)
                    print(f"\nResults have been written to file {args.filename}\n")
            except OSError:
                raise Exception(f"Could not open file {args.filename}")

        if not v:
            os._exit(0)
    return work_fn


def main(sys_args):
    args = create_parser(sys_args)
    eqos = QosPerEntity(args.entityqos)
    if args.qos:
        qos = QosParser.parse(args.qos)
        eqos.entity_qos(qos, args.entityqos)

    dp = DomainParticipant(0)
    waitset = WaitSet(dp)
    manager = TopicManager(args, dp, eqos, waitset)
    if args.topic or args.dynamic:
        try:
            worker = Worker(make_work_function(manager, waitset, args))
            while True:
                txt = input("")
                worker.put_input(txt)
        except (KeyboardInterrupt, IOError, ValueError):
            pass
        except EOFError:
            # stdin closed, if runtime is set wait for that to expire, else exit
            if args.runtime:
                worker.work.join()
        finally:
            worker.stop()

    return 0


def command():
    main(sys.argv[1:])
