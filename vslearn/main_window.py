# -*- coding: utf-8 -*-
import datetime
import glob
import os
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image
from qtpy.QtWidgets import (
    QAbstractButton, QButtonGroup, QColorDialog, QFileDialog, QGraphicsView,
    QMainWindow)
from qtpy.QtCore import QObject, Signal, Slot

from . import UI_DIR
from .enums import (
    AnnotationCheckedState, DataFileType, MachineLearningMode, UserType)
from .input_output import WRecordWriter
from .models.scene import WGraphicsItemGroup, WGraphicsScene
from .models.bounding_box import UserID, BoundingBoxParameter
from .registry import (
    AnnotationRegistry, ImagePathRegistry, annotation_registry_from_labelImg,
    default_human_user_id)
from .ui.ui_main_window import Ui_MainWindow
from .warning import WWarningMessageBox, WErrorMessageBox


# TODO clean up the interface with `WButtonGroup` such that no slots need be
# connected directly to signals of `QAbstractButton` objects inside
# `WButtonGroup`. Instead, `WButtonGroup` should just emit
# `check_state_changed` whenever a contained button emits a `toggled` or other
# signal.
class WButtonGroup(QButtonGroup):
    check_state_changed = Signal(list)
    """
    A container for buttons. In WButtonGroup, we can set a minimum and maximum
    number of buttons that can remain in the "checked" and "unchecked" states.
    For example, imagine a WButtonGroup with three buttons, A, B, and C, and
    whose minimum and maximum are 1 and 2, respectively. Upon instantiation, it
    starts with A in the checked state. If button B is pressed, nothing happens
    to A. If button C is then pressed, A is unchecked but B remains checked.

    Parameters
    -------------
    exclusive: Tuple[int, int]
        Minimum and maximum number of buttons that can remain in the "checked"
        state at once.
    """
    def __init__(self, *buttons: QAbstractButton,
                 exclusive: Tuple[int, int] = (0, 1),
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        minimum, maximum = exclusive
        if not maximum >= minimum:
            raise ValueError('Second value must be greater than or equal '
                             'to first value.')
        if minimum == 0 and maximum == 0:
            raise ValueError('At least one item in the ButtonGroup must '
                             'be checkable.')

        self._minimum_checked: int = minimum
        self._maximum_checked: int = maximum
        # keeps track of the order in which the buttons were pressed such that
        # if a new button is pressed, the earliest button to be pressed
        # (at index zero) is released
        self._checked: List[int] = []
        self._setup(buttons, minimum)
        self._signals_setup()

    def _setup(self, buttons: QAbstractButton, minimum: int) -> None:
        super().setExclusive(False)
        for button in buttons:
            button.setCheckable(True)
            super().addButton(button)

        for i, button in zip(range(minimum), self.buttons()):
            # setDown does not emit signals
            button.setChecked(True)
            self._checked.append(button)

    def _signals_setup(self) -> None:
        self.buttonClicked.connect(self._update_buttons)

    def setExclusive(self, exclusive: bool) -> None:
        # override base class method
        # this class has its own implementation of Qt's button exclusivity
        pass

    def addButton(self, button: QAbstractButton) -> None:
        # override base class method to make this group immutable
        pass

    def clear(self) -> None:
        """
        Releases all buttons.
        """
        _check_state_changed: bool = False
        if self._checked:
            _check_state_changed = True
        for button in self.buttons():
            button.setChecked(False)
        self._checked = []
        if _check_state_changed:
            self.check_state_changed.emit([])

    def setEnabled(self, enable: bool) -> None:
        for button in self.buttons():
            button.setEnabled(enable)

    @Slot(QAbstractButton)
    def _update_buttons(self, button: QAbstractButton) -> None:
        """
        Called *after* button has been clicked. See QAbstractButton.clicked().
        """
        _check_state_changed = True

        if button.isChecked():
            # print('CHECKED')
            # print('{} was  pressed'.format(button))
            # print('old _checked: {}'.format(self._checked))
            self._checked.append(button)
            if len(self._checked) > self._maximum_checked:
                button = self._checked.pop(0)
                button.setChecked(False)
                # button.toggled.emit(False)
            # print('new _checked: {}'.format(self._checked))

        elif len(self._checked) < self._minimum_checked:
            # XXX: UNTESTED
            # if the button click caused the button to become unchecked and now
            # too few buttons are in the OFF state, reverse the effect of the
            # button click
            # print('unchecked 1')
            button.setChecked(True)
            # button.toggled.emit(True)
            _check_state_changed = False
        else:
            # print('unchecked 2')
            # print('{} was released'.format(button))
            # print('old _checked: {}'.format(self._checked))
            index = self._checked.index(button)
            button = self._checked.pop(index)
            # print('new _checked: {}'.format(self._checked))

        if _check_state_changed:
            # notifies of changes to the checked state of buttons
            self.check_state_changed.emit(
                [b for b in self.buttons() if b.isChecked()])


class WMainWindow(QMainWindow, Ui_MainWindow):
    """

    """
    # 'selected' means the user has chosen that item/category from
    # an QFileDialog
    files_selected = Signal(str, int)
    image_registry_created = Signal()
    annotation_registry_created = Signal()
    images_about_to_reset = Signal()
    images_were_reset = Signal()
    bounding_boxes_about_to_reset = Signal()
    bounding_boxes_were_reset = Signal()
    scrollbar_value_about_to_change = Signal()

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self._attributes_setup()
        self._setup()
        self._signals_setup()

    def __enter__(self) -> 'WMainWindow':
        return self

    def __exit__(self, typ, value, traceback):
        """
        Placeholder. We might some day need to close image or Tensorflow Record
        files here.
        """
        pass

    def _attributes_setup(self):
        self.image_registry: Optional[ImagePathRegistry] = None
        self.annotation_registry: Optional[AnnotationRegistry] = None

    def _setup(self):
        # model for the QGraphicsView
        self.scene = WGraphicsScene(parent=self)
        self.graphics_view.setScene(self.scene)

        # checkmark and X buttons
        # these buttons mark the image as correctly or incorrectly segmented,
        # respectively. when the latter button is pressed, the user may go into
        # 'editing mode', which allows him/her to modify the bounding boxes.
        self.accept_reject_button_group = WButtonGroup(
            self.button_accept, self.button_reject, exclusive=(0, 1))
        self.accept_reject_button_group.setEnabled(False)

        self._warning_message_box = WWarningMessageBox()
        self._error_message_box = WErrorMessageBox()

    def _signals_setup(self) -> None:
        # File -> Open images...
        self.action_open_images.triggered.connect(
            lambda: self.open_file_dialog(DataFileType.IMAGE))
        # File -> Open bounding boxes... -> from CSV...
        self.action_from_CSV.triggered.connect(
            lambda: self.open_file_dialog(DataFileType.CSV))
        # File -> Open bounding boxes... -> from JSON...
        self.action_from_JSON.triggered.connect(
            lambda: self.open_file_dialog(DataFileType.JSON))
        # File -> Open tensorflow record...
        self.action_from_tfrecord.triggered.connect(
            lambda: self.open_file_dialog(DataFileType.TFRECORD))
        # File -> Open bounding boxes... -> from XML...
        self.action_from_XML.triggered.connect(
            lambda: self.open_file_dialog(DataFileType.XML))

        # a file or folder for loading data from
        self.files_selected[str, int].connect(self.load_files)

        self.image_registry_created.connect(
            self._enable_image_dependent_widgets)
        self.image_registry_created.connect(self.scene.reset_images)
        self.images_were_reset.connect(self._reset_scrollbar)

        self.bounding_boxes_were_reset.connect(self._reset_scrollbar)

        # File -> Export to... -> JSON
        self.action_to_JSON.triggered.connect(
            lambda: self.save(DataFileType.JSON))
        # File -> Export to... -> TFRecord
        self.action_to_tfrecord.triggered.connect(
            lambda: self.save(DataFileType.TFRECORD))

        # zoom buttons signals
        self.button_resize.clicked.connect(self.graphics_view.fit_to_window)
        self.button_zoom_in.clicked.connect(self.graphics_view.zoom_in)
        self.button_zoom_out.clicked.connect(self.graphics_view.zoom_out)

        # accept/reject button signals
        self.accept_reject_button_group.check_state_changed[list].connect(
            self._enable_enter_button)
        self.accept_reject_button_group.check_state_changed[list].connect(
            self._set_edit_mode_from_button_list)
        self.button_enter.clicked.connect(self._enter_button_pressed)

        # add rectangle button
        self.button_add.toggled[bool].connect(self.scene.set_drawing_mode)
        self.button_add.toggled[bool].connect(self._set_drag_mode)
        self.scrollbar.valueChanged.connect(lambda: self.scene.set_drawing_mode(False))
        self.scrollbar.valueChanged.connect(lambda: self._set_drag_mode(False))
        self.scrollbar.valueChanged.connect(lambda: self.button_add.setChecked(False))
        self.button_enter.clicked.connect(lambda: self.button_add.setChecked(False))

        # set bounding box color
        self.action_bounding_box_color.triggered.connect(
            self.set_bounding_box_color)

        # XXX is it worth putting display_image and display_bounding_boxes into
        # one method or is there a case we want to display an image
        # without bounding boxes?
        self.scrollbar.valueChanged[int].connect(self.display_image)
        self.scrollbar.valueChanged[int].connect(self.display_bounding_boxes)
        # self.scrollbar.valueChanged[int].connect(self._data_entry_finished)

        # editing mode finished
        # TODO the accept_reject_button_group should be the widget connected to
        # _set_edit_mode
        self.scrollbar.valueChanged.connect(self.accept_reject_button_group.clear)
        self.scrollbar.valueChanged.connect(lambda: self._set_edit_mode(False))
        self.scrollbar.valueChanged.connect(lambda: self.button_enter.setEnabled(False))
        self.scrollbar.valueChanged[int].connect(self._set_statusbar_message)

    def _enable_image_dependent_widgets(self):
        """
        Widgets that should only be enabled when images have been loaded.
        """
        widgets = (self.action_from_XML,  # self.action_from_CSV,
                   self.action_from_JSON, self.accept_reject_button_group,
                   self.action_from_tfrecord)
        for widget in widgets:
            widget.setEnabled(True)

    @Slot(bool)
    def _set_drag_mode(self, off: bool):
        if off:
            self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        else:
            self.graphics_view.setDragMode(QGraphicsView.RubberBandDrag)

    @Slot(bool)
    def _set_edit_mode(self, edit: bool):
        print('setting edit mode of image {} to {}'.format(self.get_current_image_id(), edit))
        self.scene.set_edit_mode(self.get_current_image_id(), edit)

    @Slot(list)
    def _set_edit_mode_from_button_list(self, buttons: List[QAbstractButton]):
        print('button list check state changed')
        if self.button_reject in buttons:
            print('reject button')
            self._set_edit_mode(True)
        else:
            self._set_edit_mode(False)

    @Slot()
    def _enter_button_pressed(self):
        """
        This method achieves two things. The simplest is advancing the
        scrollbar to the next image. The other is updating the
        annotation_registry with any changes the user made to the bounding
        boxes.
        """
        current_index: int = self.scrollbar.value()
        image_id = self.get_current_image_id()
        self.update_annotation_registry(image_id)
        if self.scrollbar.isEnabled() and \
                not current_index == self.scrollbar.maximum():
            self.scrollbar.setValue(current_index + 1)
            self.scrollbar.valueChanged.emit(current_index + 1)

    @Slot(int)
    def _set_statusbar_message(self, index: int):
        self.statusbar.showMessage(self.get_current_image_id())

    def _open_images(self):
        """
        Open a QFileDiaolog in which the user selects a folder containing the
        images.
        """
        # DontUseNativeDialog might help with OS compatibility??
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Select a folder containing images"), '',
            QFileDialog.DontUseNativeDialog)
        self.image_folder_selected.emit(os.path.abspath(folder))

    @Slot(int)
    def open_file_dialog(self, flag: DataFileType) -> None:
        path = ''
        if DataFileType.IMAGE & flag:
            path: str = QFileDialog.getExistingDirectory(self)
        elif DataFileType.TFRECORD & flag:
            print('getting record')
            paths: Tuple[str] = QFileDialog.getOpenFileName(
                parent=self, caption=self.tr("Open Tensorflow Record File..."),
                # "Images (*.png *.xpm *.jpg)"
                filter=self.tr("TensorflowRecord (*.tfrecord *.record)"))
            # for example if a *.tfrecord file is selected,
            # paths = ([FILENAME].tfrecord, '')
            path, _ = paths
        elif self.image_registry is None:
            raise RuntimeError('Loading bounding boxes should be impossible ' +
                               'if no images have been loaded.')
        elif DataFileType.CSV & flag:
            paths: Tuple[str] = QFileDialog.getOpenFileName(
                self, self.tr("Open CSV File..."),
                filter=self.tr("CSV Files (*.csv)"))
            path, _ = paths
        elif DataFileType.JSON & flag:
            paths: Tuple[str, str] = QFileDialog.getOpenFileName(
                self, self.tr("Open JSON File..."),
                filter=self.tr("JSON Files (*.json)"))
            path, _ = paths
        elif DataFileType.XML & flag:
            path: str = QFileDialog.getExistingDirectory(self)

        print('opened path: {}'.format(path))
        if path:
            self.files_selected.emit(path, flag)

    @Slot(str, int)
    def load_files(self, path: str, flag: int) -> None:
        print('loading files')
        print('flag: {!s:}'.format(flag))
        if DataFileType.IMAGE & flag:
            # creates ImagePathRegistry and empty AnnotationRegistry
            self._load_image_files(path)
        elif DataFileType.TFRECORD & flag:
            # creates ImagePathRegistry and AnnotationRegistry
            self._load_tfrecord(path)
        elif not self.image_registry:
            raise RuntimeError('Images must be loaded before bounding boxes.')
        elif DataFileType.XML & flag:
            # updates existing AnnotationRegistry
            self._load_xml_boxes(path)
        elif DataFileType.CSV & flag:
            # not implemented
            pass
        elif DataFileType.JSON & flag:
            # updates the AnnotationRegistry
            self._load_json_boxes(path)
        else:
            raise ValueError('{!s} not a supported file type.'.format(path))

        if flag & DataFileType.IMAGE:
            self.image_registry_created.emit()
            self.images_about_to_reset.emit()
            self.scene.reset_images()
            for name in self.annotation_registry.image_ids:
                self.scene.create_group(name)
            self.images_were_reset.emit()
        elif flag & DataFileType.BBOX:
            self.annotation_registry_created.emit()
            self.bounding_boxes_about_to_reset.emit()
            for annotation in self.annotation_registry.annotations:
                for box_parameter in annotation.bounding_boxes:
                    box = box_parameter.make_box_graphics_item()
                    self.scene.add_bounding_box(box)
            self.bounding_boxes_were_reset.emit()

    def _load_image_files(self, folder: str):
        self.image_registry = ImagePathRegistry.from_dir(folder)
        self.annotation_registry = \
            AnnotationRegistry.make_empty_registry(self.image_registry)

    def _load_xml_boxes(self, directory: str) -> None:
        filenames = glob.glob(os.path.join(directory, '*.xml'))
        # registry contains the subset of XML files whose ID is in the current
        # image_registry
        registry = annotation_registry_from_labelImg(
            self.image_registry, filenames, self.get_user_id())
        for imgid, annot in zip(registry.image_ids, registry.annotations):
            self.annotation_registry.update_annotation(imgid, annot)

    def _load_json_boxes(self, filename: str) -> None:
        if self.image_registry is not None:
            json_registry = AnnotationRegistry.loads_from_json(filename)
            image_ids = set(self.image_registry.image_ids)
            image_ids.intersection_update(json_registry.image_ids)
            for image_id in image_ids:
                annotation = json_registry.get_annotation(image_id)
                self.annotation_registry.update_annotation(image_id,
                                                           annotation)
        else:
            raise RuntimeError(
                'Cannot add annotations before adding an ImageRegistry.')

    def _load_tfrecord(self, filename: str) -> None:
        """
        Loads bounding box coordinates from Tensorflow Record containing
        inferred (a.k.a. predicted) bounding boxes. Note that, to save disk
        space, such files do not contain image data. Instead, the user must
        load the original jpeg images from which the inferences were generated.
        """
        if self.image_registry is not None:
            current_user: UserID = self.get_user_id()
            current_confidence: float = 0.5
            tf_registry = AnnotationRegistry.from_tfrecord(
                filename, MachineLearningMode.INFERENCE, user=current_user,
                confidence=current_confidence)
            # print(list(tf_registry.image_ids))
            image_ids = set(self.image_registry.image_ids)
            image_ids.intersection_update(tf_registry.image_ids)
            # print('image IDs: {}'.format(image_ids))
            for image_id in image_ids:
                annotation = tf_registry.get_annotation(image_id)
                self.annotation_registry.update_annotation(image_id,
                                                           annotation)
        else:
            raise RuntimeError(
                'Cannot add annotations before adding an ImageRegistry.')

    @Slot(int)
    def save(self, flag: DataFileType):
        try:
            if flag & DataFileType.JSON:
                self._save_as_json()
            elif flag & DataFileType.TFRECORD:
                self._save_as_tfrecord()

        except Exception as e:
            print('\n'.join(self.annotation_registry.annotations))
            self._display_warning(
                'There was an error while saving the file.\n\n{!s:}'.format(e))

    def _save_as_json(self):
        filename = QFileDialog.getSaveFileName(
            self, 'Save as JSON...', filter=self.tr("JSON Files (*.json)"))
        as_string = self.annotation_registry.dumps_to_json(indent=4)
        print('saving as: {}'.format(filename))
        with open(filename[0], 'w') as f:
            f.write(as_string)

    def _save_as_tfrecord(self):
        filename: str = QFileDialog.getSaveFileName(
            self, 'Save as Tensorflow Record...',
            filter=self.tr("Tensorflow Records (*.tfrecord *.record)"))[0]

        maximum: int = len(self.image_registry) - 1
        self.progress_bar.setRange(0, maximum)
        with WRecordWriter(filename) as writer:
            for i, annotation in enumerate(
                    self.annotation_registry.annotations):
                boxes, classes = zip(*[
                    ([box.xmin, box.ymin, box.xmax, box.ymax], box.label)
                    for box in annotation.bounding_boxes
                    if not box.delete and (box.state &
                                           AnnotationCheckedState.CORRECT)
                ])
                # equivalent to:
                # boxes: List[List[int]] = [
                #     [box.xmin, box.ymin, box.xmax, box.ymax]
                #     for box in annotation.bounding_boxes if...]
                # classes: List[str] = [
                #     box.label for box in annotation.bounding_boxes if...]
                image_filename: str = \
                    self.image_registry.get_filename_from_image_id(
                        annotation.image_id)
                example = writer.create_example(boxes, classes, image_filename)
                writer.write(example)
                self.progress_bar.setValue(i)

        self.progress_bar.setValue(0)

    def get_current_image_id(self) -> str:
        if self.image_registry is None:
            raise RuntimeError('No image ID available since no image registry '
                               'has been created.')
        scrollbar_index = self.scrollbar.value()
        return self.image_registry.get_image_id_by_index(scrollbar_index)

    def get_user_id(self) -> UserID:
        name = self.user_id_line_edit.text()
        if name:
            return UserID(name=name,
                          typ=UserType.HUMAN,
                          timestamp=str(datetime.datetime.now()))
        else:
            return default_human_user_id

    @Slot()
    def _reset_scrollbar(self):
        self.scrollbar.setEnabled(True)
        self.scrollbar.setMaximum(len(self.image_registry) - 1)
        self.scrollbar.setValue(0)
        self.scrollbar.valueChanged.emit(self.scrollbar.value())

    def _display_warning(self, message: str):
        self._warning_message_box.set_informative_text(message)
        self._warning_message_box.exec()

    def _display_error(self, message: str, traceback: str = ''):
        self._error_message_box.set_informative_text(message)
        self._error_message_box.set_traceback(traceback)
        self._error_message_box.exec()

    @Slot()
    def set_bounding_box_color(self):
        color = QColorDialog.getColor(parent=self,
                                      options=QColorDialog.ShowAlphaChannel |
                                      QColorDialog.DontUseNativeDialog)
        if color:
            self.scene.set_box_color(color)

    @Slot(list)
    def _enable_enter_button(self, buttons: List[QAbstractButton]):
        """
        Enables the "ENTER" button, which writes the bounding box data to the
        data model.
        """
        self.button_enter.setEnabled(bool(buttons))

    @Slot(int)
    def display_image(self, index: int) -> None:
        """
        Display image corresponding to filename in position 'index' in
        the image registry.
        """
        filename = self.image_registry.get_filename_by_index(index)
        with Image.open(filename) as image_file_handle:
            image_array = np.asarray(image_file_handle)
        self.scene.set_pixmap(image_array, rescale=False)

    @Slot(int)
    def display_bounding_boxes(self, index: int) -> None:
        """
        Shows the bounding boxes in the Scene associated with image_id
        """
        print('displaying bounding boxes at index = {}'.format(index))
        if self.annotation_registry is not None:
            image_id: str = self.image_registry.get_image_id_by_index(index)
            # TODO: hide iterates through all the bounding boxes and executes
            # their setVisible(False) method. to improve performance we can
            # track the state of shown and hidden bounding boxes.
            self.scene.hide()
            self.scene.show(image_id)

    def update_annotation_registry(self, image_id: str):
        """
        Convenience method for updating the AnnotationRegistry's members with
        values from the GraphicsItems.
        """
        print('updating image_id: {}'.format(image_id))
        group: WGraphicsItemGroup = self.scene.groups[image_id]
        updated_bounding_boxes: List[BoundingBoxParameter] = \
            [bbox.parameter for bbox in group]
        for param in updated_bounding_boxes:
            param.set_state(self.get_user_id(), True)
        # self.annotation_registry.bounding_boxes = updated_bounding_boxes
        self.annotation_registry.update_annotation(
            image_id, {'bounding_boxes': updated_bounding_boxes})

        # print('after')
        # print(self.annotation_registry.get_annotation(image_id))
