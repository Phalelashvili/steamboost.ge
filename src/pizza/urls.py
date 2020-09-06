from django.urls import path
from . import views

urlpatterns = [
    path('', views.pizza),
    path('lite', views.pizzaLite),
    path('remove/<pk>', views.pizza_remove),
    path('stats/<arg>', views.stats),
    # path('giveAccess/<steam64id>', views.giveAccess),
    # path('revokeAccess/<steam64id>', views.revokeAccess),
    path('lock', views.lockPage),
    path('lock/acquire', views.acquireLock),
    path('lock/release', views.releaseLock),
    path('ramelinki', views.memberList)
]