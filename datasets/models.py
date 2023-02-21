import datetime as datetime
from django.db import models, connection


# Create your models here.
class TestDataset(models.Model):

    item_id = models.CharField(max_length=120)
    datetime = models.DateTimeField(max_length=10, default=datetime.datetime.now)
    value = models.FloatField(null=True)

    @classmethod
    def truncate(cls):
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE TABLE "{0}" CASCADE'.format(cls._meta.db_table))

    class Meta:
        db_table = 'historytable'
        verbose_name = 'test data value'
        verbose_name_plural = 'current dataset'

    def __str__(self):
        return self.item_id
