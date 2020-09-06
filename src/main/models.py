import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    balance = models.FloatField(default=0)
    credits = models.FloatField(default=0)
    avatar = models.URLField(default='')
    trade_link = models.CharField(
        default='არაა დაყენებული', blank=True, null=True, max_length=99)
    pending_trade = models.BooleanField(default=False)
    referred_by = models.CharField(max_length=17, blank=True, null=True)
    referral_credits = models.IntegerField(default=0)
    freeTradeAvailable = models.BooleanField(default=True)
    freeCommentAvailable = models.BooleanField(default=True)
    freeArtworkAvailable = models.BooleanField(default=True)
    gems = models.IntegerField(default=0)
    bonus = models.DateTimeField(
        default=datetime.datetime(2002, 7, 22, 15, 27, 27, 699669))
    ip = models.CharField(max_length=15, blank=True, null=True)
    seen = models.BooleanField(default=True)
    extension_history = models.BooleanField(default=False)
    extension_paypal = models.BooleanField(default=False)
    extension_avatarFinder = models.DateTimeField(
        default=None, blank=True, null=True)

    class Meta:
        verbose_name_plural = "მომხმარებლები"


class PromoCode(models.Model):
    code = models.CharField(unique=True, max_length=16)
    use = models.IntegerField()
    gel = models.FloatField(default=0)
    credits = models.FloatField()
    used_by = models.TextField(default='', blank=True, null=True)

    def __str__(self):
        return f'{self.gel}₾ | {self.credits}C {self.use}'

    class Meta:
        verbose_name_plural = "პრომო კოდები"


class Logs(models.Model):
    user = models.CharField(max_length=17)  # didn't know about 1-1 relationship atm
    type = models.CharField(max_length=13)
    change = models.FloatField()
    time = models.DateTimeField()
    security_code = models.CharField(max_length=10, blank=True, null=True)
    details = models.TextField()
    link = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return '%s - %s (%s)' % (self.user, self.type, self.time)

    class Meta:
        verbose_name_plural = "ჩანაწერები"


class Notifications(models.Model):
    to = models.CharField(max_length=17)
    sender = models.CharField(max_length=17, blank=True, null=True)
    time = models.DateTimeField()
    message = models.TextField()
    cause = models.TextField(blank=True, null=True)

    def __str__(self):
        return '%s - %s - %s' % (self.to, self.message, str(self.time))

    class Meta:
        verbose_name_plural = "შეტყობინებები"


class eMoneyDeposit(models.Model):
    user = models.CharField(max_length=17)
    amount = models.FloatField()
    identifier = models.TextField()
    name = models.TextField()
    time = models.DateTimeField()
    transactioncode = models.CharField(max_length=10)
    security_code = models.CharField(max_length=10, blank=True, null=True)
    completed = models.BooleanField(default=False)
    time_completed = models.DateTimeField(blank=True, null=True)
    accepted = models.BooleanField(default=False)


class Withdraw(models.Model):
    user = models.CharField(max_length=17)
    website = models.TextField()
    identifier = models.TextField()
    name = models.TextField()
    amount = models.FloatField()
    time = models.DateTimeField()
    completed = models.BooleanField(default=False)
    refunded = models.BooleanField(default=False)
    time_completed = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return '%s - %s > %s' % (self.user, self.amount, self.website)

    class Meta:
        verbose_name_plural = "Withdraw"


class Settings(models.Model):
    name = models.TextField()
    gel_price = models.FloatField(default=1.25)
    min_price = models.FloatField(default=5)
    max_price = models.FloatField(default=500)
    credit_price = models.FloatField(default=1)
    tf2_key_price = models.FloatField(default=4)
    csgo_key_price = models.FloatField(default=4)
    t_boost_price = models.FloatField(default=6)
    h_boost_price = models.FloatField(default=0.01)
    c_boost_price = models.FloatField(default=0.1)
    a_boost_price = models.FloatField(default=0.1)
    tboost_enabled = models.BooleanField(default=False)
    hboost_enabled = models.BooleanField(default=False)
    cboost_enabled = models.BooleanField(default=False)
    aboost_enabled = models.BooleanField(default=False)
    deposit_enabled = models.BooleanField(default=False)
    withdraw_enabled = models.BooleanField(default=False)
    referral_reward = models.FloatField(default=3)
    referral_reward_user = models.FloatField(default=5)
    comment_reward = models.FloatField(default=0.25)
    min_sold_amount = models.IntegerField(default=10)
    banned_items = models.TextField(default='', blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Site Settings"
