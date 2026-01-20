"""
 * Copyright(c) 2021 ZettaScale Technology and others
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
from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.topic import Topic
from cyclonedds.sub import Subscriber, DataReader

IDLC_PY_COMMAND = "/usr/local/lib/cyclonedds/bin/idlc -l py -Wno-implicit-extensibility test.idl"

"""
 *
 * Test_001
 *
"""

def test_datatypes_keywords_001():
    idl = """
        module module_test_001 {
            struct struct_test {
                char var;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)

    from module_test_001 import struct_test

    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_001', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)

    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(var='z')

    writer.write(msg)
    print(">> Wrote struct_test msg")

    for sample in reader.read():
        print(sample)
        assert sample.var == 'z'

    os.system("rm test.idl")
    os.system("rm -rf module_test_001")
    
"""
 *
 * Test_002
 *
"""

def test_datatypes_keywords_002():
    idl = """
        module module_test_002 {
            struct struct_test_A {
                char var;
            };
            struct struct_test_B : struct_test_A {
                char var_2;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_002 import struct_test_A, struct_test_B
   
    domain_participant = DomainParticipant(0)
    
    topic_1 = Topic(domain_participant, 'module_test_struct_test_A_002', struct_test_A)
    topic_2 = Topic(domain_participant, 'module_test_struct_test_B_002', struct_test_B)

    publisher = Publisher(domain_participant)
    writer_1 = DataWriter(publisher, topic_1)
    writer_2 = DataWriter(publisher, topic_2)

    subscriber = Subscriber(domain_participant)
    reader_1 = DataReader(domain_participant, topic_1)
    reader_2 = DataReader(domain_participant, topic_2)

    msg_1 = struct_test_A(var='z')
    msg_2 = struct_test_B(var_2='y', var = 'p')

    writer_1.write(msg_1)
    print(">> Wrote struct_test_A msg_1")
    writer_2.write(msg_2)
    print(">> Wrote struct_test_B msg_2")
    
    for sample in reader_1.read():
        print(sample)
        assert sample.var == 'z'
        
    for sample in reader_2.read():
        print(sample)
        assert sample.var == 'p'
        assert sample.var_2 == 'y'
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_002")

"""
 *
 * Test_003
 *
"""
    
def test_datatypes_keywords_003():
    idl = """
        module module_test_A {
            module module_test_B {
                struct struct_test {
                    char var;
                };
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)
    
    from module_test_A.module_test_B import struct_test

    domain_participant = DomainParticipant(0)
    
    topic = Topic(domain_participant, 'module_test_A_module_test_B_struct_test_003', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)

    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(var='z')
     
    writer.write(msg)
    print(">> Wrote struct_test msg")

    for sample in reader.read():
        print(sample)
        assert sample.var == 'z'

    os.system("rm test.idl")
    os.system("rm -rf module_test_A")        

"""
 *
 * Test_004
 *
"""

def test_datatypes_keywords_004():
    idl = """
        module module_test_004 {
            struct struct_test {
                char bool;
                char pass;
                char None;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)

    from module_test_004 import struct_test
   
    domain_participant = DomainParticipant(0)
    
    topic = Topic(domain_participant, 'module_test_struct_test_004', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)

    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)
    
    msg = struct_test(bool='a', _pass='b', _None='c')

    writer.write(msg)
    print(">> Wrote struct_test msg")

    for sample in reader.read():
        print(sample)
        assert sample.bool == 'a'
        assert sample._pass == 'b'
        assert sample._None == 'c'
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_004")        

"""
 *
 * Test_005
 *
"""

def test_datatypes_keywords_005():
    idl = """
        module module_test_005 {
            struct struct_test {
                string str;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)
    
    from module_test_005 import struct_test
   
    domain_participant = DomainParticipant(0)
    
    topic = Topic(domain_participant, 'module_test_struct_test_005', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)

    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)
    
    msg = struct_test(str = "Hello world!")
     
    writer.write(msg)
    print(">> Wrote struct_test msg")

    for sample in reader.read():
        print(sample)
        assert sample.str == "Hello world!"

    os.system("rm test.idl")
    os.system("rm -rf module_test_005")        

"""
 *
 * Test_006
 *
"""

def test_datatypes_keywords_006():
    idl = """
        module module_test_006 {
            struct global {
                char var;
                char pass[5];
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)
    
    from module_test_006 import _global
   
    domain_participant = DomainParticipant(0)
    
    topic = Topic(domain_participant, 'module_test_struct_test_006', _global)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)

    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)
    
    msg = _global(var='z',_pass=['a', 'b', 'c', 'd', 'e'])

    writer.write(msg)
    print(">> Wrote struct_test msg")

    for sample in reader.read():
        print(sample)
        assert sample.var == 'z'
        assert sample._pass == ['a', 'b', 'c', 'd', 'e']

    os.system("rm test.idl")
    os.system("rm -rf module_test_006")        
    
"""
 *
 * Test_007_a
 *
"""

def test_datatypes_keywords_007_a():
    idl = """
        module module_test_007_a {
            struct and {
                char var;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)
    
    from module_test_007_a import _and

    domain_participant = DomainParticipant(0)
    
    topic = Topic(domain_participant, 'module_test_struct_test_007_a', _and)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)

    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)
    
    msg = _and(var='z')

    writer.write(msg)
    print(">> Wrote _and msg")
    
    for sample in reader.read():
        print(sample)
        assert sample.var == 'z'

    os.system("rm test.idl")
    os.system("rm -rf module_test_007_a")            

"""
 *
 * Test_007_b
 *
"""

def test_datatypes_keywords_007_b():
    idl = """
        module module_test_007_b {
            struct parent {
                char var;
            };
            struct child : parent {
                char var_2;
            };
        };
        """
    
    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)
   
    from module_test_007_b import parent, child 

    domain_participant = DomainParticipant(0)

    topic_1 = Topic(domain_participant, 'module_test_parent_007_b', parent)
    topic_2 = Topic(domain_participant, 'module_test_child_007_b', child)
   
    publisher = Publisher(domain_participant)
    writer_1 = DataWriter(publisher, topic_1)
    writer_2 = DataWriter(publisher, topic_2)

    subscriber = Subscriber(domain_participant)
    reader_1 = DataReader(domain_participant, topic_1)
    reader_2 = DataReader(domain_participant, topic_2)

    msg_1 = parent(var='z')
    msg_2 = child(var = 'p', var_2='y')
     
    writer_1.write(msg_1)
    print(">> Wrote parent msg_1")
    writer_2.write(msg_2)
    print(">> Wrote child msg_2")
    
    for sample in reader_1.read():
        print(sample)
        assert sample.var == 'z'
        
    for sample in reader_2.read():
        print(sample)
        assert sample.var == 'p'
        assert sample.var_2 == 'y'
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_007_b")    

