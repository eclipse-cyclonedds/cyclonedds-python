import pytest

from support_modules.testtopics import Message


def test_regression_write_read_take(common_setup):
    """
        This popped up in early testing, if the refcounting in the C backend is not done right
        the count can become zero between read and take and python frees it.
    """

    common_setup.dw.write(Message(message="Hi!"))
    assert common_setup.dr.read()[0] == Message(message="Hi!")
    assert common_setup.dr.take()[0] == Message(message="Hi!")
