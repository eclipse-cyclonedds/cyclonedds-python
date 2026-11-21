import asyncio
import pytest


MESSAGE_TEXT = "Hello, World!"


@pytest.fixture
def announcements_library():
    '''
    Generates the Announcements library from the test_idlc.idl file.
    '''
    import os
    import shutil
    import subprocess
    assert 'CYCLONEDDS_HOME' in os.environ, 'CYCLONEDDS_HOME is not set'
    idlc_path = os.path.join(os.environ['CYCLONEDDS_HOME'], 'bin', 'idlc')
    subprocess.run([idlc_path, '-l', 'py', 'test_idlc.idl'])
    yield
    shutil.rmtree('Announcements')


@pytest.mark.asyncio
async def test_communication(announcements_library):
    '''
    Creates a publisher and a subscriber and checks if the subscriber receives
    the message sent by the publisher.
    '''
    tasks = [
        _subscriber(),
        _publisher(MESSAGE_TEXT),
    ]
    results = await asyncio.gather(*tasks)
    assert results[0] == MESSAGE_TEXT


async def _publisher(message_text, timeout=2):
    '''
    Sends a given message text to the subscriber.
    '''
    from cyclonedds.domain import DomainParticipant
    from cyclonedds.topic import Topic
    from cyclonedds.pub import DataWriter
    from Announcements import Message

    participant = DomainParticipant(0)
    topic = Topic(participant, "Announcements", Message)
    writer = DataWriter(participant, topic)
    message = Message(text=message_text)
    writer.write(message)
    await asyncio.sleep(timeout)


async def _subscriber(timeout=2):
    '''
    Receives a message. Returns None if it times out.
    '''
    from cyclonedds.domain import DomainParticipant
    from cyclonedds.topic import Topic
    from cyclonedds.sub import DataReader
    from Announcements import Message
    from cyclonedds.util import duration

    participant = DomainParticipant(0)
    topic = Topic(participant, "Announcements", Message)
    reader = DataReader(participant, topic)
    async for update in reader.read_aiter(timeout=duration(seconds=timeout)):
        return update.text
    return None