"""
 *
 * Test_007_c
 *
"""

def test_datatypes_keywords_007_c():
    idl = """
        module module_test_007_c {
            struct and {
                char var;
            };
            struct child : and {
                char var_2;
            };
        };
        """
    
    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)
   
    from module_test_007_c import _and, child

    domain_participant = DomainParticipant(0)

    topic_1 = Topic(domain_participant, 'module_test__and_007_c', _and)
    topic_2 = Topic(domain_participant, 'module_test_child_007_c', child)
   
    publisher = Publisher(domain_participant)
    writer_1 = DataWriter(publisher, topic_1)
    writer_2 = DataWriter(publisher, topic_2)

    subscriber = Subscriber(domain_participant)
    reader_1 = DataReader(domain_participant, topic_1)
    reader_2 = DataReader(domain_participant, topic_2)

    msg_1 = _and(var='z')
    msg_2 = child(var = 'p', var_2='y')

    writer_1.write(msg_1)
    print(">> Wrote _and msg_1")
    writer_2.write(msg_2)
    print(">> Wrote child msg_2")
    
    for sample in reader_1.read():
        print(sample)
        assert sample.var == 'z'

    for sample in reader_2.read():
        print(sample)
        assert sample.var == 'p'
        assert sample.var_2 == 'y'
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_007_c")    

