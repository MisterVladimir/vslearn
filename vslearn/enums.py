# -*- coding: utf-8 -*-
from enum import IntFlag, auto


class DataFileType(IntFlag):
    XML = auto()
    CSV = auto()
    JSON = auto()

    JPG = auto()
    PNG = auto()

    TFRECORD = auto()

    BBOX = XML | CSV | JSON | TFRECORD
    IMAGE = JPG | PNG


class BoxCorner(IntFlag):
    """
    Describes corners (or center region) of the WBoundingBoxGraphicsItem.
    """
    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()


class BoxEditMode(IntFlag):
    """
    """
    NONE = 0

    TRANSLATE = auto()
    STRETCH = auto()

    MOUSE = auto()
    KEYBOARD = auto()


class Direction(IntFlag):
    """
    """
    NONE = 0
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class UserType(IntFlag):
    HUMAN = auto()
    MACHINE = auto()


class AnnotationCheckedState(IntFlag):
    """
    Result of a human review.
    """
    # whether the bounding box has been inspected (probably by a human)
    REVIEWED = auto()
    # whether the bounding box is placed correctly over the object
    CORRECT = auto()
    # bounding box was added by the user, e.g. not added by the algorithm or
    # person who edited this image set prior
    NEW = auto()


class MachineLearningMode(IntFlag):
    TRAINING = auto()
    TESTING = auto()
    INFERENCE = auto()
