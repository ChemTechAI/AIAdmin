from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportActionModelAdmin
from import_export.formats import base_formats

from datasets.models import TestDataset


# Register your models here.
class TestDatasetResource(resources.ModelResource):
    class Meta:
        model = TestDataset
        fields = ('id', 'item_id', 'value', 'datetime')
        import_id_fields = ['id']


class TestDatasetAdmin(ImportExportActionModelAdmin):
    list_display = (
        'item_id',
        'value',
        'datetime'
    )

    resource_class = TestDatasetResource
    formats = [base_formats.CSV]


admin.site.register(TestDataset, TestDatasetAdmin)
