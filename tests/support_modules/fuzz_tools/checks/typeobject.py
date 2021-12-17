import traceback

from ..rand_idl.context_containers import FullContext
from ..utility.stream import Stream
from ..utility.comparison import type_info_equivalence, type_map_equivalence

from cyclonedds.idl._typesupport.DDS.XTypes import TypeInformation, TypeMapping


def check_type_object_equivalence(log: Stream, ctx: FullContext, typename: str) -> bool:
    datatype = ctx.get_datatype(typename)

    try:
        py_typeinfo = datatype.__idl__.get_type_info()
    except Exception as e:
        log.write_exception("PY TypeInfo", e)
        return False

    try:
        py_typemap = datatype.__idl__.get_type_mapping()
    except Exception as e:
        log.write_exception("PY TypeMap", e)
        return False

    c_data = ctx.c_app.description(typename)

    if not c_data:
        log << "[PY TypeMap]" << log.endl << log.indent << py_typemap << log.dedent << log.endl
        log << "[PY TypeInfo]" << log.endl << log.indent << py_typeinfo << log.dedent << log.endl
        log << "-!- C FAIL -!-" << log.endl << log.indent << \
               ctx.c_app.last_error << log.dedent << log.endl
        return False

    decode_successful = True
    try:
        c_typeinfo = TypeInformation.deserialize(data=c_data[0], has_header=False)
    except Exception as e:
        log.write_exception("Decode TypeInformation", e)
        log << log.indent << c_data[0] << log.dedent
        decode_successful = False

    try:
        c_typemap = TypeMapping.deserialize(data=c_data[1], has_header=False)
    except Exception as e:
        log.write_exception("Decode TypeMap", e)
        log << log.indent << c_data[1] << log.dedent
        decode_successful = False

    if decode_successful:
        match, info = type_info_equivalence(py_typeinfo, c_typeinfo)
        if not match:
            log << "[PY TypeInfo]" << log.endl << log.indent << py_typeinfo << log.dedent << log.endl
            log << "[C TypeInfo]" << log.endl << log.indent << c_typeinfo << log.dedent << log.endl
            log << "Error: C TypeInfo not equal: " << info << log.endl
            decode_successful = False

        match, info = type_map_equivalence(py_typemap, c_typemap)
        if not match:
            log << "[C TypeMap]" << log.endl << log.indent << c_typemap << log.dedent << log.endl
            log << "[PY TypeMap]" << log.endl << log.indent << py_typemap << log.dedent << log.endl
            log << "Error: C TypeMap not equal: " << info << log.endl
            decode_successful = False

    return decode_successful


