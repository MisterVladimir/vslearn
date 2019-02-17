# -*- coding: utf-8 -*-
from collections import OrderedDict
import dataclasses
import numpy as np
from qtpy.QtWidgets import (
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem,
    QGraphicsSceneMouseEvent)
from qtpy.QtCore import Property, QPointF, Qt, Signal, Slot
from qtpy.QtGui import QColor, QImage, QPen, QPixmap
from typing import Dict, Optional

from .bounding_box import WBoundingBoxGraphicsItem, BoundingBoxParameter
from ..enums import AnnotationCheckedState


class WGraphicsItemGroup(QGraphicsRectItem):
    def __init__(self, image_id: str,
                 parent: Optional[QGraphicsPixmapItem] = None):
        super().__init__(parent)
        self.image_id: str = image_id
        self._bboxes: Dict[int, WBoundingBoxGraphicsItem] = {}

    def __getitem__(self, key: int):
        return self._bboxes[key]

    def __setitem__(self, key: int, bbox: WBoundingBoxGraphicsItem):
        self._bboxes[key] = bbox

    def __iter__(self):
        for item in self.childItems():
            yield item

    def __len__(self):
        return len(self.childItems())

    def set_edit_mode(self, edit: bool):
        self.setEnabled(edit)
        for child in self.childItems():
            child.set_editable(edit)

    def is_dirty(self) -> bool:
        return any((box.parameter.is_dirty() or
                    box.parameter.state & AnnotationCheckedState.NEW or
                    box.delete
                    for box in self.childItems()))

    def paint(self, *args, **kwargs):
        pass


