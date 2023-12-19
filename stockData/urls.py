from django.urls import path
from .views import *

urlpatterns = [
    path('kline/<str:stock_id>', req_kline, name='req_kline'),
    path('brief/<str:stock_id>', req_brief, name='req_brief'),
    path('news', req_news),
    path('best/<str:k>', req_best_k),
    path('show', show_stock)
]
