import warnings
from dataclasses import dataclass

from .datastruct import datatypes, Integer, String, IntArray, StrArray, IntSequence, StrSequence
from .check_entity_qos import warning_msg

from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.topic import Topic
from cyclonedds.core import Listener, DDSException, ReadCondition, ViewState, InstanceState, SampleState


warnings.formatwarning = warning_msg


class IncompatibleQosWarning(UserWarning):
    pass


class QosListener(Listener):
    def on_requested_incompatible_qos(self, reader, status):
        warnings.warn("The Qos requested for subscription is incompatible with the Qos offered by publication." +
                      "PubSub may not be available.", IncompatibleQosWarning)


@dataclass
class TypeEntities:
    reader: DataReader
    writer: DataWriter


class TopicManager():
    def __init__(self, args, dp, eqos, waitset):
        self.dp = dp
        self.topic_name = args.topic
        self.seq = -1  # Sequence number counter
        self.eqos = eqos  # Entity qos
        self.entities = {}  # Store writers and readers
        self.file = args.filename  # Write to file or not
        self.track_samples = {}  # Track read samples if needs to write to file
        try:
            self.listener = QosListener()
            self.pub = Publisher(dp, qos=self.eqos.publisher_qos)
            self.sub = Subscriber(dp, qos=self.eqos.subscriber_qos, listener=self.listener)
            for type in datatypes:
                self.entities[type] = self.create_entities(type)
        except DDSException:
            raise Exception("The arguments inputted are considered invalid for cyclonedds.")

        self.read_cond = ReadCondition(self.entities[Integer].reader,
                                       ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        waitset.attach(self.read_cond)

    def write(self, text):
        self.seq += 1
        # Write integer
        if type(text) is int:
            self.entities[Integer].writer.write(Integer(self.seq, text))
        elif type(text) is list:
            for i in text:
                if not isinstance(i, type(text[0])):  # Check if elements in the list are the same type
                    raise Exception("TypeError: Element type inconsistent, " +
                                    "input list should be a list of integer or a list of string.")

            # Write array or sequence of integer
            if text == [] or isinstance(text[0], int):
                if len(text) == IntArray.size():
                    self.entities[IntArray].writer.write(IntArray(self.seq, text))
                else:
                    self.entities[IntSequence].writer.write(IntSequence(self.seq, text))
            # Write array or sequence of string
            else:
                if len(text) == StrArray.size():
                    self.entities[StrArray].writer.write(StrArray(self.seq, text))
                else:
                    self.entities[StrSequence].writer.write(StrSequence(self.seq, text))
        # Write string
        else:
            self.entities[String].writer.write(String(self.seq, text))

    def read(self):
        for type, entity in self.entities.items():
            for sample in entity.reader.take(N=100):
                print(f"Subscribed: {sample}")

                # Track sample to write to file
                if self.file:
                    self.track_samples["sequence " + str(sample.seq)] = {
                        "type": type.postfix(),
                        "keyval": sample.keyval
                        }

    # Create topic, datawriter and datareader
    def create_entities(self, type):
        topic = Topic(self.dp, self.topic_name + type.postfix(), type, qos=self.eqos.topic_qos)
        writer = DataWriter(self.pub, topic, qos=self.eqos.datawriter_qos)
        reader = DataReader(self.sub, topic, qos=self.eqos.datareader_qos)
        return TypeEntities(writer=writer, reader=reader)
