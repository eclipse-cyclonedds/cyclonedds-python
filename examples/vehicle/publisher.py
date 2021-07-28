import time
import random

from cyclonedds.core import Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.topic import Topic
from cyclonedds.util import duration

from vehicles import Vehicle

qos = Qos(
    Policy.Reliability.BestEffort,
    Policy.Deadline(duration(microseconds=10)),
    Policy.Durability.Transient,
    Policy.History.KeepLast(10)
)

domain_participant = DomainParticipant(0)
topic = Topic(domain_participant, 'Vehicle', Vehicle, qos=qos)
publisher = Publisher(domain_participant)
writer = DataWriter(publisher, topic)


cart = Vehicle(name="Dallara IL-15", x=200, y=200)


while True:
    cart.x += random.choice([-1, 0, 1])
    cart.y += random.choice([-1, 0, 1])
    writer.write(cart)
    print(">> Wrote vehicle")
    time.sleep(random.random() * 0.9 + 0.1)
    
