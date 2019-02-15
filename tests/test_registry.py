# -*- coding: utf-8 -*-
import pytest
import os
import glob

from config import TEST_DATA_DIR, get_filenames, temporarily_skipping
from vslearn.input_output import parse_labelImg_xml_file
from vslearn.registry import (
     Annotation, AnnotationRegistry, annotation_registry_from_labelImg,
     BoundingBoxParameter, default_human_user_id, ImagePathRegistry)


_image_dir = os.path.join(TEST_DATA_DIR, 'images')
_image_filenames = sorted(get_filenames(_image_dir, 'jpg'))

_xml_dir = os.path.join(TEST_DATA_DIR, 'labelImg_xml_files')
_xml_filenames = sorted(get_filenames(_xml_dir, 'xml'))


class TestImagePathRegistry(object):
    def test_image_registry(self):
        registry = ImagePathRegistry.from_dir(_image_dir)
        assert len(registry) == 3
        assert sorted(registry.image_ids) == ['boxes0', 'boxes1', 'boxes2']
        assert sorted(registry.filenames) == _image_filenames
        assert 'boxes0' in registry

    def test_get_image_id_by_index(self):
        def get_stem(path):
            return os.path.basename(path).split(os.path.extsep)[0]
        registry = ImagePathRegistry.from_dir(_image_dir)
        image_id_list = [registry.get_image_id_by_index(i) for i in range(3)]
        correct_image_id_list = [get_stem(f) for f in _image_filenames]
        assert sorted(image_id_list) == correct_image_id_list

    def test_get_image_filename_by_index(self):
        registry = ImagePathRegistry.from_dir(_image_dir)
        filename_list = [registry.get_filename_by_index(i) for i in range(3)]
        assert sorted(filename_list) == _image_filenames


class TestAnnotationRegistry(object):
    _image_registry = ImagePathRegistry.from_dir(_image_dir)
    _annotation_registry = annotation_registry_from_labelImg(_image_registry,
                                                             _xml_filenames)

    def test_instantiate_empty(self):
        registry = AnnotationRegistry()

    def test_get(self):
        boxes0 = self._annotation_registry.get_annotation('boxes0')
        assert len(boxes0.bounding_boxes) == 0

        boxes1 = self._annotation_registry.get_annotation('boxes1')
        assert len(boxes1.bounding_boxes) == 1

    def test_to_json(self):
        result = self._annotation_registry.dumps_to_json(indent=4)


class TestBoundingBoxParameter(object):
    _box = BoundingBoxParameter(
        xmin=173, ymin=344, xmax=261, ymax=429, label='pill',
        user=default_human_user_id, image_id='boxes1', index=0)
