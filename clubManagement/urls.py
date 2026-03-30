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
    path('organizations/<int:org_id>/edit-member/', views.edit_member_role, name='edit_member_role'),
    path('organizations/<int:org_id>/kick-member/', views.kick_member, name='kick_member'),

    path('tasks/', views.tasks, name='tasks'),
    path('tasks/<int:org_id>/', views.org_tasks, name='org_tasks'),
    path('tasks/<int:org_id>/add/', views.add_task, name='add_task'),
    path('tasks/<int:org_id>/edit/', views.edit_task, name='edit_task'),
    path('tasks/<int:org_id>/delete/', views.delete_task, name='delete_task'),

    path('create-org/', views.create_organization, name='create_organization'),
    path('join-org/', views.join_organization, name='join_organization'),
    path('add-member/<int:org_id>/', views.add_member, name='add_member'),
    path('remove-member/<int:org_id>/<int:user_id>/', views.remove_member, name='remove_member'),

    path('logout/', views.logout_user, name='logout'),
]