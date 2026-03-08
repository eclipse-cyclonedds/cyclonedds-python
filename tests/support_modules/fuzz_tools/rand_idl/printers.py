from . import containers as cn
from ..utility.stream import Stream


def print_type(stream: Stream, rtype: cn.RType):
    if rtype.discriminator == cn.RTypeDiscriminator.Simple:
        stream << rtype.name
    elif rtype.discriminator == cn.RTypeDiscriminator.String:
        stream << "string"
    elif rtype.discriminator == cn.RTypeDiscriminator.BoundedString:
        stream << "string<" << rtype.bound << "> "
    elif rtype.discriminator == cn.RTypeDiscriminator.Sequence:
        stream << "sequence<"
        print_type(stream, rtype.inner)
        stream << "> "
    elif rtype.discriminator == cn.RTypeDiscriminator.BoundedSequence:
        stream << "sequence<"
        print_type(stream, rtype.inner)
        stream << ", " << rtype.bound << "> "
    elif rtype.discriminator in [cn.RTypeDiscriminator.Enumerator, cn.RTypeDiscriminator.Nested]:
        stream << rtype.reference.name


def print_field(stream: Stream, rfield: cn.RField):
    for annotation in rfield.annotations:
        stream << "@" << annotation << stream.endl
    print_type(stream, rfield.type)
    stream << " " << rfield.name
    if rfield.array_bound:
        for bound in rfield.array_bound:
            stream << "[" << bound << "]"

    stream << ";"
    if rfield.seq_depth > 0:
        stream << " /* seq_depth=" << rfield.seq_depth << " */"
    stream << stream.endl


def print_struct(stream: Stream, rstruct: cn.RStruct):
    if rstruct.extensibility == cn.RExtensibility.Final:
        stream << "@final" << stream.endl
    elif rstruct.extensibility == cn.RExtensibility.Appendable:
        stream << "@appendable" << stream.endl
    elif rstruct.extensibility == cn.RExtensibility.Mutable:
        stream << "@mutable" << stream.endl

    for annotation in rstruct.annotations:
        stream << "@" << annotation << stream.endl

    stream << "struct " << rstruct.name << " {" << stream.endl << stream.indent
    for field in rstruct.fields:
        print_field(stream, field)
    stream << stream.dedent << "};" << stream.endl << stream.endl


def print_case(stream: Stream, rcase: cn.RCase):
    for label in rcase.labels:
        stream << "case " << label << ":" << stream.endl
    stream << stream.indent
    print_field(stream, rcase.field)
    stream << stream.dedent


def print_union(stream: Stream, runion: cn.RUnion):
    if runion.extensibility == cn.RExtensibility.Final:
        stream << "@final" << stream.endl
    elif runion.extensibility == cn.RExtensibility.Appendable:
        stream << "@appendable" << stream.endl

    stream << "union " << runion.name << " switch("
    if runion.discriminator_is_key:
        stream << "@key "
    print_type(stream, runion.discriminator)
    stream << ") {" << stream.endl << stream.indent

    for case in runion.cases:
        print_case(stream, case)

    if runion.default:
        stream << "default:" << stream.endl << stream.indent
        print_field(stream, runion.default)
        stream << stream.dedent

    stream << stream.dedent << "};" << stream.endl << stream.endl


def print_enum(stream: Stream, renum: cn.REnumerator):
    #if renum.bit_bound:
    #    stream << "@bit_bound(" << renum.bit_bound << ")" << stream.endl

    stream << "enum " << renum.name << " {" << stream.endl << stream.indent

    for annotation in renum.fields[0].annotations:
        stream << "@" << annotation << stream.endl
    if renum.fields[0].value:
        stream << "@value(" << renum.fields[0].value << ") "
    stream << renum.fields[0].name

    for field in renum.fields[1:]:
        stream << "," << stream.endl
        for annotation in field.annotations:
            stream << "@" << annotation << stream.endl
        if field.value:
            stream << "@value(" << field.value << ") "
        stream << field.name

    stream << stream.endl << stream.dedent
    stream << "};" << stream.endl << stream.endl


def print_bitmask(stream: Stream, rbitmask: cn.RBitmask):
    #if rbitmask.bit_bound:
    #    stream << "@bit_bound(" << rbitmask.bit_bound << ")" << stream.endl

    stream << "bitmask " << rbitmask.name << " {" << stream.endl << stream.indent

    if rbitmask.fields[0].position:
        stream << "@position(" << rbitmask.fields[0].position << ") "
    stream << rbitmask.fields[0].name

    for field in rbitmask.fields[1:]:
        stream << "," << stream.endl
        if field.position:
            stream << "@position(" << field.position << ") "
        stream << field.name

    stream << stream.endl << stream.dedent
    stream << "};" << stream.endl << stream.endl


def print_typedef(stream: Stream, rtypedef: cn.RTypedef):
    stream << "typedef "
    print_type(stream, rtypedef.rtype)
    stream << " " << rtypedef.name
    if rtypedef.array_bound is not None:
        for bound in rtypedef.array_bound:
            stream << "[" << bound << "]"
    stream << ";" << stream.endl << stream.endl


def print_entity(stream: Stream, rentity: cn.REntity):
    if isinstance(rentity, cn.RStruct):
        print_struct(stream, rentity)
        return
    elif isinstance(rentity, cn.RUnion):
        print_union(stream, rentity)
        return
    elif isinstance(rentity, cn.REnumerator):
        print_enum(stream, rentity)
        return
    elif isinstance(rentity, cn.RBitmask):
        print_bitmask(stream, rentity)
        return
    elif isinstance(rentity, cn.RTypedef):
        print_typedef(stream, rentity)
        return
    raise Exception(f"{rentity} is not an entity I can print")
