# -*- coding: utf-8 -*-
"""
enums.py
    Contains enumerations used throughout the program. This is a placeholder.


input_output.py
    Input/output operations, a placeholder for objects that parse the bounding
    box data.


main_window.py
    Contains the main_window and any widgets used directly in the main window.


main.py
    Script that runs the application.


promoted.py
    Contains promoted widgets, i.e. those imported by QtDesigner. These are not
    directly used by other modules.


registry.py
    Data structures for tracking the application data, e.g. image filenames.
    This is essentially a poor man's database, which associates images with
    their bounding boxes.
    See also vslearn.models.bounding_box.BoundingBoxparameter.


resource_rc.py
    This file was automatically generated by entering the following into the
    command terminal:
    > pyrcc5 resource.qrc -o resource_rc.py

    See Qt5's documentation here: http://doc.qt.io/qt-5/resources.html. In
    short, it translates the data in vslearn.icons into a form directly
    import-able by Python.


utils.py
    Functions for importing and exporting application data as JSON.


warning.py
    Dialogs that pop up when to notify the user of warnings or errors, e.g. if
    there was a problem saving data. These should be used sparingly so as to
    avoid glossing over bugs.
"""
import os
from typing import Any, Dict, Iterable, List, NamedTuple

from .enums import MachineLearningMode


class Version(NamedTuple):
    """
    Software version.
    """
    major: int
    minor: int
    micro: int

    def __eq__(self, other: Any) -> bool:
        attributes = ['major', 'minor', 'micro']
        self_attributes = [getattr(self, attr) for attr in attributes]

        if isinstance(other, Version):
            other_attributes = [getattr(other, attr) for attr in attributes]
        elif isinstance(other, str):
            try:
                other_attributes: Iterable[int] = map(int, other.split('.'))
            except ValueError:
                return False
        else:
            return False

        return all(map(lambda arg: arg[0] == arg[1], zip(self_attributes,
                                                         other_attributes)))

    def __str__(self) -> str:
        return '{}.{}.{}'.format(self.major, self.minor, self.micro)

    def __repr__(self) -> str:
        return 'vslearn.Version (major={}, minor={}, micro={})'.format(
            self.major, self.minor, self.micro)


class ExampleFields(object):
    image_encoded = 'image/encoded'
    image_format = 'image/format'
    filename = 'image/filename'
    height = 'image/height'
    width = 'image/width'
    ground_truth_class_text = 'image/object/class/text'
    ground_truth_class_label = 'image/object/class/label'
    ground_truth_bbox_ymin = 'image/object/bbox/ymin'
    ground_truth_bbox_xmin = 'image/object/bbox/xmin'
    ground_truth_bbox_ymax = 'image/object/bbox/ymax'
    ground_truth_bbox_xmax = 'image/object/bbox/xmax'
    inference_class_label = 'image/detection/label'
    inference_bbox_ymin = 'image/detection/bbox/ymin'
    inference_bbox_xmin = 'image/detection/bbox/xmin'
    inference_bbox_ymax = 'image/detection/bbox/ymax'
    inference_bbox_xmax = 'image/detection/bbox/xmax'
    inference_score = 'image/detection/score'

    common = ['image_encoded', 'image_format', 'filename', 'height', 'width']
    training = set(
        ('ground_truth_class_text', 'object_class_label',
         'ground_truth_bbox_ymin', 'ground_truth_bbox_xmin',
         'ground_truth_bbox_ymax', 'ground_truth_bbox_xmax'))
    inference = set(
        ('inference_class_label', 'inference_bbox_ymin', 'inference_bbox_xmin',
         'inference_bbox_ymax', 'inference_bbox_xmax', 'inference_score'))

    xmin = {MachineLearningMode.TRAINING: ground_truth_bbox_xmin,
            MachineLearningMode.INFERENCE: inference_bbox_xmin}
    ymin = {MachineLearningMode.TRAINING: ground_truth_bbox_ymin,
            MachineLearningMode.INFERENCE: inference_bbox_ymin}
    xmax = {MachineLearningMode.TRAINING: ground_truth_bbox_xmax,
            MachineLearningMode.INFERENCE: inference_bbox_xmax}
    ymax = {MachineLearningMode.TRAINING: ground_truth_bbox_ymax,
            MachineLearningMode.INFERENCE: inference_bbox_ymax}
    label = {MachineLearningMode.TRAINING: ground_truth_class_label,
             MachineLearningMode.INFERENCE: inference_class_label}
    confidence = {MachineLearningMode.INFERENCE: inference_score}


ROOT_DIR: str = os.path.abspath(os.path.dirname(__file__))
UI_DIR: str = os.path.join(ROOT_DIR, 'ui')
CLASS_TEXT_TO_INT: Dict[str, int] = {
    'pill': 1, 'not_pill': 2}
CLASS_INT_TO_TEXT: Dict[int, str] = {
    v: k for k, v in CLASS_TEXT_TO_INT.items()}
VERSION: Version = Version(major=0, minor=0, micro=3)
