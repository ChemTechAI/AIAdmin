from django.db import models
import datetime


class ResultDataset(models.Model):

    item_id = models.CharField(max_length=120)
    datetime = models.DateTimeField(max_length=10, default=datetime.datetime.now)
    value = models.FloatField(null=True)

    class Meta:
        db_table = 'last_test_function_result'
        verbose_name = 'test data value'
        verbose_name_plural = 'current dataset'

    def __str__(self):
        return self.item_id
