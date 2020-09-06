from django.db import models


class Pizza(models.Model):
    class Meta:
        managed = False
        db_table = 'listings'
    id = models.AutoField(primary_key=True)
    item = models.CharField(max_length=255)
    avatar = models.CharField(max_length=43)
    marketavatar = models.CharField(max_length=168)
    price = models.CharField(max_length=10, blank=True, null=True)
    time = models.TextField()
    details = models.TextField()
    removed = models.BooleanField(default=False)
    scanned = models.BooleanField(default=False)


class PizzaLite(models.Model):  # this table is copy of pizza, with different name
    class Meta:
        managed = False
        db_table = 'litelistings'
    id = models.AutoField(primary_key=True)
    item = models.CharField(max_length=255)
    avatar = models.CharField(max_length=43)
    marketavatar = models.CharField(max_length=168)
    price = models.CharField(max_length=10, blank=True, null=True)
    time = models.TextField()
    details = models.TextField()
    removed = models.BooleanField(default=False)
    scanned = models.BooleanField(default=False)


class Pizza_Log(models.Model):
    user = models.CharField(max_length=17)
    user_cookie = models.CharField(max_length=17, blank=True, null=True)
    ip = models.CharField(max_length=19)
    time = models.DateTimeField()
    tier = models.CharField(max_length=9, default='pizza')

    def __str__(self):
        return f"{self.user} ({self.user_cookie or '00000000000000000'}) - {self.ip} ({self.time}) [{self.tier}]"


class Pizza_Acquire_Log(models.Model):
    user = models.CharField(max_length=17, blank=True, null=True)
    time = models.DateTimeField()
    forceLock = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} ({self.time}) {'[Force Lock]' if self.forceLock else ''}"
