# -*- coding: utf-8 -*-
import os
import pytest
import pytestqt
from PyQt5.QtWidgets import QAbstractButton
from PyQt5.QtCore import Qt

from config import TEST_DATA_DIR, temporarily_skipping
from vslearn.gui.main_window import WMainWindow
from vslearn.enums import DataFileType


@pytest.fixture
def main_window(qtbot):
    with WMainWindow() as widget:
        widget.show()
        qtbot.add_widget(widget)
        yield widget, qtbot


class TestMainWindow(object):
    def test_run_app(self, main_window):
        widget, qtbot = main_window

    def test_load_image_no_bb(self, main_window):
        """
        Load images from folder, no bounding boxes loaded or drawn.
        """
        widget, qtbot = main_window

    def test_load_images(self, main_window):
        """
        Load images.
        """
        widget, qtbot = main_window
        folder = os.path.join(TEST_DATA_DIR, 'images')
        print('Test -- loading images from {}'.format(os.path.abspath(folder)))
        widget.files_selected.emit(os.path.abspath(folder), DataFileType.JPG)
        # scroll through images
        widget.scrollbar.valueChanged.emit(1)

    def test_load_bounding_boxes(self, main_window):
        """
        """
        widget, qtbot = main_window
        image_folder = os.path.join(TEST_DATA_DIR, 'images')
        print('Test -- loading images from {}'.format(
            os.path.abspath(image_folder)))
        widget.files_selected.emit(os.path.abspath(image_folder),
                                   DataFileType.JPG)
        # load XML data
        xml_folder = os.path.join(TEST_DATA_DIR, 'labelImg_xml_files')
        widget.files_selected.emit(os.path.abspath(xml_folder),
                                   DataFileType.XML)

    def test_mark_false_positive(self):
        pass

    def test_mark_false_negative(self):
        pass

    def test_mark_true_positive(self):
        pass

    def test_mark_true_negative(self):
        pass


"""
This test can't pass in the WMainWindow because by default the accept/reject
buttons are not enabled. Only after the user has selected an image can
he/she/it mark an annocation as correct or incorrect.
"""


@temporarily_skipping
class TestAcceptRejectEnterButtons(object):
    def test_buttons_added(self, main_window):
        def button_instantiated(_window, _name, _checkable=True):
            assert hasattr(_window, _name)
            button = getattr(_window, _name)
            assert isinstance(button, QAbstractButton)
            assert button.isCheckable() is _checkable

        window, qtbot = main_window
        button_instantiated(window, 'button_accept')
        button_instantiated(window, 'button_reject')
        button_instantiated(window, 'button_enter', False)

    def test_buttons_exclusive(self, main_window):
        def button_type_checker(*buttons):
            """
            Checks whether all buttons are in the list of buttons emitted by
            the signal
            """
            return lambda li: all([b in li for b in buttons])

        window, qtbot = main_window

        qtbot.mouseClick(window.button_reject, Qt.LeftButton)
        assert window.button_reject.isChecked()
        assert not window.button_accept.isChecked()

        with qtbot.waitpyqtSignal(
                window.accept_reject_button_group.check_state_changed,
                timeout=50,
                check_params_cb=button_type_checker(window.button_accept)) as blocker:
            qtbot.mouseClick(window.button_accept, Qt.LeftButton)
            assert window.button_accept.isChecked()
            assert window.button_enter.isEnabled()

        with qtbot.waitpyqtSignal(
                window.accept_reject_button_group.check_state_changed,
                timeout=50,
                check_params_cb=button_type_checker(window.button_reject)) as blocker:
            qtbot.mouseClick(window.button_reject, Qt.LeftButton)
            assert window.button_reject.isChecked()

        # uncheck the reject button
        with qtbot.waitpyqtSignal(
                window.accept_reject_button_group.check_state_changed,
                timeout=50,
                check_params_cb=lambda button_list: len(button_list) == 0) as blocker:
            qtbot.mouseClick(window.button_reject, Qt.LeftButton)
            assert not window.button_reject.isChecked()
            assert not window.button_enter.isEnabled()
