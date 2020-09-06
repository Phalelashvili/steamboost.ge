from django.db import models
import datetime


class Comment_queue(models.Model):
    steam64id = models.CharField(max_length=17)
    comment = models.TextField(blank=True, null=True)
    delay = models.IntegerField(default=0)
    last_return = models.DateTimeField(
        default=datetime.datetime(2002, 7, 22, 15, 27, 27, 699669))
    last_comment = models.DateTimeField(
        default=datetime.datetime(2002, 7, 22, 15, 27, 27, 699669))
    amount = models.IntegerField(blank=True, null=True)
    commented = models.TextField(blank=True, null=True)
    returned = models.TextField(blank=True, null=True)
    time = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return '%s - %s %s' % (self.steam64id, self.comment, self.amount)

    class Meta:
        verbose_name_plural = "Comment Boost"


class Hour_queue(models.Model):
    user = models.CharField(max_length=17)
    username = models.CharField(max_length=255, unique=True)
    password = models.TextField(max_length=255)
    authcode = models.CharField(max_length=630, blank=True, null=True)
    games = models.CharField(max_length=255)
    free = models.BooleanField()
    target_time = models.IntegerField()
    steam64id = models.CharField(
        blank=True, null=True, max_length=17, unique=True)
    boosted_time = models.FloatField(blank=True, null=True, default=0)
    finished = models.BooleanField(default=False)
    stopped = models.BooleanField(default=False)
    log = models.TextField(blank=True, null=True, default='')
    errlog = models.TextField(blank=True, null=True, default='')

    def __str__(self):
        return '%s%s - %s/%s' % ('-' if self.stopped else '', self.username, self.boosted_time, self.target_time)

    class Meta:
        verbose_name_plural = "Hour Boost"
        ordering = ('stopped',)


class Trade_queue(models.Model):
    user = models.CharField(max_length=17)
    steam64id = models.CharField(
        blank=True, null=True, max_length=17, unique=True)
    username = models.CharField(max_length=255, unique=True)
    password = models.TextField()
    identity_secret = models.CharField(max_length=80, blank=True, null=True)
    shared_secret = models.CharField(max_length=80, blank=True, null=True)
    authcode = models.CharField(max_length=630, blank=True, null=True)
    amount = models.IntegerField()
    trade_link = models.URLField(blank=True, null=True)
    one_way_trade = models.BooleanField()
    log = models.TextField(blank=True, null=True, default='')
    errlog = models.TextField(blank=True, null=True, default='')
    finished = models.BooleanField(default=False)
    stopped = models.BooleanField(default=False)
    trades_sent = models.IntegerField(blank=True, null=True, default=0)

    def __str__(self):
        return '%s%s - %s/%s' % ('-' if self.stopped else '', self.username, self.trades_sent, self.amount)

    class Meta:
        verbose_name_plural = "Trade Boost"
        ordering = ('stopped',)


class Artwork(models.Model):
    user = models.CharField(max_length=17)
    sharedID = models.CharField(max_length=70, unique=True)
    likeAmount = models.IntegerField()
    favAmount = models.IntegerField()
