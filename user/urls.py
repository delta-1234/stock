from django.urls import path
from .views import *

urlpatterns = [
    path('register', register),
    path('login', login),
    path('simulate/hold/<str:user_id>', req_hold),
    path('simulate/order/<str:user_id>', req_order),
    path('order', try_order),
    path('favor/<str:user_id>', req_favor),
    path('addfavor', add_favor),
    path('rollback', delete_order),
    path('charge', charge),
    path('withdraw', withdraw),
    path('balance/<str:user_id>', req_balance),
    path('upload/photo', upload_photo),
    path('getPhoto', req_photo),
    path('deletefavor', delete_favor)
]
