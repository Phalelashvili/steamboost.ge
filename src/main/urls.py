from django.urls import path, include
from django.views.generic import TemplateView
from . import views
from django.contrib.auth.views import logout
from jet.dashboard.dashboard_modules import google_analytics_views

urlpatterns = [
    path('admin', views.fake_admin),
    path('admin.php', views.fake_admin),
    path('wp-admin', views.fake_admin),
    path('wp-login.php', views.fake_admin),
    path('', views.index),
    path('', include('social_django.urls', namespace='social')),
    path('deposit', views.deposit),
    path('deposit/emoney', views.emoney_deposit),
    path('return/<amount>', views.return_gems),
    path('withdraw', views.withdraw),
    path('faq', views.faq),
    path('history', views.history),
    path('profile', views.profile),
    path('notifications', views.notifications),
    path('ref/<ref>', views.check_ref),
    path('free', views.free_credits),
    path('set_trade_link', views.set_trade_link),
    path('code/<code>', views.redeem_code),
    path('buy/<amount>', views.buy),
    path('maintenance/', include('maintenance_mode.urls')),
    path('realadminpanel/transactions/<id>', views.transaction),
    path('realadminpanel/transactions/<id>/<action>', views.transaction_action),
    path('realadminpanel/<action>', views.realadminpanel),
    path('realadminpanel/read_log/<pk>', views.read_log),
    path('realadminpanel/ajax/<action>', views.admin_ajax),
    path('realadminpanel/refund/<logid>', views.refund),
    path('user/<steam64id>', views.editUser),
    path('transfer/<old_steam64id>/<new_steam64id>', views.transferClient),
    path('logout', logout, {'next_page': '/'}),
    path('ajax/<action>', views.ajax),

    path('guard/<password>', views.guard)
]

# path('grind/next', views.grind_next),
# path('grind/check/<profile>', views.grind_check),
