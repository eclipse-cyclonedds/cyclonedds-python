import pytest
import random
import test_rec_classes as trc


def test_recursive_types():
    v1 = trc.Node(
        left=trc.OptNode(node=trc.Node(
            left=trc.OptNode(nothing=None),
            right=trc.OptNode(node=trc.Node(
                left=trc.OptNode(nothing=None),
                right=trc.OptNode(nothing=None),
                value=12
            )),
            value = 6
        )),
        right=trc.OptNode(node=trc.Node(
            left=trc.OptNode(nothing=None),
            right=trc.OptNode(node=trc.Node(
                left=trc.OptNode(nothing=None),
                right=trc.OptNode(nothing=None),
                value=-12
            )),
            value = -6
        )),
        value=0
    )
    assert v1 == trc.Node.deserialize(v1.serialize())


def test_optional_recursive():
    tree = trc.CNode(value=0)

    l = list(range(-100, 100))
    random.seed(0)
    random.shuffle(l)
    for i in l:
        tree.add(i)

    print(tree)
    assert tree == trc.CNode.deserialize(tree.serialize())

