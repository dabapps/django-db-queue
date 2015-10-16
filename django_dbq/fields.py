from uuidfield import UUIDField
from django.db.models import SubfieldBase
from django.utils import six


class UUIDField(six.with_metaclass(SubfieldBase, UUIDField)):
    pass
