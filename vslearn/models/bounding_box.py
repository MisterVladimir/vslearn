# -*- coding: utf-8 -*-
from collections import OrderedDict
import dataclasses
import datetime
import numpy as np
from qtpy.QtCore import Property, QPointF, QRectF, Qt, QTimer, Slot
from qtpy.QtGui import QKeyEvent
from qtpy.QtWidgets import (
    QGraphicsItem, QGraphicsRectItem, QGraphicsSceneMouseEvent)
from typing import Any, Dict, List, Optional, Union

from ..enums import (
    BoxCorner, UserType, AnnotationCheckedState, BoxEditMode, Direction)


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
    sensitivity: int = 3

    def __init__(self, parameter: 'BoundingBoxParameter',
                 parent: Optional['QGraphicsItem'] = None):
        x, y = parameter.xmin, parameter.ymin
        width, height = parameter.get_width(), parameter.get_height()
        super().__init__(x, y, width, height, parent)
        self.parameter = parameter
        self._set_default_flags()
        self.set_editable(False)
        self._setup()

    def _setup(self):
        self.setAcceptedMouseButtons(Qt.LeftButton)
        # self._edit_mode: BoxEditMode = BoxEditMode.NONE
        # self._direction: BoxEditMode = Direction.NONE

    def _set_default_flags(self) -> None:
        self.setFlag(QGraphicsRectItem.ItemIsFocusable, False)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)

    def _set_editable_flags(self, edit: bool) -> None:
        flags = (QGraphicsRectItem.ItemIsMovable,
                 QGraphicsRectItem.ItemSendsGeometryChanges,
                 QGraphicsRectItem.ItemSendsScenePositionChanges)
        for flag in flags:
            self.setFlag(flag, edit)

    @Property(bool)
    def editable(self) -> bool:
        return self._editable

    @Slot(bool)
    def set_editable(self, edit: bool) -> None:
        """
        When a WBoundingBoxGraphicsItem is moved or otherwise edited,
        """
        self._editable = edit
        self._set_editable_flags(edit)

    def get_image_id(self) -> str:
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

    def _get_rect_params(self, wh: bool = True) -> List[float]:
        """
        wh: bool
            If true, returns Tuple[x, y, width, height]. Otherwise returns
            (x, y) coordinates of top left and bottom right corners as a four-
            member tuple.
        """
        rect: QRectF = self.mapToScene(self.rect()).boundingRect()
        if wh:
            return [rect.left(), rect.top(), rect.width(), rect.height()]
        else:
            return [rect.left(), rect.top(), rect.right(), rect.bottom()]

    def _get_corner(self,
                    pos: QPointF,
                    rect: QRectF,
                    max_distance: Optional[float] = None
                    ) -> Optional[BoxCorner]:
        """
        Which corner or edge of `rect` is `pos` closest to? First subdivide
        `rect` into the following ninths

        -------------------------
        |   1   |   2   |   3   |
        |-------|-------|-------|
        |   4   |   5   |   6   |
        |-------|-------|-------|
        |   7   |   8   |   9   |
        -------------------------

        Then determine the distance between `pos` and the centroid of each
        ninth. Return the BoxCorner enum associated with the smallest distance.

        Parameters
        ------------
        max_distance : Optional[float]
            Optional maximal distance between pos and a rectangle corner for
            which to return a value.
        """
        topleft: QPointF = rect.topLeft()
        dx: QPointF = QPointF(rect.width(), 0)
        dy: QPointF = QPointF(0, rect.height())

        ninths: Dict[BoxCorner, QPointF] = OrderedDict([
            (BoxCorner.TOP | BoxCorner.LEFT, topleft + dx/6 + dy/6),
            (BoxCorner.TOP | BoxCorner.MIDDLE, topleft + dx/2 + dy/6),
            (BoxCorner.TOP | BoxCorner.RIGHT, topleft + 5*dx/6 + dy/6),
            (BoxCorner.MIDDLE | BoxCorner.LEFT, topleft + dx/6 + dy/2),
            (BoxCorner.MIDDLE, topleft + dx/2 + dy/2),
            (BoxCorner.MIDDLE | BoxCorner.RIGHT, topleft + 5*dx/6 + dy/2),
            (BoxCorner.BOTTOM | BoxCorner.LEFT, topleft + dx/6 + 5*dy/6),
            (BoxCorner.BOTTOM | BoxCorner.MIDDLE, topleft + dx/2 + 5*dy/6),
            (BoxCorner.BOTTOM | BoxCorner.RIGHT, topleft + 5*dx/6 + 5*dy/6)])

        distances: List[float] = [
            (pos - p).manhattanLength() for p in ninths.values()]
        if max_distance is not None and min(distances) > max_distance:
            return None
        else:
            corners: List[BoxCorner] = list(ninths.keys())
            min_distance_index: int = np.argmin(distances)
            return corners[min_distance_index]

    def wheelEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Stretch the rectangle with the mouse wheel depending on where in the
        bounding box the mouse pointer is located and which way the mouse wheel
        is rolled.
        """
        if self._editable and self.isSelected():
            # find ninth closest to mouse cursor location
            pos = event.pos()
            rect = self.rect()
            corner = self._get_corner(pos, rect)

            width = rect.width()
            height = rect.height()
            factor = (width + height) * event.delta() / (self.sensitivity * 2000)
            if corner & BoxCorner.TOP:
                rect.setTop(rect.y() - factor)
            elif corner & BoxCorner.BOTTOM:
                rect.setHeight(height + factor)
            if corner & BoxCorner.LEFT:
                rect.setLeft(rect.x() - factor)
            elif corner & BoxCorner.RIGHT:
                rect.setWidth(width + factor)
            elif corner == BoxCorner.MIDDLE:
                rect.setTop(rect.y() - factor / 2)
                rect.setLeft(rect.x() - factor / 2)
                rect.setHeight(height + factor)
                rect.setWidth(width + factor)

            self.setRect(rect)
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.LeftButton:
            self.update()
        super().mousePressEvent(event)

    def itemChange(self, change: int, value: Any) -> Any:
        if change == QGraphicsItem.ItemPositionHasChanged:
            xmin, ymin, xmax, ymax = self._get_rect_params(wh=False)
            self.parameter.xmin = round(xmin)
            self.parameter.ymin = round(ymin)
            self.parameter.xmax = round(xmax)
            self.parameter.ymax = round(ymax)
            # i think this will help remove weird graphics artifacts when
            # making the rect smaller?
            # width = self.parameter.get_width()
            # height = self.parameter.get_height()
            # self.scene().update(xmin - 5, ymin - 5, width + 10, height + 10)

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
