from django.contrib import admin
from django.urls import path, include
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.conf.urls.i18n import i18n_patterns

admin.autodiscover()
admin.site.login = staff_member_required(
    admin.site.login, login_url='/login/steam/')

urlpatterns = [
    path('', include('main.urls')),
    path('boost/', include('boost.urls')),
    path('pizza/', include('pizza.urls')),
    path('susi/', include('susi.urls')),
    path('extension/', include('extensions.urls')),
    path('realadminpanel/', admin.site.urls, name='admin'),
    # other apps
    path('ჩანგელაგუნგე/', include('django.conf.urls.i18n')),
    path('jet/', include('jet.urls', 'jet')),
    path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),
    path('webpush/', include('webpush.urls')),
]

handler404 = 'main.views.handler404'
handler500 = 'main.views.handler500'
CSRF_FAILURE_VIEW = 'main.views.csrf_failure'
