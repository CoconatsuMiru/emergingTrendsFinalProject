from django.urls import path
from . import views

urlpatterns = [
   path('main_page', views.login, name = 'login'),
   path('sign_up', views.signUp, name = 'signup'),
]
