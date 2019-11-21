from lxml import etree
from enum import Enum


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

    def __init__(self, name, attributes=[]):
        """
        Define a label inside the `meta` tag

        :param name: name of the label
        :param attributes: list of attributes. [Attribute, ...]
        """
        self.name = name
        self.attributes = attributes

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return other.name == self.name
        elif isinstance(other, str):
            return other == self.name
        else:
            return False


AnnotationEnum = Enum('AnnotationType', 'polygon polyline points box')
class Annotation():

    def __init__(self, type, label, points=[], occluded=False, z_order=None,
                 attributes=[], **kwargs):
        """
        Describes an annotation for an image. There are multiple types of
        annotation. Refer to `AnnotationEnum` to see the different types

        :param type: type of annotation. Instance of `AnnotationEnum`
        :param label: associated label string
        :param points: list with tuples of 2D points [(x0, y1), ..., (xn, yn)]
        :param occluded: annotation is occluded. Boolean
        :param z_order: integer with the z-order of the object
        :param attributes: list of attributes [(name, value), ...]
        """
        assert isinstance(type, AnnotationEnum), \
            'type arg is not instance of AnnotationEnum'

        self.type = type
        self.label = label
        self.points = points
        self.occluded = occluded
        self.z_order = z_order

        if self.type is AnnotationEnum.box:
            assert (len(points) == 3 or
                    all(c in kwargs for c in ['xtl', 'ytl', 'xbr', 'ybr'])), \
                    'Provide 4 points for the box. {} provided'.format(len(points))
            if len(points) == 4:
                self.xtl, self.ytl, self.xbr, self.ybr = points
            else:
                self.xtl, self.ytl = kwargs['xtl'], kwargs['ytl']
                self.xbr, self.ybr = kwargs['xbr'], kwargs['ybr']



class Image():

    def __init__(self, id, name, width, height, **kwargs):
        """
        Describe an image in the dataset.

        :param id: the id of the image
        :param name: string path to the image
        :param width: width of the image
        :param height: height of the image
        """
        self.id = id
        self.name = name
        self.width = width
        self.height = height

        if 'annotations' in kwargs:
            assert isinstance(kwargs['annotations'], list), \
                'annotations kwarg is not a list'
            self.annotation_list = kwargs['annotations']


class CVAT_XML():

    def __init__(self, xml_file_name):
        """
        Parse a CVAT XML file and fill this object with it's attributes

        :param xml_file_name: Name of the xml in cvat format
        """
        self.xml_file_name = xml_file_name
        self.parse_xml(self, self.xml_file_name)

    def parse_xml(self, xml_file_name):
        root = etree.parse(xml_file_name).getroot()

    def _parse_metadata(self, root):
        # TODO: Implement
        return None

    def _parse_images(self, root):
        return None

    def _parse_track_interpolation(self, root):
        # TODO: Implement
        return None
