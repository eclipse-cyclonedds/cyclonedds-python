import warnings

from .datastruct import Integer, String, IntArray, StrArray, IntSequence, StrSequence
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


class TopicManager():
    def __init__(self, args, dp, eqos, waitset):
        self.dp = dp
        self.topic_name = args.topic
        self.seq = -1
        self.eqos = eqos
        self.readers = []
        self.file = args.filename
        self.track_samples = {}
        try:
            self.listener = QosListener()
            self.pub = Publisher(dp, qos=self.eqos.publisher_qos)
            self.sub = Subscriber(dp, qos=self.eqos.subscriber_qos)
            self.int_writer = self.create_entities("int", Integer)
            self.str_writer = self.create_entities("str", String)
            self.int_array_writer = self.create_entities("int_array", IntArray)
            self.str_array_writer = self.create_entities("str_array", StrArray)
            self.int_seq_writer = self.create_entities("int_seq", IntSequence)
            self.str_seq_writer = self.create_entities("str_seq", StrSequence)
        except DDSException:
            raise Exception("The arguments inputted are considered invalid for cyclonedds.")

        self.read_cond = ReadCondition(self.readers[0], ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        waitset.attach(self.read_cond)

    def write(self, input):
        self.seq += 1
        # Write integer
        if type(input) is int:
            self.int_writer.write(Integer(self.seq, input))
        elif type(input) is list:
            for i in input:
                if not isinstance(i, type(input[0])):  # Check if elements in the list are the same type
                    raise Exception("TypeError: Element type inconsistent, " +
                                    "input list should be a list of integer or a list of string.")

            # Write array or sequence of integer
            if isinstance(input[0], int):
                if len(input) == IntArray.size():
                    self.int_array_writer.write(IntArray(self.seq, input))
                else:
                    self.int_seq_writer.write(IntSequence(self.seq, input))
            # Write array or sequence of string
            else:
                if len(input) == StrArray.size():
                    self.str_array_writer.write(StrArray(self.seq, input))
                else:
                    self.str_seq_writer.write(StrSequence(self.seq, input))
        # Write string
        else:
            self.str_writer.write(String(self.seq, input))

    def read(self):
        for reader in self.readers:
            for sample in reader.take(N=100):
                print(f"Subscribed: {sample}")

                # track sample to write to file
                if self.file:
                    self.track_samples["sequence " + str(sample.seq)] = {
                        "type": sample.__class__.__name__,
                        "keyval": sample.keyval
                        }

    # Create topic, datawriter and a list of datareaders
    def create_entities(self, name, datastruct):
        topic = Topic(self.dp, self.topic_name + name, datastruct, qos=self.eqos.topic_qos)
        writer = DataWriter(self.pub, topic, qos=self.eqos.datawriter_qos)
        if name == "int":
            self.readers.append(DataReader(self.sub, topic, qos=self.eqos.datareader_qos, listener=self.listener))
        else:
            self.readers.append(DataReader(self.sub, topic, qos=self.eqos.datareader_qos))
        return writer

    def as_dict(self):
        return self.track_samples
