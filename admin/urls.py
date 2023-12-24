from django.urls import path
from .views import *

urlpatterns = [
    path('list', req_user_list),
    path('balance', req_user_balance),
    path('simulate', req_order),
    path('deleteHead', delete_photo),
    path('deleteUser', delete_user)
]
