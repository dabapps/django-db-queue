from django.conf import settings
from django_dbq.models import Job
from rest_framework import serializers
import json


class JobSerializer(serializers.Serializer):
    name = serializers.ChoiceField()
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)
    state = serializers.CharField(read_only=True)
    workspace = serializers.WritableField(required=False)
    url = serializers.HyperlinkedIdentityField(view_name='job_detail')

    def __init__(self, *args, **kwargs):
        super(JobSerializer, self).__init__(*args, **kwargs)
        self.fields['name'].choices = ((key, key) for key in settings.JOBS)

    def validate_workspace(self, attrs, source):
        workspace = attrs.get('workspace')
        if workspace and isinstance(workspace, basestring):
            try:
                attrs['workspace'] = json.loads(workspace)
            except ValueError:
                raise serializers.ValidationError("Invalid JSON")
        return attrs

    def restore_object(self, attrs, instance=None):
        return Job(**attrs)
