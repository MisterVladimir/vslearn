# -*- coding: utf-8 -*-
import glob
import os
import pytest


temporarily_skipping = pytest.mark.skip("work in progress")
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def get_filenames(folder: str, extension: str):
    return glob.glob(os.path.join(folder, '*.' + extension))
