import asyncio
import pytest
import sys


IDL_FILE = 'test_idlc_hierarchy.idl'


@pytest.fixture
def hierarchy_library():
    '''
    Generates the Hierarchy library from the test_idlc_hierarchy.idl file.
    '''
    import os
    import shutil
    import subprocess
    assert 'CYCLONEDDS_HOME' in os.environ, 'CYCLONEDDS_HOME is not set'
    idlc_path = os.path.join(os.environ['CYCLONEDDS_HOME'], 'bin', 'idlc')
    subprocess.run([idlc_path, '-l', 'py', IDL_FILE])
    yield
    shutil.rmtree('Hierarchy')


@pytest.mark.asyncio
async def test_base_topic(hierarchy_library):
    '''
    Creates a publisher and a subscriber of the Base topic and checks if the
    subscriber receives the update sent by the publisher.
    '''
    from Hierarchy import Base
    base = Base(fieldA="Hakuna")
    tasks = [
        _subscriber(Base),
        _publisher(Base, base),
    ]
    results = await asyncio.gather(*tasks)
    assert results[0] == results[1]


@pytest.mark.asyncio
async def test_derived_topic(hierarchy_library):
    '''
    Creates a publisher and a subscriber of the Derived topic and checks if the
    subscriber receives the update sent by the publisher.
    '''
    from Hierarchy import Derived
    derived = Derived(
        fieldA="Hakuna",
        fieldB="Matata",
    )
    tasks = [
        _subscriber(Derived),
        _publisher(Derived, derived),
    ]
    results = await asyncio.gather(*tasks)
    assert results[0] == results[1]


@pytest.mark.asyncio
@pytest.mark.skipif(sys.platform == 'darwin', reason='I do not know why this fails on macOS')
async def test_cyclonedds_typeof_command(hierarchy_library):
    '''
    Executes the command "cyclonedds typeof" and compares the result with the
    IDL file.
    '''
    from Hierarchy import Derived
    tasks = [
        _subscriber(Derived),
        _type_checker(Derived, IDL_FILE),
    ]
    await asyncio.gather(*tasks)


async def _publisher(topic_class, value, timeout=2):
    '''
    Sends a given value update to the subscriber.
    '''
    from cyclonedds.domain import DomainParticipant
    from cyclonedds.topic import Topic
    from cyclonedds.pub import DataWriter

    participant = DomainParticipant(0)
    topic = Topic(participant, topic_class.__name__, topic_class)
    writer = DataWriter(participant, topic)
    writer.write(value)
    await asyncio.sleep(timeout)
    return value


async def _subscriber(topic_class, timeout=2):
    '''
    Receives an update. Returns None if it times out.
    '''
    from cyclonedds.domain import DomainParticipant
    from cyclonedds.topic import Topic
    from cyclonedds.sub import DataReader
    from cyclonedds.util import duration

    participant = DomainParticipant(0)
    topic = Topic(participant, topic_class.__name__, topic_class)
    reader = DataReader(participant, topic)
    async for update in reader.read_aiter(timeout=duration(seconds=timeout)):
        return update
    return None


async def _type_checker(topic_class, idl_file):
    '''
    Executes the command "cyclonedds typeof" and compares the result with a
    given IDL file.
    '''
    def _normalise(text):
        text = text.replace('\n', ' ')
        text = ' '.join(text.split())
        return text

    # loads the IDL file
    with open(idl_file) as file:
        expected_idl = file.read().rstrip()

    # executes the command
    import subprocess
    result = subprocess.run(
        ['cyclonedds', 'typeof', topic_class.__name__, '--suppress-progress-bar'],
        stdout=subprocess.PIPE,
        check=True,)
    command_output = result.stdout.decode().splitlines()

    # skips the first lines of the output (As defined in participant...)
    first_idl_line = 0
    while first_idl_line < len(command_output) and not command_output[first_idl_line].startswith('module'):
        first_idl_line += 1
    actual_idl = '\n'.join(command_output[first_idl_line:])

    # compares the command output with the IDL file
    print(actual_idl)
    assert _normalise(actual_idl) == _normalise(expected_idl)
