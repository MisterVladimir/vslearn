# -*- coding: utf-8 -*-
from io import BytesIO
from functools import partial
import numpy as np
import os
from PIL import Image
from typing import Callable, Dict, Generator, List, Optional, Set, Tuple, Union
import tensorflow as tf
from xml.etree import ElementTree as ET

# TODO make this a set-able parameter
from . import CLASS_INT_TO_TEXT, CLASS_TEXT_TO_INT, ExampleFields
from .enums import MachineLearningMode


class WRecordWriter(object):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self._writer: tf.python_io.TFRecordWriter = \
            tf.python_io.TFRecordWriter(filename)

    def __enter__(self) -> 'WRecordWriter':
        return self

    def __exit__(self, *args, **kwargs) -> None:
        self._writer.close()

    # https://bit.ly/2sN773P
    @staticmethod
    def to_int64_feature(value: List[int]) -> tf.train.Feature:
        return tf.train.Feature(int64_list=tf.train.Int64List(value=value))

    @staticmethod
    def to_bytes_feature(value: List[bytes]) -> tf.train.Feature:
        return tf.train.Feature(bytes_list=tf.train.BytesList(value=value))

    @staticmethod
    def to_floats_feature(value: List[float]) -> tf.train.Feature:
        return tf.train.Feature(float_list=tf.train.FloatList(value=value))

    def create_example(self,
                       bboxes: List[List[int]],
                       labels: List[str],
                       filename: str
                       ) -> Callable[[str, str], tf.train.Example]:
        """
        Parameters
        ------------
        bboxes : Union[np.ndarray, List[List[int]]]
            bounding box coordinates

        labels : Union[np.ndarray, List[str]]
            Class of each bounding box.

        filename : str
            Image filename.
        """
        format_dict_PIL: Dict[str, str] = {
            'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png'}
        format_dict_TF: Dict[str, bytes] = {
            'jpeg': b'jpg', 'jpg': b'jpg', 'png': b'png'}
        image_file_extension: str = filename.split(os.path.extsep)[-1]

        PIL_image_format: str = format_dict_PIL[image_file_extension]
        image_bytes_io = BytesIO()
        with Image.open(filename) as im:
            im.save(image_bytes_io, PIL_image_format)
            height: int = im.height
            width: int = im.width
        image_bytes_io.seek(0)
        image_bytes: bytes = image_bytes_io.read()

        TF_image_format = format_dict_TF[image_file_extension]

        try:
            xmin, ymin, xmax, ymax = np.array(bboxes).T
        except ValueError:
            xmin, ymin, xmax, ymax = np.array([[], [], [], []])

        image_height_feature = self.to_int64_feature([height])
        image_width_feature = self.to_int64_feature([width])
        image_feature = self.to_bytes_feature([image_bytes])
        filename_feature = self.to_bytes_feature([filename.encode('utf-8')])
        image_format_feature = self.to_bytes_feature([TF_image_format])
        xmin_feature = self.to_floats_feature(xmin / width)
        ymin_feature = self.to_floats_feature(ymin / height)
        xmax_feature = self.to_floats_feature(xmax / width)
        ymax_feature = self.to_floats_feature(ymax / height)
        classes_feature = self.to_int64_feature([
            CLASS_TEXT_TO_INT[label] for label in labels])
        classes_text_feature = self.to_bytes_feature([
            label.encode('utf-8') for label in labels])

        return tf.train.Example(features=tf.train.Features(feature={
            ExampleFields.height: image_height_feature,
            ExampleFields.width: image_width_feature,
            ExampleFields.image_encoded: image_feature,
            ExampleFields.filename: filename_feature,
            ExampleFields.image_format: image_format_feature,
            ExampleFields.ground_truth_bbox_xmin: xmin_feature,
            ExampleFields.ground_truth_bbox_ymin: ymin_feature,
            ExampleFields.ground_truth_bbox_xmax: xmax_feature,
            ExampleFields.ground_truth_bbox_ymax: ymax_feature,
            ExampleFields.ground_truth_class_label: classes_feature,
            ExampleFields.ground_truth_class_text: classes_text_feature}))

    def write(self, example: tf.train.Example) -> None:
        self._writer.write(example.SerializeToString())


