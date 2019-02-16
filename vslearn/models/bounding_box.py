# -*- coding: utf-8 -*-
from collections import OrderedDict
import dataclasses
import datetime
import numpy as np
from qtpy.QtCore import Property, Slot, QPointF, Qt, QTimer
from qtpy.QtGui import QKeyEvent
from qtpy.QtWidgets import (
    QGraphicsItem, QGraphicsRectItem, QGraphicsSceneMouseEvent)
from typing import Any, List, Optional, Union

from ..enums import (
    UserType, AnnotationCheckedState, BoxEditMode, Direction)


@dataclasses.dataclass
class UserID(object):
    name: str
    typ: UserType
    timestamp: str


default_human_user_id = UserID(name='default',
                               typ=UserType.HUMAN,
                               timestamp=str(datetime.datetime.now()))


default_machine_user_id = UserID(name='default',
                                 typ=UserType.MACHINE,
                                 timestamp=str(datetime.datetime.now()))


class WBoundingBoxGraphicsItem(QGraphicsRectItem):
    """
    Bounding box editable by the user. Interface:

        Change Size
        -------------
        Click on bounding box to select it, then roll the mouse wheel within
        the rectangle bounds to expand or contract the side closest to the
        mouse pointer. Mouse wheel actions in the center of the bounding box
        expand or contract uniformly on all sides.

        Translate
        -------------
        Either one of:
        1) Click on the bounding box to select it, then drag with the mouse.
        2) Select bounding box, then press arrow keys to translate up, down,
           and side to side.

    Parameters
    ------------
    parameter : BoundingBoxParameter
        See attributes of BoundingBoxParameter.

    parent: Optional[WGraphicsItemGroup]
    """
    # how sensitive this item is to user input; i.e. how quickly is this Item
    # translated if they user holds down a keyboard arrow button
    sensitivity: int = 5
    arrow_keys: List[int] = [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]
    directions: List[Direction] = [Direction.UP, Direction.DOWN,
                                   Direction.LEFT, Direction.RIGHT]
    key_to_direction = dict(zip(arrow_keys, directions))

    def __init__(self, parameter: 'BoundingBoxParameter',
                 parent: Optional['QGraphicsItem'] = None):
        x, y = parameter.xmin, parameter.ymin
        width, height = parameter.get_width(), parameter.get_height()
        super().__init__(x, y, width, height, parent)
        self.parameter = parameter
        self._stretch_modifier = Qt.ShiftModifier
        self._set_default_flags()
        self.set_editable(False)
        self._setup()
        self._signals_setup()

    def _setup(self):
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self._keyboard_timer = QTimer()
        self._keyboard_timer.setInterval(5. / self.sensitivity)
        self._edit_mode = BoxEditMode.NONE
        self._direction = Direction.NONE

    def _signals_setup(self):
        pass

    def _set_default_flags(self):
        self.setFlag(QGraphicsRectItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)

    @Property(str)
    def image_id(self) -> str:
        return self.parameter.image_id

    @Property(int)
    def index(self) -> int:
        return self.parameter.index

    def setVisible(self, visible: bool):
        if self.parameter.delete:
            pass
        else:
            super().setVisible(visible)

    def setEnabled(self, enabled: bool):
        if self.parameter.delete:
            pass
        else:
            super().setEnabled(enabled)

    def delete(self):
        self.parameter.delete = True
        super().setVisible(False)
        super().setEnabled(False)

    @Property(bool)
    def editable(self) -> bool:
        return bool(self._edit_mode) and self._editable

    # @editable.setter
    # def editable(self, edit: bool):
    #     raise NotImplementedError('Use the "set_editable" methods instead.')

    @Slot(bool)
    def set_editable(self, edit: bool):
        """
        When a WBoundingBoxGraphicsItem is moved or otherwise edited,
        """
        self._editable = edit
        flags = (QGraphicsRectItem.ItemIsMovable,
                 QGraphicsRectItem.ItemSendsGeometryChanges,
                 QGraphicsRectItem.ItemSendsScenePositionChanges)
        for flag in flags:
            self.setFlag(flag, edit)

    def _get_rect_params(self, wh: bool = True) -> List[float]:
        """
        wh: bool
            If true, returns Tuple[x, y, width, height]. Otherwise returns
            (x, y) coordinates of top left and bottom right corners as a four-
            member tuple.
        """
        rect = self.mapToScene(self.rect()).boundingRect()
        if wh:
            return [rect.left(), rect.top(), rect.width(), rect.height()]
        else:
            return [rect.left(), rect.top(), rect.right(), rect.bottom()]

    @Slot()
    def _move_by_keys(self):
        i = 2
        direction_to_args = {Direction.UP: QPointF(0, -i),
                             Direction.DOWN: QPointF(0, i),
                             Direction.LEFT: QPointF(-i, 0),
                             Direction.RIGHT: QPointF(i, 0)}

        if self._edit_mode | BoxEditMode.TRANSLATE:
            delta = direction_to_args[self._direction]
            pos = self.pos()
            self.setPos(pos + delta)

    @Property(int)
    def stretch_modifier(self):
        return self._stretch_modifier

    def set_stretch_modifier(self, modifier: int):
        self._stretch_modifier = modifier

    def keyPressEvent(self, event: QKeyEvent):
        # determine whether one of the arrow keys were pressed
        if event.key() in self.arrow_keys:
            # determine whether the SHIFT button is pressed down concurrently
            if event.modifiers() == self._stretch_modifier:
                self._edit_mode |= BoxEditMode.STRETCH
            else:
                self._edit_mode |= BoxEditMode.TRANSLATE

            self._direction = self.key_to_direction[event.key()]
            self._move_by_keys()
            self._keyboard_timer.start()
        elif event.key() == Qt.Key_Delete:
            self.delete()

    def keyReleaseEvent(self, event: QKeyEvent):
        """
        Stops the self._keyboard_timer and notifies the scene's model that this
        WBoundingBoxGraphicsItem has been stretched or TRANSLATEd.
        """
        if event.key() in self.arrow_keys:
            self._keyboard_timer.stop()

    def wheelEvent(self, event: QGraphicsSceneMouseEvent):
        """
        Stretch the rectangle with the mouse wheel. This works by first
        subdividing bounding box into the following ninths

        -------------------------
        |   1   |   2   |   3   |
        |-------|-------|-------|
        |   4   |   5   |   6   |
        |-------|-------|-------|
        |   7   |   8   |   9   |
        -------------------------

        and then stretching the box's corner coordinates inwards or outwards
        depending on which way the mouse wheel was rolled.
        """
        if not self.isSelected():
            super().wheelEvent(event)
            return None
        # event.accept()
        # find ninth closest to mouse cursor location
        pos = event.pos()
        rect = self.rect()
        topleft = rect.topLeft()
        width = rect.width()
        height = rect.height()
        dx = QPointF(rect.width(), 0)
        dy = QPointF(0, rect.height())

        ninths = OrderedDict([
            (1, topleft + dx/6 + dy/6),
            (2, topleft + dx/2 + dy/6),
            (3, topleft + 5*dx/6 + dy/6),
            (4, topleft + dx/6 + dy/2),
            (5, topleft + dx/2 + dy/2),
            (6, topleft + 5*dx/6 + dy/2),
            (7, topleft + dx/6 + 5*dy/6),
            (8, topleft + dx/2 + 5*dy/6),
            (9, topleft + 5*dx/6 + 5*dy/6)])

        distances = [(pos - p).manhattanLength() for p in ninths.values()]
        corner = list(ninths.keys())[np.argmin(distances)]
        factor = (width + height) * event.delta() / 6000
        if corner in [1, 2, 3]:
            rect.setTop(rect.y() - factor)
        elif corner in [7, 8, 9]:
            rect.setHeight(height + factor)
        if corner in [1, 4, 7]:
            rect.setLeft(rect.x() - factor)
        elif corner in [3, 6, 9]:
            rect.setWidth(width + factor)
        elif corner == 5:
            rect.setTop(rect.y() - factor / 2)
            rect.setLeft(rect.x() - factor / 2)
            rect.setHeight(height + factor)
            rect.setWidth(width + factor)

        self.setRect(rect)

    def itemChange(self, change: int, value: Any) -> Any:
        if change == QGraphicsItem.ItemPositionHasChanged:
            xmin, ymin, xmax, ymax = self._get_rect_params(wh=False)
            self.parameter.xmin = round(xmin)
            self.parameter.ymin = round(ymin)
            self.parameter.xmax = round(xmax)
            self.parameter.ymax = round(ymax)
            # i think this will help remove weird graphics artifacts when
            # making the rect smaller?
            width = self.parameter.get_width()
            height = self.parameter.get_height()
            self.scene().update(xmin - 5, ymin - 5, width + 10, height + 10)

        return super().itemChange(change, value)


