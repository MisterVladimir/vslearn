# -*- coding: utf-8 -*-
import pytest

from pytestqt import qt_compat


# copied from pytest-qt package
# functions as a positive control for tests actually running
def test_basics(qtbot):
    """
    Basic test that works more like a sanity check to ensure we are setting up
    a QApplication properly and are able to display a simple event_recorder.
    """
    assert qt_compat.qt_api.QApplication.instance() is not None
    widget = qt_compat.qt_api.QWidget()
    qtbot.addWidget(widget)
    widget.setWindowTitle("W1")
    widget.show()

    assert widget.isVisible()
    assert widget.windowTitle() == "W1"