"""
 *
 * Test_007_d
 *
"""

def test_datatypes_keywords_007_d():
    idl = """
        module module_test_007_d {
            struct parent {
                char var;
            };
            struct continue : parent {
                char var_2;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)

    from module_test_007_d import parent, _continue

    domain_participant = DomainParticipant(0)

    topic_1 = Topic(domain_participant, 'module_test_parent_007_d', parent)
    topic_2 = Topic(domain_participant, 'module_test__continue_007_d', _continue)
   
    publisher = Publisher(domain_participant)
    writer_1 = DataWriter(publisher, topic_1)
    writer_2 = DataWriter(publisher, topic_2)

    subscriber = Subscriber(domain_participant)
    reader_1 = DataReader(domain_participant, topic_1)
    reader_2 = DataReader(domain_participant, topic_2)

    msg_1 = parent(var='z')
    msg_2 = _continue(var = 'p', var_2='y')

    writer_1.write(msg_1)
    print(">> Wrote parent msg_1")
    writer_2.write(msg_2)
    print(">> Wrote _continue msg_2")
    
    for sample in reader_1.read():
        print(sample)
        assert sample.var == 'z'
        
    for sample in reader_2.read():
        print(sample)
        assert sample.var == 'p'
        assert sample.var_2 == 'y'
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_007_d")    

"""
 *
 * Test_007_e   
 *
"""

def test_datatypes_keywords_007_e():
    idl = """
        module module_test_007_e {
            struct and {
                char var;
            };
            struct continue : and {
                char var_2;
            };
        };
        """
    
    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)
    
    from module_test_007_e import _and, _continue

    domain_participant = DomainParticipant(0)

    topic_1 = Topic(domain_participant, 'module_test__and_007_e', _and)
    topic_2 = Topic(domain_participant, 'module_test__continue_007_e', _continue)
   
    publisher = Publisher(domain_participant)
    writer_1 = DataWriter(publisher, topic_1)
    writer_2 = DataWriter(publisher, topic_2)

    subscriber = Subscriber(domain_participant)
    reader_1 = DataReader(domain_participant, topic_1)
    reader_2 = DataReader(domain_participant, topic_2)

    msg_1 = _and(var='z')
    msg_2 = _continue(var = 'p', var_2='y')

    writer_1.write(msg_1)
    print(">> Wrote _and msg_1")
    writer_2.write(msg_2)
    print(">> Wrote _continue msg_2")
    
    for sample in reader_1.read():
        print(sample)
        assert sample.var == 'z'

        
    for sample in reader_2.read():
        print(sample)
        assert sample.var == 'p'
        assert sample.var_2 == 'y'
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_007_e")    

"""
 *
 * Test_008_a
 *
