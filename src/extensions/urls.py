from django.urls import path
from . import views

urlpatterns = [
    path('market-finder', views.marketFinder),
    path('avatar-finder/<pre>/<avatar>', views.allProfiles),
    path('avatarApi', views.avatarFinder_api),
    path('tradeHistory', views.extension),
    path('paypal', views.paypal),
    path('<extension>/<arg>', views.extension_actions),
    path('avatarReverseSearch', views.search),
    path('similaritySearch', views.similaritySearch),
    path('rust', views.rustAPI)
]