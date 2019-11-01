from collections import OrderedDict
from datetime import timedelta
import json
import os, os.path as osp
import shutil
import sys
import tempfile
from urllib.parse import urlsplit

from django.utils import timezone
import django_rq

from cvat.apps.engine.log import slogger
from cvat.apps.engine.models import Task, Label, AttributeSpec, ShapeType
from cvat.apps.datumaro.util import current_function_name, make_zip_archive

sys.path.append(osp.join(osp.dirname(__file__), 'modules'))
from datumaro.components.project import Project
import datumaro.components.extractor as datumaro

from cvat.apps.datumaro.bindings import CvatImagesDirExtractor, CvatTaskExtractor


_MODULE_NAME = __package__ + '.' + osp.splitext(osp.basename(__file__))[0]
def log_exception(logger=None, exc_info=True):
    if logger is None:
        logger = slogger
    logger.exception("[%s @ %s]: exception occurred" % \
            (_MODULE_NAME, current_function_name(2)),
        exc_info=exc_info)

_TASK_IMAGES_EXTRACTOR = '_cvat_task_images'
_TASK_ANNO_EXTRACTOR = '_cvat_task_anno'

class TaskProject:
    @staticmethod
    def create(db_task):
        task_project = TaskProject(db_task)
        task_project._create()
        return task_project

    @staticmethod
    def load(db_task):
        task_project = TaskProject(db_task)
        task_project._load()
        task_project._init_dataset()
        return task_project

    @staticmethod
    def from_task(db_task, user):
        task_project = TaskProject(db_task)
        task_project._import_from_task(user)
        return task_project

    def __init__(self, db_task):
        self._db_task = db_task
        self._project_dir = self._db_task.get_datumaro_project_dir()
        self._project = None
        self._dataset = None

    def _create(self):
        self._project = Project.generate(self._project_dir)
        self._project.add_source('task_%s' % self._db_task.id, {
            'url': self._db_task.get_data_dirname(),
            'format': _TASK_IMAGES_EXTRACTOR,
        })
        self._project.env.extractors.register(_TASK_IMAGES_EXTRACTOR,
            CvatImagesDirExtractor)

        self._init_dataset()
        self._dataset.define_categories(self._generate_categories())

        self.save()

    def _load(self):
        self._project = Project.load(self._project_dir)
        self._project.env.extractors.register(_TASK_IMAGES_EXTRACTOR,
            CvatImagesDirExtractor)

    def _import_from_task(self, user):
        self._project = Project.generate(self._project_dir)

        self._project.add_source('task_%s_images' % self._db_task.id, {
            'url': self._db_task.get_data_dirname(),
            'format': _TASK_IMAGES_EXTRACTOR,
        })
        self._project.env.extractors.register(_TASK_IMAGES_EXTRACTOR,
            CvatImagesDirExtractor)

        self._project.add_source('task_%s_anno' % self._db_task.id, {
            'format': _TASK_ANNO_EXTRACTOR,
        })
        self._project.env.extractors.register(_TASK_ANNO_EXTRACTOR,
            lambda url: CvatTaskExtractor(url,
                db_task=self._db_task, user=user))

        self._init_dataset()

    def _init_dataset(self):
        self._dataset = self._project.make_dataset()

    def _generate_categories(self):
        categories = {}
        label_categories = datumaro.LabelCategories()

        db_labels = self._db_task.label_set.all()
        for db_label in db_labels:
            db_attributes = db_label.attributespec_set.all()
            label_categories.add(db_label.name)

            for db_attr in db_attributes:
                label_categories.attributes.add(db_attr.name)

        categories[datumaro.AnnotationType.label] = label_categories

        return categories

    def save(self, save_dir=None, save_images=False):
        if self._dataset is not None:
            self._dataset.save(save_dir=save_dir, save_images=save_images)
        else:
            self._project.save(save_dir=save_dir)

    def export(self, format, save_dir, save_images=False, server_url=None):
        if self._dataset is None:
            self._init_dataset()
        if format == DEFAULT_FORMAT:
            self._dataset.save(save_dir=save_dir, save_images=save_images)
        else:
            self._dataset.export(output_format=format,
                save_dir=save_dir, save_images=save_images)


DEFAULT_FORMAT = "datumaro_project"
DEFAULT_CACHE_TTL = timedelta(hours=10)
CACHE_TTL = DEFAULT_CACHE_TTL

def export_project(task_id, user, format=None, server_url=None):
    try:
        db_task = Task.objects.get(pk=task_id)

        if not format:
            format = DEFAULT_FORMAT

        cache_dir = db_task.get_export_cache_dir()
        save_dir = osp.join(cache_dir, format)
        archive_path = osp.normpath(save_dir) + '.zip'

        task_time = timezone.localtime(db_task.updated_date).timestamp()
        if not (osp.exists(archive_path) and \
                task_time <= osp.getmtime(archive_path)):
            os.makedirs(cache_dir, exist_ok=True)
            with tempfile.TemporaryDirectory(
                    dir=cache_dir, prefix=format + '_') as temp_dir:
                project = TaskProject.from_task(db_task, user)
                project.export(format, save_dir=temp_dir, save_images=True,
                    server_url=server_url)

                os.makedirs(cache_dir, exist_ok=True)
                make_zip_archive(temp_dir, archive_path)

            archive_ctime = osp.getctime(archive_path)
            scheduler = django_rq.get_scheduler()
            cleaning_job = scheduler.enqueue_in(time_delta=CACHE_TTL,
                func=clear_export_cache,
                task_id=task_id,
                file_path=archive_path, file_ctime=archive_ctime)
            slogger.task[task_id].info(
                "The task '{}' is exported as '{}' "
                "and available for downloading for next '{}'. "
                "Export cache cleaning job is enqueued, "
                "id '{}', start in '{}'" \
                    .format(db_task.name, format, CACHE_TTL,
                        cleaning_job.id, CACHE_TTL))

        return archive_path
    except Exception as ex:
        log_exception(slogger.task[task_id])
        raise

def clear_export_cache(task_id, file_path, file_ctime):
    try:
        if osp.exists(file_path) and osp.getctime(file_path) == file_ctime:
            os.remove(file_path)
            slogger.task[task_id].info(
                "Export cache file '{}' successfully removed" \
                .format(file_path))
    except Exception as ex:
        log_exception(slogger.task[task_id])
        raise