class WRecordReader(object):
    """
    Read inference or training data
    """
    common_feature = {
        ExampleFields.height: tf.FixedLenFeature((), tf.int64),
        ExampleFields.width: tf.FixedLenFeature((), tf.int64),
        ExampleFields.image_encoded: tf.FixedLenFeature(
            (), tf.string, default_value=''),
        ExampleFields.filename: tf.FixedLenFeature((), tf.string),
        ExampleFields.image_format: tf.FixedLenFeature((), tf.string)}
    train_feature = {
        ExampleFields.ground_truth_bbox_xmin: tf.VarLenFeature(tf.float32),
        ExampleFields.ground_truth_bbox_ymin: tf.VarLenFeature(tf.float32),
        ExampleFields.ground_truth_bbox_xmax: tf.VarLenFeature(tf.float32),
        ExampleFields.ground_truth_bbox_ymax: tf.VarLenFeature(tf.float32),
        ExampleFields.ground_truth_class_label: tf.VarLenFeature(tf.int64),
        ExampleFields.ground_truth_class_text: tf.VarLenFeature(tf.string)}
    inference_feature = {
        ExampleFields.inference_bbox_xmin: tf.VarLenFeature(tf.float32),
        ExampleFields.inference_bbox_ymin: tf.VarLenFeature(tf.float32),
        ExampleFields.inference_bbox_xmax: tf.VarLenFeature(tf.float32),
        ExampleFields.inference_bbox_ymax: tf.VarLenFeature(tf.float32),
        ExampleFields.inference_class_label: tf.VarLenFeature(tf.int64),
        ExampleFields.inference_score: tf.VarLenFeature(tf.float32)}

    def __init__(self):
        self._filename: tf.string = tf.placeholder(tf.string, [1])
        self._dataset: tf.data.TFRecordDataset = \
            tf.data.TFRecordDataset(self._filename)
        self._training_feature_dict = self._make_training_feature_dict()
        self._inference_feature_dict = self._make_inference_feature_dict()

    def _make_training_feature_dict(
            self) -> Dict[str, Union[tf.FixedLenFeature, tf.VarLenFeature]]:
        return {**self.common_feature, **self.train_feature}

    def _make_inference_feature_dict(
            self) -> Dict[str, Union[tf.FixedLenFeature, tf.VarLenFeature]]:
        return {**self.common_feature, **self.inference_feature}

    @staticmethod
    def _parse_proto(
            proto: tf.train.Example,
            features: Dict[str, Union[tf.FixedLenFeature, tf.VarLenFeature]]
            ):
        """
        Reads inferred bounding boxes from a tfrecord.
        """
        return tf.parse_single_example(proto, features)

    def read(self,
             filename: str,
             flag: MachineLearningMode
             ) -> Generator[Dict[str, np.ndarray], None, None]:
        """
        Parameters
        -------------
        filename : str
            Name of tfrecord file to be read.

        flag : MachineLearningMode
            What kind of data to extract from the tfrecord.
        """
        if flag & MachineLearningMode.INFERENCE:
            dataset: tf.data.TFRecordDataset = \
                self._dataset.map(partial(
                    self._parse_proto,
                    features=self._inference_feature_dict))
        elif flag & MachineLearningMode.TRAINING:
            dataset: tf.data.TFRecordDataset = \
                self._dataset.map(partial(
                    self._parse_proto,
                    features=self._training_feature_dict))
        else:
            raise ValueError('{} not supported'.format(flag))

        iterator = dataset.make_initializable_iterator()
        next_element = iterator.get_next()
        with tf.Session() as sess:
            sess.run(iterator.initializer,
                     feed_dict={self._filename: [filename]})
            while True:
                try:
                    result = sess.run(next_element)
                    # turn SparseTensorValue -> np.ndarray
                    yield {
                        k: (v[1] if isinstance(v, tf.SparseTensorValue) else v)
                        for k, v in result.items()}
                except tf.errors.OutOfRangeError:
                    break


# object class, xmin, ymin, xmax, ymax
LabelImgParameterType = Tuple[str, int, int, int, int]


def parse_labelImg_xml_file(xml_file: str) -> Tuple[str, int, int,
                                                    LabelImgParameterType]:
    """
    Get bounding box parameters from XML file exported by labelImg.
    # TODO check for errors in XML structure?
    # TODO return dictionary instead of tuple?

    Parameters
    -------------
    xml_file : str
        Full path to XML file.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    # XXX change image_id if implementation of ImagePathRegistry changes
    image_id = root.find('filename').text.split(os.path.extsep)[0]
    imwidth = int(root.find('size')[0].text)
    imheight = int(root.find('size')[1].text)
    parameters: List[LabelImgParameterType] = [
        (member[0].text, # class name, e.g. "person"
         int(member[4][0].text),
         int(member[4][1].text),
         int(member[4][2].text),
         int(member[4][3].text)) for member in root.findall('object')]

#     parameters: List[LabelImgParameterType] = []
#     for member in root.findall('object'):
#         value = (member[0].text,
#                  int(member[4][0].text),
#                  int(member[4][1].text),
#                  int(member[4][2].text),
#                  int(member[4][3].text))
#         parameters.append(value)
    return image_id, imwidth, imheight, parameters
