# -*- coding: utf-8 -*-
"""
scene.py
    Sticking with the Model/View programming style of Qt
    (see https://doc.qt.io/qt-5/model-view-programming.html), this module
    contains classes that manage the objects in the
    vlsearn.promoted.WGraphicsView.

    Classes
    --------
    WGraphicsScene
        The model to the WGraphicsView. This handles the user interactions that
        manipulate internal data, e.g. drawing or moving bounding boxes. By
        contrast, zooming in and out, which has no impact on underlying data,
        is handled by WGraphicsView.

    WGraphicsItemGroup
        A container for an image's bounding boxes.


bounding_box.py
    
"""
