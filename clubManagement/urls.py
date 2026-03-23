from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('signup/', views.signUp, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('organizations/', views.organizations, name='organizations'),
    path('tasks/', views.tasks, name='tasks'),
    path('logout/', views.logout_user, name='logout'),
]