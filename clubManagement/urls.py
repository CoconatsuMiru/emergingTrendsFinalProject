from django.contrib import admin
from django.urls import path
from clubManagement import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signUp, name='signup'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('organizations/', views.organizations, name='organizations'),
    path('organizations/<int:org_id>/', views.organization_detail, name='organization_detail'),
    path('organizations/<int:org_id>/delete/', views.delete_organization, name='delete_organization'),
    path('tasks/', views.tasks, name='tasks'),

    path('create-org/', views.create_organization, name='create_organization'),
    path('add-member/<int:org_id>/', views.add_member, name='add_member'),
    path('remove-member/<int:org_id>/<int:user_id>/', views.remove_member, name='remove_member'),

    path('logout/', views.logout_user, name='logout'),
]