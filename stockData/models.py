from django.db import models

# Create your models here.
class StockData(models.Model):
    stockId = models.CharField(max_length=20, null=True)
    tradingVolume = models.IntegerField(default=0)
    highestPrice = models.FloatField(default=0)
    lowestPrice = models.FloatField(default=0)
    openingPrice = models.FloatField(default=0)
    closingPrice = models.FloatField(default=0)
    timestamp = models.IntegerField(default=0)

    class Meta:
        db_table = 'stockData'


class StockInfo(models.Model):
    stockId = models.CharField(max_length=20, primary_key=True)
    stockName = models.CharField(max_length=50, null=True)
    companyName = models.CharField(max_length=50, null=True)
    information = models.CharField(max_length=500, null=True)

    class Meta:
        db_table = 'stockInfo'


class News(models.Model):
    title = models.CharField(max_length=200)
    link = models.CharField(max_length=200)
    timestamp = models.IntegerField(default=0)
    brief = models.CharField(max_length=500, null=True)

    class Meta:
        db_table = 'news'

