# -*- coding: utf-8 -*-
from collections import OrderedDict
import dataclasses
import datetime
import json
import numpy as np
import os
from pathlib import Path
import PIL
import tensorflow as tf
from typing import (
    Any, Dict, Generator, Iterable, Iterator, List, NamedTuple, Optional, Set,
    Tuple, Union)
import warnings

from . import Version, VERSION, ExampleFields
from .enums import MachineLearningMode
from .models.bounding_box import (
    default_human_user_id, default_machine_user_id, BoundingBoxParameter,
    UserID)
from .input_output import parse_labelImg_xml_file, WRecordReader
from .utils import dataclass_object_dump, dataclass_object_load


def _dumps_to_json(obj, **kwargs) -> str:
    assert 'default' not in kwargs, "'default' function already in use"
    return json.dumps(obj, default=dataclass_object_dump, **kwargs)


def _loads_from_json(filename: str, **kwargs):
    assert 'object_hook' not in kwargs, "'default' function already in use"
    as_string = None
    with open(filename) as f:
        as_string = f.read()
    return json.loads(as_string, object_hook=dataclass_object_load, **kwargs)


class ImagePathRegistry(object):
    """
    Note that internally we use only Path objects, but when filenames or
    directory-type data is returned, it's always returned as a string.

    img_id_to_image_path : OrderedDict
    """
    def __init__(self, img_id_to_image_path: Dict[str, str]) -> None:
        self._img_id_to_image_path = img_id_to_image_path

    def __contains__(self, value: str) -> bool:
        if not isinstance(value, str):
            return False
        else:
            stem = value.split(os.path.extsep)[0]
            return stem in self._img_id_to_image_path

    def __iter__(self) -> Generator[str, None, None]:
        for key in self._img_id_to_image_path:
            yield key

    def __len__(self) -> int:
        return len(self._img_id_to_image_path)

    @classmethod
    def from_dir(cls,
                 directory: Union[str, Path],
                 extension: str = 'jpg') -> 'ImagePathRegistry':
        # XXX look for PNG images too?
        directory = Path(directory)
        if not directory.is_dir():
            raise ValueError('{} is not a directory.'.format(str(directory)))
        image_paths = directory.glob('*' + extension)
        img_id_to_path = {
            cls.make_image_id_from_path(ip): str(ip) for ip in image_paths}
        return cls(img_id_to_path)

    @staticmethod
    def make_image_id_from_path(filename: Union[str, Path]) -> str:
        filename = Path(filename)
        return filename.stem

    def get_image_id_by_index(self, index: int) -> str:
        all_keys = list(self._img_id_to_image_path.keys())
        return all_keys[index]

    def get_filename_from_image_id(self, image_id: str) -> str:
        return self._img_id_to_image_path[image_id]

    def get_filename_by_index(self, index: int) -> str:
        key = self.get_image_id_by_index(index)
        return self._img_id_to_image_path[key]

    @property
    def image_ids(self) -> Iterator[str]:
        return iter(self._img_id_to_image_path)

    @property
    def filenames(self) -> Iterator[str]:
        return iter(self._img_id_to_image_path.values())

    def dumps_to_json(self, **kwargs) -> str:
        return _dumps_to_json(self._img_id_to_image_path, **kwargs)

    @classmethod
    def loads_from_json(cls, filename: str, **kwargs) -> 'ImagePathRegistry':
        result = _loads_from_json(filename)
        return cls(result)