class WGraphicsScene(QGraphicsScene):
    default_image = np.random.randint(0, 256, (512, 512), dtype=np.uint8)
    pixmap_changed = Signal(int)
    default_bounding_box_pen = QPen(Qt.black)
    default_bounding_box_pen.setWidth(2)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_default_image()
        self._setup_attributes()
        self._signals_setup()

    def _setup_attributes(self) -> None:
        self._start_drag: Optional[QPointF] = None
        self._temp_bbox: Optional[WBoundingBoxGraphicsItem] = None
        self._drawing_mode: bool = False
        # XXX not sure if I still need this private attribute
        self._current_image_id: Optional[str] = None
        self.groups: Dict[str, WGraphicsItemGroup] = OrderedDict()
        self._edit_mode: bool = False
        self._box_pen: QPen = QPen(self.default_bounding_box_pen)

    def _signals_setup(self) -> None:
        pass
        # self.data_about_to_reset.connect(self._remove_all_items)

    @Slot()
    def _remove_all_graphics_items(self) -> None:
        for group in self.groups.values():
            self.removeItem(group)
        self.groups = OrderedDict()

    @Slot()
    def reset_images(self) -> None:
        """
        Also resets the bounding boxes.
        """
        self.clear()
        self._display_default_image()
        print('images reset')

    @Slot()
    def reset_bounding_boxes(self) -> None:
        self._remove_all_graphics_items()

    def _set_group_visible(self, image_id: str, visible: bool = True):
        group = self.groups[image_id]
        group.setVisible(visible)

    def show(self, image_id: str):
        self._set_group_visible(image_id, True)
        self._current_image_id = image_id

    def hide(self, image_id: Optional[str] = None):
        # if no image_id passed in, hide every bounding box
        if image_id is None:
            for _image_id in self.groups:
                self._set_group_visible(_image_id, False)
            self._current_image_id = None
        elif image_id in self.groups:
            self._set_group_visible(image_id, False)
            self._current_image_id = None
        else:
            raise ValueError('{} is not a group.'.format(image_id))

    def _display_default_image(self):
        """
        Show dummy image to avoid AttributeError when self._pixmap.setPixmap()
        is called (see self.set_pixmap).
        """
        pixmap = self.array2pixmap(self.default_image, rescale=False)
        self._pixmap = self.addPixmap(pixmap)
        for view in self.views():
            view.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        # self._pixmap.setFlag(QGraphicsItem.ItemIsFocusable, False)

    def create_group(self, name: str):
        group = WGraphicsItemGroup(name, parent=self.pixmap)
        group.setVisible(False)
        group.setEnabled(False)
        self.groups[name] = group

    def add_bounding_box(self, bbox: WBoundingBoxGraphicsItem) -> None:
        """
        """
        group_name = bbox.get_image_id()
        if group_name not in self.groups:
            raise ValueError(
                'GraphicsItemGroup associated with image ID ' +
                '{} has not been instantiated.'.format(group_name))

        group = self.groups[group_name]
        bbox.setParentItem(group)
        bbox.setPen(self._box_pen)

    @Property(QPen)
    def box_pen(self) -> QPen:
        return self._box_pen

    @Property(int)
    def box_line_width(self) -> int:
        return self._box_pen.width()

    def _apply_new_pen(self) -> None:
        for group in self.groups.values():
            for item in group:
                item.setPen(self._box_pen)

    def set_line_width(self, width: int) -> None:
        self._box_pen.setWidth(width)
        self._apply_new_pen()

    def set_box_color(self, color: QColor) -> None:
        self._box_pen.setColor(color)
        self._apply_new_pen()

    @Property('QPixmap')
    def pixmap(self) -> None:
        return self._pixmap

    # @pixmap.setter
    # def pixmap(self, dummy):
    #     raise NotImplementedError('Use the set_pixmap method instead.')

    def set_pixmap(self, px: np.ndarray, rescale: bool = True):
        """
        Set the background image with a numpy array.

        If 'px' is the same size as the previous image -- e.g. another image
        channel or frame in a time series -- keep the same level of zoom.
        Otherwise fit the whole image in the current view.
        """
        old = self._pixmap.pixmap()
        w, h = old.width(), old.height()
        new = self.array2pixmap(px, rescale)
        self._pixmap.setPixmap(new)

        if not (new.width() == w and new.height() == h):
            # https://bit.ly/2thKCUA
            rect = self._pixmap.sceneBoundingRect()
            self.setSceneRect(rect)
        for view in self.views():
            view.fit_to_window()

    @staticmethod
    def rescale_array(array):
        min_ = array.min()
        max_ = array.max()
        array = (array - min_) / (max_ - min_) * 256
        return array

    def array2pixmap(self, array: np.ndarray, rescale: bool = True) -> QPixmap:
        # https://github.com/sjara/brainmix/blob/master/brainmix/gui/numpy2qimage.py
        if rescale:
            array = WGraphicsScene.rescale_array(array)

        array = np.require(array, np.uint8, 'C').squeeze()
        width, height = array.shape[:2]
        if array.ndim == 2:
            format_ = QImage.Format_Grayscale8
            qimage = QImage(
                array.data, width, height, QImage.Format_Grayscale8)

        elif array.ndim == 3:
            # cv2 loads data in BGR order; Qt assumes BGR order too, but also
            # requires values for the alpha channel
            if array.shape[2] == 3:
                array = np.flip(array, axis=2)
                pad = np.full((width, height, 1), 255, np.uint8, 'C')
                array = np.concatenate([array, pad], axis=2)
                format_ = QImage.Format_RGB32
                # array = array.swapaxes(0, 1)

        # is segfault occuring because of python's garbage collection?
        # let's see if binding array to (persistent) instance variable
        # overcomes this issue
        self._image_array = array
        qimage = QImage(array.data, height, width, format_)
        return QPixmap.fromImage(qimage)

    @Property(bool)
    def edit_mode(self):
        return self._edit_mode

    @Slot(str, bool)
    def set_edit_mode(self, image_id: str, edit: bool):
        # print('setting edit mode to: {}'.format(edit))
        if edit is not self._edit_mode:
            self._edit_mode = edit
        if image_id in self.groups:
            print('item editing set to: {}'.format(edit))
            group = self.groups[image_id]
            group.set_edit_mode(edit)
        else:
            raise ValueError('{} not a valid image'.format(image_id))

    @Property(bool)
    def drawing_mode(self) -> bool:
        return self._drawing_mode and self._edit_mode

    @Slot(bool)
    def set_drawing_mode(self, draw: bool):
        self._drawing_mode = draw

    def get_current_label(self) -> str:
        """
        Dummy method. In a later version this will return the label currently
        selected by the user.
        """
        return 'pill'

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self._temp_bbox and event.button() == Qt.LeftButton:
            # get updated parameters
            pos = event.scenePos()
            xmax = round(pos.x())
            ymax = round(pos.y())
            xmin = round(self._temp_bbox.parameter.xmin)
            ymin = round(self._temp_bbox.parameter.ymin)
            # make sure xmin, ymin <= xmax, ymax
            xmin, xmax = sorted((xmin, xmax))
            ymin, ymax = sorted((ymin, ymax))

            self._temp_bbox.parameter.xmin = xmin
            self._temp_bbox.parameter.ymin = ymin
            self._temp_bbox.parameter.xmax = xmax
            self._temp_bbox.parameter.ymax = ymax
            self._temp_bbox.parameter.state |= AnnotationCheckedState.CORRECT

            current_group = self.groups[self._current_image_id]
            self._temp_bbox.setParentItem(current_group)
            self._temp_bbox = None
            self._start_drag = None
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self._temp_bbox and self._start_drag:
            rect = self._temp_bbox.rect()
            pos = event.scenePos()
            delta = pos - self._start_drag
            rect.setWidth(delta.x())
            rect.setHeight(delta.y())
            self._temp_bbox.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.LeftButton and self.drawing_mode:
            index = len(self.groups[self._current_image_id])
            pos = event.buttonDownScenePos(Qt.LeftButton)
            self._start_drag = pos
            kwargs = dict(
                xmin=pos.x(),
                ymin=pos.y(),
                xmax=pos.x(),
                ymax=pos.y(),
                label=self.get_current_label(),
                image_id=self._current_image_id,
                index=index,
                state=AnnotationCheckedState.NEW | AnnotationCheckedState.REVIEWED)

            initial_parameter = BoundingBoxParameter(**kwargs)

            self._temp_bbox = WBoundingBoxGraphicsItem(
                initial_parameter, parent=self.pixmap)
            self._temp_bbox.setPen(self._box_pen)
            self._temp_bbox.set_editable(True)
        else:
            super().mousePressEvent(event)