@dataclasses.dataclass
class BoundingBoxParameter(object):
    """
    xmin : Union[int, float]
        x coordinate of the top left corner. Increasing xmin moves the topleft
        coordinate to the right.

    ymin : Union[int, float]
        y coordinate of the top left corner. Increasing ymin moves the topleft
        coordinate down.

    xmax : Union[int, float]
        x coordinate of the bottom right hand corner.

    ymax : Union[int, float]
        y coordinate of the bottom right hand corner.

    image_id: str
        'image_id' and 'index' (see below) together form the bounding box's ID.
        'image_id' corresponds to that in the ImagePathRegistry.

    index: int
        'image_id' (see above) and 'index' together form the bounding box's ID.
        This number is unique to one WBoundingBoxGraphicsItem within one
        WGraphicsItemGroup.
    """
    xmin: Union[int, float]
    ymin: Union[int, float]
    xmax: Union[int, float]
    ymax: Union[int, float]
    label: str
    image_id: str
    index: int
    # name of person or algorithm ID that generated this annotation
    user: UserID = dataclasses.field(
        default_factory=lambda: default_human_user_id)
    confidence: float = 1.
    # see docs to AnnotationCheckedState
    state: AnnotationCheckedState = 0
    # whether the user deleted this bounding box
    delete: bool = False
    # whether any attributes have been changed since last time user saved
    # this bounding box
    _dirty: bool = False

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Mark this bounding box as 'dirty' if any parameters were changed.
        """
        if not getattr(self, name, value) == value:
            super().__setattr__('_dirty', True)
        super().__setattr__(name, value)

    def is_dirty(self) -> bool:
        return self._dirty

    def get_width(self) -> Union[int, float]:
        return abs(self.xmax - self.xmin)

    def get_height(self) -> Union[int, float]:
        return abs(self.ymax - self.ymin)

    def set_state(self, user: UserID, correct: Optional[bool] = True) -> None:
        """
        A BoundingBoxParameter may have three non-mutually exclusive states:
        1) REVIEWED : Whether the bounding box has been reviewed by `user`.
        2) CORRECT : `user` considers this bounding box to accurately represent
        the bounding box of the object
        3) NEW : bounding box has been added by `user`
        """
        self.user = user
        self.state |= AnnotationCheckedState.REVIEWED
        if correct:
            self.state |= AnnotationCheckedState.CORRECT
        else:
            self.state &= ~AnnotationCheckedState.CORRECT

    def make_box_graphics_item(self) -> WBoundingBoxGraphicsItem:
        return WBoundingBoxGraphicsItem(self, parent=None)