@dataclasses.dataclass
class Annotation(object):
    """
    So that parameters defining an annotation are grouped into one place.
    """
    image_id: str
    image_width: int
    image_height: int
    # AnnotationRegistry's 'dumps' and 'loads' makes sure its version is
    # compatible
    version: Version = VERSION
    origin_filename: Optional[str] = None
    # annotation_shape will be implemented when necessary, i.e. when we want to
    # label images with polygons, circles, points, etc.
    # annotation_shape: str
    bounding_boxes: List['BoundingBoxParameter'] = \
        dataclasses.field(default_factory=lambda: [])

    def __repr__(self) -> str:
        return _dumps_to_json(self, indent=4)

    def __str__(self) -> str:
        return repr(self)

    def has_bounding_boxes(self) -> bool:
        return bool(self.bounding_boxes)

    def get_bounding_box(self, index: int) -> 'BoundingBoxParameter':
        return self.bounding_boxes[index]

    def delete_bounding_box(self, index: int) -> None:
        box = self.bounding_boxes[index]
        box.delete = True

    def update_boxes_correct(self, user: UserID):
        """
        Convenience method for marking all BoundingBoxParameters in
        self.bounding_boxes as 'correct'. This method should be called when
        the user finishes drawing or editing bounding boxes in the image.
        """
        user.timestamp = str(datetime.datetime.now())
        for box in self.bounding_boxes:
            box.set_state(user, True)

    @classmethod
    def from_tensor(cls,
                    tensor: Dict[str, tf.Tensor],
                    flag: MachineLearningMode,
                    record_filename: str = '',
                    user: UserID = default_machine_user_id,
                    confidence: float = 0.5):
        """
        Returns an Annotation instance from a tf.Tensor dictionary extracted
        from a TFRecord by WRecordReader.

        Parameters
        ------------
        tensor : Dict[str, tf.Tensor]
            `tensor` should be the value of WRecordReader's `read` method.

        flag : MachineLearningMode
            Describes which attributes to extract from `tensor`.

        user : UserID

        confidence : flaot
            If flag & MachineLearningMode.INFERENCE, a default argument of
            confidence=0.25 means only bounding boxes whose confidence score
            is greater than 0.25 will be included in the output list of
            BoundingBoxParameter.
        """
        # keys common to all tensor dictionaries, whether they are from
        # tfrecords containing training or inference data
        common_keys: Iterator[str] = (
            getattr(ExampleFields, name) for name in ExampleFields.common)
        _, _, image_filename, image_height, image_width = (
            tensor[k] for k in common_keys)
        image_filename: str = image_filename.decode('utf-8')
        image_id: str = ImagePathRegistry.make_image_id_from_path(image_filename)

        # base_box_keys: List[str] = ['xmin', 'ymin', 'xmax', 'ymax', 'label']
        base_box_keys: List[str] = ['label']
        x_coord_keys: List[str] = ['xmin', 'xmax']
        y_coord_keys: List[str] = ['ymin', 'ymax']
        # SparseTensorValue values
        if flag & MachineLearningMode.INFERENCE:
            mask = tensor[ExampleFields.inference_score] > confidence
            base_box_keys = base_box_keys + ['confidence']
        elif flag & MachineLearningMode.TRAINING:
            mask = True
        else:
            raise ValueError('{} is not a compatible flag.')
        box_keys = x_coord_keys + y_coord_keys + base_box_keys

        # get the key names in tensor
        base_tensor_keys: Dict[str, str] = {
            k: getattr(ExampleFields, k)[flag] for k in base_box_keys}
        x_tensor_keys: Dict[str, str] = {
            k: getattr(ExampleFields, k)[flag] for k in x_coord_keys}
        y_tensor_keys: Dict[str, str] = {
            k: getattr(ExampleFields, k)[flag] for k in y_coord_keys}

        # get bounding box parameters that pass the confidence threshold
        # and stack them into an array of shape (N, 5 or 6)
        base_values: Iterator[np.ndarray] = np.stack([
            tensor[base_tensor_keys[k]][mask] for k in base_tensor_keys], axis=1)
        x_coord_values: Iterator[np.ndarray] = image_width * np.stack([
            tensor[x_tensor_keys[k]][mask] for k in x_tensor_keys], axis=1)
        y_coord_values: Iterator[np.ndarray] = image_height * np.stack([
            tensor[y_tensor_keys[k]][mask] for k in y_tensor_keys], axis=1)
        box_values: np.ndarray = np.concatenate(
            [x_coord_values, y_coord_values, base_values], axis=1)

        boxes: List[BoundingBoxParameter] = [BoundingBoxParameter(
            **{**dict(zip(box_keys, _box_values)),
               'user': user, 'image_id': image_id, 'index': i})
            for i, _box_values in enumerate(box_values)]

        return cls(
            image_id=image_id, image_width=int(image_width),
            image_height=int(image_height), origin_filename=record_filename,
            bounding_boxes=boxes)


