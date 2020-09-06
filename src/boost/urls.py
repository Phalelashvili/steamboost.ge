from django.urls import path
from . import views

urlpatterns = [
    path('<action>', views.boost),
    path('<action>/<service>/<id>', views.boost_action),
    path('restart/<boost>/<username>/<authcode>', views.restart),
    path('grind', views.grind_page),
    path('price/<service>/<amount>', views.price),
]