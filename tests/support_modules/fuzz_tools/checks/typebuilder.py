import traceback

from ..rand_idl.context_containers import FullContext
from ..utility.stream import Stream

def check_sertype_from_typeobj(log: Stream, ctx: FullContext, typename: str) -> bool:
    c_res = ctx.c_app.typebuilder(typename)
    if not c_res[0]:
        log << "typebuilder failed: " << c_res[1] << log.endl
    return c_res[0]
