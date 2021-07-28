from cyclonedds.domain import DomainParticipant
from cyclonedds.builtin import BuiltinDataReader, BuiltinTopicDcpsParticipant
from cyclonedds.util import duration


dp = DomainParticipant()
dr = BuiltinDataReader(dp, BuiltinTopicDcpsParticipant)

for sample in dr.take_iter(timeout=duration(milliseconds=10)):
    print(sample)
