from django.db import models


# Create your models here.

class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100, null=True)
    email = models.CharField(max_length=50, null=True)
    privilege = models.CharField(max_length=20, null=True)
    balance = models.FloatField(default=0)

    class Meta:
        db_table = 'user'


class FavorOfUser(models.Model):
    userId = models.ForeignKey(User, on_delete=models.CASCADE)
    stockId = models.CharField(max_length=20, null=True)

    class Meta:
        db_table = 'favor_of_user'


class StockOfUser(models.Model):
    userId = models.ForeignKey(User, on_delete=models.CASCADE)
    stockId = models.CharField(max_length=20, null=True)
    holdNum = models.IntegerField(default=0)
    spendMoney = models.FloatField(default=0)

    class Meta:
        db_table = 'stock_of_user'
        unique_together = (('userId', 'stockId'),)


class OrderOfUser(models.Model):
    userId = models.ForeignKey(User, on_delete=models.CASCADE)
    stockId = models.CharField(max_length=20, null=True)
    buyOrSell = models.BooleanField(default=False)
    orderNum = models.IntegerField(default=0)
    price = models.FloatField(default=0)
    time = models.IntegerField(default=0)
    finished = models.BooleanField(default=False)

    class Meta:
        db_table = 'order_of_user'


class Images(models.Model):
    userId = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='images/')

    class Meta:
        db_table = 'images'