"""    
    
def test_datatypes_keywords_008_a():
    idl = """
        module module_test_008_a {
            union union_type switch (int8) {
                    case 1:
                        int16 value_int;
                    case 2:
                        char value_char_array[5];
                    default:
                        string value_string;
            };
            struct struct_test {
                union_type union_field;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)

    from module_test_008_a import struct_test, union_type

    domain_participant = DomainParticipant(0)
  
    topic = Topic(domain_participant, 'module_test_struct_test_008_a', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
   
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg_1 = struct_test(union_field=union_type(discriminator=1, value=10))
    msg_2 = struct_test(union_field=union_type(discriminator=2, value=['a', 'b', 'c', 'd', 'e']))
    msg_3 = struct_test(union_field=union_type(discriminator=3, value="Hello world!"))

    writer.write(msg_1)
    print(">> Wrote struct_test msg_1")
   
    for sample in reader.read():
        print(sample)
        assert sample.union_field.value_int == 10

    writer.write(msg_2)
    print(">> Wrote struct_test msg_2")

    for sample in reader.read():
        print(sample)
        assert sample.union_field.value_char_array == ['a', 'b', 'c', 'd', 'e']

    writer.write(msg_3)
    print(">> Wrote struct_test msg_3")
    
    for sample in reader.read():
        print(sample)
        assert sample.union_field.value_string == "Hello world!"

    os.system("rm test.idl")
    os.system("rm -rf module_test_008_a")

"""
 *
 * Test_008_b
 *
"""

def test_datatypes_keywords_008_b(common_setup):
    idl = """
        module module_test_008_b {
            union assert switch (int8) {
                    case 1:
                        int16 value_int;
                    case 2:
                        char value_char_array[5];
                    default:
                        string value_string;
            };
            struct struct_test {
                assert union_field;
            };
        };
        """
    
    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)

    from module_test_008_b import struct_test, _assert

    domain_participant = DomainParticipant(0)
  
    topic = Topic(domain_participant, 'module_test_struct_test_008_b', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
   
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)
   
    msg_1 = struct_test(union_field=_assert(discriminator=1, value=10))
    msg_2 = struct_test(union_field=_assert(discriminator=2, value=['a', 'b', 'c', 'd', 'e']))
    msg_3 = struct_test(union_field=_assert(discriminator=3, value="Hello world!"))
    
    writer.write(msg_1)
    print(">> Wrote struct_test msg_1")
   
    for sample in reader.read():
        print(sample)
        assert sample.union_field.value_int == 10

    writer.write(msg_2)
    print(">> Wrote struct_test msg_2")
    
    for sample in reader.read():
        print(sample)
        assert sample.union_field.value_char_array == ['a', 'b', 'c', 'd', 'e']

    writer.write(msg_3)
    print(">> Wrote struct_test msg_3")

    for sample in reader.read():
        print(sample)
        assert sample.union_field.value_string == "Hello world!"

    os.system("rm *.idl")
    os.system("rm -rf module_test_008_b")    

"""
 *
 * Test_008_c
 *
"""
    
def test_datatypes_keywords_008_c(common_setup):
    idl = """
        module module_test_008_c {
            union assert switch (int8) {
                    case 1:
                        int16 break;
                    case 2:
                        char class[5];
                    default:
                        string continue;
            };
            struct struct_test {
                assert union_field;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)

    from module_test_008_c import struct_test, _assert

    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_008_c', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
   
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg_1 = struct_test(union_field=_assert(discriminator=1, value=10))
    msg_2 = struct_test(union_field=_assert(discriminator=2, value=['a', 'b', 'c', 'd', 'e']))
    msg_3 = struct_test(union_field=_assert(discriminator=3, value="Hello world!"))

    writer.write(msg_1)
    print(">> Wrote struct_test msg_1")
   
    for sample in reader.read():
        print(sample)
        assert sample.union_field._break == 10

    writer.write(msg_2)
    print(">> Wrote struct_test msg_2")
    
    for sample in reader.read():
        print(sample)
        assert sample.union_field._class == ['a', 'b', 'c', 'd', 'e']

    writer.write(msg_3)
    print(">> Wrote struct_test msg_3")

    for sample in reader.read():
        print(sample)
        assert sample.union_field._continue == "Hello world!"

    os.system("rm *.idl")
    os.system("rm -rf module_test_008_c")    

"""
 *
 * Test_008_d
 *
"""
    
def test_datatypes_keywords_008_d(common_setup):
    idl = """
        module module_test_008_d {
            union assert switch (int8) {
                    case 1:
                        int16 break;
                    case 2:
                        char class[5];
                    default:
                        string continue;
            };
            struct struct_test {
                assert as;
            };
        };
        """
    
    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
    
    os.system(IDLC_PY_COMMAND)

    from module_test_008_d import struct_test, _assert

    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_008_d', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
   
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg_1 = struct_test(_as=_assert(discriminator=1, value=10))
    msg_2 = struct_test(_as=_assert(discriminator=2, value=['a', 'b', 'c', 'd', 'e']))
    msg_3 = struct_test(_as=_assert(discriminator=3, value="Hello world!"))

    writer.write(msg_1)
    print(">> Wrote struct_test msg_1")
   
    for sample in reader.read():
        print(sample)
        assert sample._as._break == 10

    writer.write(msg_2)
    print(">> Wrote struct_test msg_2")
    
    for sample in reader.read():
        print(sample)
        assert sample._as._class == ['a', 'b', 'c', 'd', 'e']

    writer.write(msg_3)
    print(">> Wrote struct_test msg_3")

    for sample in reader.read():
        print(sample)
        assert sample._as._continue == "Hello world!"

    os.system("rm *.idl")
    os.system("rm -rf module_test_008_d")    

"""
 *
 * Test_009_a
 *
"""

def test_datatypes_keywords_009_a():
    idl = """
        module module_test_009_a {
            enum def {
                one,
                two
            };
            struct struct_test {
                def enum_def;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_009_a import struct_test, _def
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_009_a', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(enum_def=_def.two)

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample.enum_def == _def.two
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_009_a")

"""
 *
 * Test_009_b
 *
"""

def test_datatypes_keywords_009_b():
    idl = """
        module module_test_009_b {
            enum def {
                del,
                elif
            };
            struct struct_test {
                def enum_def;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_009_b import struct_test, _def
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_009_b', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(enum_def=_def._elif)

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample.enum_def == _def._elif
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_009_b")

"""
 *
 * Test_009_c
 *
"""

def test_datatypes_keywords_009_c():
    idl = """
        module module_test_009_c {
            enum def {
                del,
                elif
            };
            struct struct_test {
                def else;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_009_c import struct_test, _def
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_009_c', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(_else=_def._elif)

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample._else == _def._elif
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_009_c")

"""
 *
 * Test_010_a
 *
"""

def test_datatypes_keywords_010_a():
    idl = """
        module module_test_010_a {
            bitmask bitmask_type {
                value_1,
                value_2
            };
            struct struct_test {
                bitmask_type bitmask_value;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_010_a import struct_test, bitmask_type
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_010_a', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(bitmask_value=bitmask_type(value_1=True, value_2=False))

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample.bitmask_value.value_1 == True
        assert sample.bitmask_value.value_2 == False
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_010_a")

"""
 *
 * Test_010_b
 *
"""

def test_datatypes_keywords_010_b():
    idl = """
        module module_test_010_b {
            bitmask except {
                value_1,
                value_2
            };
            struct struct_test {
                except bitmask_value;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_010_b import struct_test, _except
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_010_b', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(bitmask_value=_except(value_1=True, value_2=False))

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample.bitmask_value.value_1 == True
        assert sample.bitmask_value.value_2 == False
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_010_b")

"""
 *
 * Test_010_c
 *
"""

def test_datatypes_keywords_010_c():
    idl = """
        module module_test_010_c {
            bitmask except {
                finally,
                for
            };
            struct struct_test {
                except bitmask_value;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_010_c import struct_test, _except
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_010_c', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(bitmask_value=_except(_finally=True, _for=False))

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample.bitmask_value._finally == True
        assert sample.bitmask_value._for == False
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_010_c")

"""
 *
 * Test_010_d
 *
"""

def test_datatypes_keywords_010_d():
    idl = """
        module module_test_010_d {
            bitmask except {
                finally,
                for
            };
            struct struct_test {
                except from;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_010_d import struct_test, _except
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_010_d', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(_from=_except(_finally=True, _for=False))

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample._from._finally == True
        assert sample._from._for == False
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_010_d")

"""
 *
 * Test_011
 *
"""

def test_datatypes_keywords_011():
    idl = """
        module module_test_011 {
            typedef int8 global[8];
            typedef sequence<octet> raise;
            struct struct_test {
                global if;
                raise return;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_011 import struct_test
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_011', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(_if=[1, 2, 3, 4, 5, 6, 7, 8], _return=[10, 20, 30, 40])

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample._if == [1, 2, 3, 4, 5, 6, 7, 8]
        assert sample._return == [10, 20, 30, 40]
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_011")

"""
 *
 * Test_012
 *
"""

def test_datatypes_keywords_012():
    idl = """
        module import {
            struct struct_test {
                char var;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from _import import struct_test
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module__import_struct_test_012', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(var='z')

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample.var == 'z'
           
    os.system("rm test.idl")
    os.system("rm -rf _import")

"""
 *
 * Test_013
 *
"""

def test_datatypes_keywords_013():
    idl = """
        module in {
           module is {
               struct struct_test {
                   char var;
               };
           };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from _in._is import struct_test
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module__in_module__is_struct_test_013', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(var='z')

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample.var == 'z'
           
    os.system("rm test.idl")
    os.system("rm -rf _in")

"""
 *
 * Test_014_a
 *
"""

def test_datatypes_keywords_014_a():
    idl = """
        module module_test_014_a {
            const int8 num_values = 3;
            struct struct_test {
                char var[num_values];
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_014_a import struct_test, num_values
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_014_a', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(var=['a','b','c'])

    writer.write(msg)
    print(">> Wrote struct_test msg with num_values: ", num_values)
        
    for sample in reader.read():
        print(sample)
        assert sample.var == ['a','b','c']
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_014_a")

"""
 *
 * Test_014_b
 *
"""

def test_datatypes_keywords_014_b():
    idl = """
        module module_test_014_b {
            const int8 lambda = 3;
            struct struct_test {
                char var[lambda];
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_014_b import struct_test, _lambda
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_014_b', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(var=['a','b','c'])

    writer.write(msg)
    print(">> Wrote struct_test msg with _lambda: ", _lambda)
        
    for sample in reader.read():
        print(sample)
        assert sample.var == ['a','b','c']
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_014_b")

"""
 *
 * Test_015_a
 *
"""

def test_datatypes_keywords_015_a():
    idl = """
        module module_test_015_a {
            struct struct_test {
                uint16 key;
                char var;
            };
            #pragma keylist struct_test key
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_015_a import struct_test
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_015_a', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(key=1, var='z')

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample.key == 1
        assert sample.var == 'z'
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_015_a")

"""
 *
 * Test_015_b
 *
"""

def test_datatypes_keywords_015_b():
    idl = """
        module module_test_015_b {
            struct struct_test {
                uint16 nonlocal;
                char var;
            };
            #pragma keylist struct_test nonlocal
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_015_b import struct_test
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_015_b', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(_nonlocal=1, var='z')

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample._nonlocal == 1
        assert sample.var == 'z'
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_015_b")

"""
 *
 * Test_015_c
 *
"""

def test_datatypes_keywords_015_c():
    idl = """
        module module_test_015_c {
            struct struct_test {
                @key uint16 key;
                char var;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_015_c import struct_test
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_015_c', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(key=1, var='z')

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample.key == 1
        assert sample.var == 'z'
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_015_c")

"""
 *
 * Test_015_d
 *
"""

def test_datatypes_keywords_015_d():
    idl = """
        module module_test_015_d {
            struct struct_test {
                @key uint8 not;
                @key uint16 or;
                @key uint32 pass;
                @key uint64 try;
                @key int8 while;
                @key int16 with;
                @key int32 yield;
                char var;
            };
        };
        """

    idl_file = open("test.idl", "w")
    idl_file.write(idl)
    idl_file.write("\n")
    idl_file.close()
   
    os.system(IDLC_PY_COMMAND)
   
    from module_test_015_d import struct_test
   
    domain_participant = DomainParticipant(0)

    topic = Topic(domain_participant, 'module_test_struct_test_015_d', struct_test)

    publisher = Publisher(domain_participant)
    writer = DataWriter(publisher, topic)
    
    subscriber = Subscriber(domain_participant)
    reader = DataReader(domain_participant, topic)

    msg = struct_test(_not=1, _or=2, _pass=3, _try=4, _while=-1, _with=-2, _yield=-3, var='z')

    writer.write(msg)
    print(">> Wrote struct_test msg")
        
    for sample in reader.read():
        print(sample)
        assert sample._not == 1
        assert sample._or == 2
        assert sample._pass == 3
        assert sample._try == 4
        assert sample._while == -1
        assert sample._with == -2
        assert sample._yield == -3
        assert sample.var == 'z'
           
    os.system("rm test.idl")
    os.system("rm -rf module_test_015_d")