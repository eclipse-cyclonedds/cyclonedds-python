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

from dataclasses import fields
from typing import Sequence, List, Union

from cyclonedds.qos import BasePolicy, Qos, Policy
from cyclonedds.util import duration


dds_infinity = 9223372036854775807


class QosParser:

    # Policy mapping (lowercase) name -> class or instance
    policies = {k.lower(): v for k, v in Qos._policy_mapper.items()}

    def __init__(self, data: List[str]) -> None:
        self.pos = 0      # parser position in data
        self.data = data  # data to parse

    @staticmethod
    def prepare_arguments(arguments: List[str]):
        # Allow user to use : and , to freely visually split arguments
        # Parsable arguments are all split along all whitespace
        ret = []
        for arg in arguments:
            arg = arg.replace(":", "").replace(",", "")
            ret += arg.split()
        return ret

    @staticmethod
    def parse(arguments: List[str]) -> Qos:
        # Main method: qos = QosParser.parse(arguments)
        arguments = QosParser.prepare_arguments(arguments)
        parser = QosParser(arguments)
        return Qos(*parser.parse_list_of_policies())

    def parse_list_of_policies(self) -> List[BasePolicy]:
        # Build policies until end of string is reached
        ret = []
        while not self.at_end():
            ret.append(self.parse_policy())

        return ret

    def parse_policy(self):
        # Construct a policy. First argument should always resolve to a policy name
        name = self.string().lower()
        name = name if name.startswith("policy.") else f"policy.{name}"

        if name not in self.policies:
            raise Exception(f"No such policy {name}")

        policy = self.policies[name]
        argument_types = [f.type for f in fields(policy)]

        if argument_types:
            # There is a non-zero amount of typed arguments to parse
            arguments = [self.parse_argument_of_type(_type) for _type in argument_types]
            return policy(*arguments)
        else:
            # There are no arguments to parse so the policy is already complete
            return policy

    def parse_argument_of_type(self, _type):
        # Typed dispatch to simple parsers

        if _type == str:
            return self.string()
        elif _type == int:
            return self.integer()
        elif _type == float:
            return self.floating()
        elif _type == bool:
            return self.boolean()
        elif _type == Sequence[str]:
            return self.string_list()
        elif _type == bytes:
            return self.binary_data()
        elif _type == Union['Policy.History.KeepAll', 'Policy.History.KeepLast']:
            # This is a special case for DurabilityService which contains a History Policy
            ret = self.parse_policy()
            if ret.__scope__ != "History":
                raise Exception("DurabilityService takes a History policy")
            return ret

        raise Exception(f"Cannot parse type {_type}, this is a bug, please report it.")

    def pop(self) -> str:
        # Safely return the next item in the parse list and increment the position
        if self.pos >= len(self.data):
            raise Exception("Unexpected end of arguments")

        ret = self.data[self.pos]
        self.pos += 1
        return ret

    def peek(self) -> str:
        # Safely peek the next item in the parse list
        if self.pos >= len(self.data):
            raise Exception("Unexpected end of arguments")

        return self.data[self.pos]

    def at_end(self) -> bool:
        # Are we done parsing?
        return self.pos >= len(self.data)

    def string(self):
        # Strings are always valid, just return the next item
        return self.pop()

    def integer(self):
        # Integers can represent: a duration or an amount
        data = self.pop().lower()

        if '=' in data:
            # Allow writing durations like "seconds=10;minutes=12"
            duration_expression = {k: float(v) for k, v in dict(value.split("=") for value in data.split(';')).items()}
            data = duration(**duration_expression)
        elif data in ["infinity", "inf"]:
            data = dds_infinity
        else:
            data = int(data)

        return data

    def floating(self):
        # Floating points are never durations so don't parse it as that.
        return float(self.pop())

    def boolean(self):
        # true or false, support some other ways of saying that
        data = self.pop().lower()

        if data in ["true", "1", "on", "yes"]:
            return True
        elif data in ["false", "0", "off", "no"]:
            return False

        raise Exception(f"Invalid boolean {data}")

    def string_list(self):
        # String lists are precarious, since it is unclear when they end.
        # We will stop when we recognize another Policy or there is nothing left to parse

        ret = []
        while not self.at_end():
            name = self.peek().lower()
            name = name if name.startswith("policy.") else f"policy.{name}"

            if name in self.policies:
                break

            ret.append(self.string())

        return ret

    def binary_data(self):
        # Support Userdata, Groupdata or Topicdata as base64 encoded string.
        data = self.string()
        return data.encode()
