from django.db import models


class SteamTracker_User(models.Model):
    class Meta:
        managed = False
        db_table = 'users'
    steam64id = models.IntegerField(primary_key=True)
    avatar = models.TextField()


class avatarFinder_Log(models.Model):
    username = models.CharField(max_length=17, blank=True, null=True)
    time = models.DateTimeField()
    avatar = models.CharField(max_length=43)
    allProfiles = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.time} {self.username} - {self.avatar} {'[all]' if self.allProfiles else ''}"

    class Meta:
        verbose_name_plural = 'Avatar Finder Logs'

class marketFinder_Log(models.Model):
    username = models.CharField(max_length=17, blank=True, null=True)
    time = models.DateTimeField()
    avatar = models.CharField(max_length=178)

    def __str__(self):
        return f'{self.time} {self.username} - {self.avatar}'

    class Meta:
        verbose_name_plural = 'Market Finder Logs'
