# -*- coding: utf-8 -*-
import os
import pytest

from config import TEST_DATA_DIR, get_filenames
from vslearn.input_output import parse_labelImg_xml_file


labelImg_xml_folder = os.path.join(TEST_DATA_DIR, 'labelImg_xml_files')


def test_labelImg_xml_reader():
    """
    A very important test that yearns to be written.
    """
    labelImg_xml_filenames = get_filenames(labelImg_xml_folder, 'xml')
    labelImg_xml_filenames = sorted(labelImg_xml_filenames)
    # test no bounding boxes in XML file
    (no_boxes_image_id, no_boxes_imwidth, no_boxes_imheight,
     no_boxes_parameter) = parse_labelImg_xml_file(labelImg_xml_filenames[0])

    print(labelImg_xml_filenames[0])
    assert no_boxes_image_id == 'boxes0'
    assert no_boxes_imwidth == 500
    assert no_boxes_imheight == 600
    assert no_boxes_parameter == []
