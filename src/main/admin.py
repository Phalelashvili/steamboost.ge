from django.contrib import admin
from .models import *

admin.site.register(Withdraw)
admin.site.register(User)
admin.site.register(Logs)
admin.site.register(PromoCode)
admin.site.register(Notifications)
admin.site.register(Settings)
admin.site.register(eMoneyDeposit)

admin.site.site_header = 'Admin Panel'
admin.site.site_title = 'Admin Panel'