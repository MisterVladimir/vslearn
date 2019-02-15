# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QMessageBox, QWidget


class _WMessageBoxBase(QMessageBox):
    wicon: int = QMessageBox.NoIcon
    wtitle: str = ''
    wbuttons: int = QMessageBox.NoButton
    default_button: int = QMessageBox.NoButton

    def __init__(self):
        super().__init__()
        self.setIcon(self.wicon)
        self.setText(self.wtitle)
        self.setStandardButtons(self.wbuttons)
        self.setDefaultButton(QMessageBox.NoButton)

    def get_informative_text(self) -> str:
        return self.informativeText()

    def set_informative_text(self, text: str) -> None:
        if text:
            self.setInformativeText(text)
            self.setDefaultButton(self.default_button)


class WErrorMessageBox(_WMessageBoxBase):
    """
    For informing users that the underlying code has failed. The traceback is
    displayed in the "Detailed Text", which can be read by clicking the "See
    Details..." button. (See Qt5 documentation).
    """
    wicon: int = QMessageBox.Critical
    wtitle: str = 'AN ERROR HAS OCCURED'
    wbuttons: int = QMessageBox.Ok
    default_button: int = QMessageBox.Ok

    def get_traceback(self) -> str:
        return self.detailedText()

    def set_traceback(self, text: str) -> None:
        if text:
            self.setDetailedText(text)
            self.setDefaultButton(self.default_button)


class WWarningMessageBox(_WMessageBoxBase):
    wicon: int = QMessageBox.Warning
    wtitle: str = 'WARNING'
    wbuttons: int = QMessageBox.Yes | QMessageBox.No
    default_button: int = QMessageBox.No
