from django.urls import path
from . import views
app_name='dashboard'
urlpatterns=[path('',views.index,name='index'),path('exportar/<str:kind>/',views.export,name='export'),path('<slug:page>/',views.index,name='page')]
