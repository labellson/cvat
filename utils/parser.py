from lxml import etree
from enum import Enum

import numpy as np


AttributeEnum = Enum('AttributeType', 'checkbox text radio number select')
class Attribute():

    def __init__(self, name, input_type, values, default_value=None):
        """
        Describe an attribute inside the `meta` tag

        :param name: name of the attribute
        :param input_type: type of input. Instance of `AttributeEnum`
        :param values: list with values
        :param default_value: default value. If not provided `values[0]`
        """
        assert isinstance(input_type, AttributeEnum), \
            'input_type arg is not instance of AttributeEnum'

        self.name = name
        self.input_type = input_type
        self.values = values
        self.default_value = values[0]

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return other.name == self.name
        elif isinstance(other, str):
            return other == self.name
        else:
            return False


class Label():

    def __init__(self, name, attributes=None):
        """
        Define a label inside the `meta` tag

        :param name: name of the label
        :param attributes: list of attributes. [Attribute, ...]
        """
        self.name = name
        self.attributes = attributes if attributes is not None else []

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return other.name == self.name
        elif isinstance(other, str):
            return other == self.name
        else:
            return False


AnnotationEnum = Enum('AnnotationType', 'polygon polyline points box')
class Annotation():

    def __init__(self, type, label, points=None, occluded=False, z_order=None,
                 attributes=None, **kwargs):
        """
        Describes an annotation for an image. There are multiple types of
        annotation. Refer to `AnnotationEnum` to see the different types.

        Boxes still have `xtl, ytl, xbr, xbl` attributes plus `points` array

        :param type: type of annotation. Instance of `AnnotationEnum`
        :param label: associated label string
        :param points: np.array of 2D points [[x0, y1], ..., [xn, yn]], or
            xml strings
        :param occluded: annotation is occluded. Boolean
        :param z_order: integer with the z-order of the object
        :param attributes: list of attributes [(name, value), ...]
        """
        assert isinstance(type, AnnotationEnum), \
            'type arg is not instance of AnnotationEnum'

        self.type = type
        self.label = label
        self.occluded = occluded
        self.z_order = z_order
        self.attributes = attributes if attributes is not None else []

        for k, v in kwargs.items():
            setattr(self, k, v)

        if isinstance(points, str) and len(points) > 0:
            self.points = np.array([coord.split(',')
                                    for coord in
                                    points.split(';')], dtype=np.float)

        elif (type == AnnotationEnum.box
              and all(c in kwargs for c in ['xtl', 'ytl', 'xbr', 'ybr'])):

            self.points = np.array([[self.xtl, self.ytl],
                                    [self.xbr, self.ybr]], dtype=np.float)
        else:
            self.points = np.array(points) if points is not None else np.array([])


class Image():

    def __init__(self, id, name, width, height, annotations=None, **kwargs):
        """
        Describe an image in the dataset.

        :param id: the id of the image
        :param name: string path to the image
        :param width: width of the image
        :param height: height of the image
        """
        self.id = int(id)
        self.name = name
        self.width = int(width)
        self.height = int(height)
        self.annotations = annotations if annotations is not None else []

        for k, v in kwargs.items():
            setattr(self, k, v)


class CVAT_XML():

    def __init__(self, xml_file_name):
        """
        Parse a CVAT XML file and fill this object with it's attributes

        :param xml_file_name: Name of the xml in cvat format
        """
        self.xml_file_name = xml_file_name
        self.parse_xml(self.xml_file_name)

    def parse_xml(self, xml_file_name):
        root = etree.parse(xml_file_name).getroot()
        self._parse_images(root)

    def _parse_metadata(self, root):
        # TODO: Implement
        return None

    def _parse_images(self, root):
        self.images = []
        for img_tag in root.iter('image'):
            img = Image(**{k: v for k, v in img_tag.items()})

            for ann_tag in img_tag:
                ann = Annotation(AnnotationEnum[ann_tag.tag],
                                 **{k: v for k, v in ann_tag.items()})

                for attr_tag in ann_tag.iter('attribute'):
                    # TODO: Parse values using attributes types from `meta`
                    ann.attributes.append((attr_tag.get('name'),
                                           attr_tag.text))

                img.annotations.append(ann)

            self.images.append(img)

    def _parse_track_interpolation(self, root):
        # TODO: Implement
        return None
