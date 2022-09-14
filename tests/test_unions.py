from cyclonedds.idl import IdlUnion, types


class A(IdlUnion, discriminator=types.uint8):
    f1: types.case[1, types.uint8]
    f2: types.default[types.uint16]


def test_union_not_equal():
    # Even though these both map to the default case
    # The very "thoughtful" XTypes API maps these to type kinds without case
    # Which is very nice...
    assert A(discriminator=3, value=1) != A(discriminator=2, value=1)