class AnnotationRegistry(object):
    annotation_version: Version = VERSION

    def __init__(
            self, img_id_to_annotation: Dict[str, Annotation] = OrderedDict()):
        self._img_id_to_annotation = img_id_to_annotation

    # might remove this in a future commit...we don't need two ways to get
    # image_ids
    def __iter__(self):
        for key in self._img_id_to_annotation:
            yield key

    def __repr__(self) -> str:
        return self.dumps_to_json(indent=4)

    def __str__(self) -> str:
        return 'AnnotationRegistry @ length {}'.format(
            len(self._img_id_to_annotation))

    @property
    def image_ids(self) -> Iterator[str]:
        return iter(self._img_id_to_annotation)

    @property
    def annotations(self):
        return iter(self._img_id_to_annotation.values())

    @classmethod
    def make_empty_registry(
            cls, image_registry: ImagePathRegistry) -> 'AnnotationRegistry':
        """
        Returns an AnnotationRegistry filled with Annotations absent of any
        bounding boxes.
        """
        def get_image_dims(filename: str) -> Tuple[int, int]:
            with PIL.Image.open(filename) as im:
                return im.size

        annotation_arg_names = [
            'image_id', 'version', 'image_width', 'image_height']
        annotation_args = (
            (img_id, VERSION, *get_image_dims(f))
            for img_id, f in zip(image_registry.image_ids,
                                 image_registry.filenames))

        # a generator of keyword arguments for each Annotation 
        kwargs = (
            dict(zip(annotation_arg_names, args)) for args in annotation_args)
        annotations = (Annotation(**kw) for kw in kwargs)

        return AnnotationRegistry(dict(zip(image_registry, annotations)))

    def get_annotation(self, img_id: str) -> Annotation:
        """
        There should be an annotation for every image_id, even if that
        Annotation contains no bounding boxes.
        """
        if img_id not in self._img_id_to_annotation:
            # return None
            raise ValueError('Image id "{}" does not exist'.format(img_id))
        else:
            return self._img_id_to_annotation[img_id]

    def _add_annotation_to_registry(
            self, img_id: str, annotation: Annotation) -> None:
        self._img_id_to_annotation[img_id] = annotation

    def update_annotation(
            self,
            img_id: str,
            arg: Union[Annotation, Dict[str, Any]]) -> None:
        """
        Update the Annnotation in this registry associated with `img_id`. The
        updated Annotation can be passed in as `arg`, in which case the current
        Annotation will be replaced with `arg`. If a dictionary is passed in,
        its keys and values should correspond to the names and values of the
        Annotation attribute to update.
        """
        if img_id not in self._img_id_to_annotation:
            raise ValueError('{} not in this registry.'.format(img_id))
        elif isinstance(arg, Dict):
            # print('arg is Dict: {}'.format(arg))
            annotation = self._img_id_to_annotation[img_id]
            for k, v in arg.items():
                setattr(annotation, k, v)
        elif isinstance(arg, Annotation):
            # print('arg is an annotation: {}'.format(str(arg)))
            annotation = arg
        self._add_annotation_to_registry(img_id, annotation)

    def add_annotation(self, img_id, annotation: Annotation) -> None:
        if img_id in self._img_id_to_annotation:
            raise ValueError("{} already present. Use ".format(img_id) +
                             "'update_annotation' to replace values.")
        else:
            self._add_annotation_to_registry(img_id, annotation)

    def dumps_to_json(self, **kwargs) -> str:
        return _dumps_to_json(self._img_id_to_annotation, **kwargs)

    @classmethod
    def loads_from_json(cls, filename: str, **kwargs) -> 'AnnotationRegistry':
        result = _loads_from_json(filename)
        return cls(result)

    @classmethod
    def from_tfrecord(cls,
                      filename: str,
                      flag: MachineLearningMode,
                      user: UserID = default_machine_user_id,
                      confidence: float = 0.5):
        """
        """
        registry: 'AnnotationRegistry' = cls(OrderedDict())
        reader = WRecordReader()
        for tensor in reader.read(filename, flag):
            annotation = Annotation.from_tensor(
                tensor, flag, record_filename=filename, user=user,
                confidence=confidence)
            registry.add_annotation(annotation.image_id, annotation)
        return registry


class XMLFilename(NamedTuple):
    """
    Used for performing set operations on XML filenames. This objects allow us
    to identify xml files with the same 'stem' (see Path.stem) as, for example,
    an image file.
    """
    index: int
    filename: str

    def __eq__(self, other: Any):
        return other == self.stem

    def __hash__(self) -> int:
        return hash(self.stem)

    @property
    def stem(self):
        return os.path.basename(self.filename).split(os.path.extsep)[0]


def annotation_registry_from_labelImg(
        image_registry: ImagePathRegistry,
        xml_filenames: Iterable[Union[Path, str]],
        user: UserID = default_human_user_id) -> AnnotationRegistry:
    """
    Note this assumes XML extensions are 'xml', not, for example, 'lxml'.

    image_registry : ImagePathRegistry

    xml_filenames : Iterable[Union[Path, str]]

    user : UserID
        Person or machine (e.g. some ID associated with the trained neural net)
        who generated these files.
    """
    # for some reason we have to pass in OrderedDict() as an argument in order
    # for test_load_bounding_boxes to pass...not sure why. Maybe it's some
    # Python caching feature under the hood like string interning?
    registry = AnnotationRegistry(OrderedDict())

    # match up XML filenames with image IDs
    image_keys: Set[str] = set(image_registry.image_ids)
    xml_files: Set[XMLFilename] = set(
        (XMLFilename(index=i, filename=str(x))
        for i, x in enumerate(xml_filenames)))
    used_xml_files: Set[XMLFilename] = image_keys.intersection(xml_files)
    unused_xml_files: Set[str] = xml_files.difference(image_keys)
    if unused_xml_files:
        warnings.warn(
            '\n'.join((unused for unused in unused_xml_files)) +
            "\nwere not imported because they didn't match an " +
            "image ID in the registry.")
    bounding_box_keys = ['label', 'xmin', 'ymin', 'xmax', 'ymax']
    for xml in used_xml_files:
        filename = xml.filename
        image_id, imwidth, imheight, data = \
            parse_labelImg_xml_file(filename)
        common_annotation_kwargs = dict(
            image_id=image_id, image_width=imwidth, image_height=imheight,
            origin_filename=filename)
        bbox_kwargs = ({**dict(zip(bounding_box_keys, datum)), 'index': i}
                       for i, datum in enumerate(data))
        bboxes = [
            BoundingBoxParameter(**kw, image_id=image_id, user=user)
            for kw in bbox_kwargs]

        common_annotation_kwargs.update(bounding_boxes=bboxes)
        annotation = Annotation(**common_annotation_kwargs)
        registry.add_annotation(image_id, annotation)

    return registry


"""
What is the correct encapsulation of my information?
 - When I know features XYZ of the object, I can retrieve any other information
   about it.
"""
