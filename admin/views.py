import concurrent

from django.http import JsonResponse

from stockData.views import save_data
from user.models import User, StockOfUser, OrderOfUser, FavorOfUser, Images
from stockData.models import StockData, StockInfo
import time
from concurrent.futures import ThreadPoolExecutor


# Create your views here.

def req_user_list(request):
    user_list = User.objects.all()
    json_list = []
    for i in user_list:
        if i.privilege is not None:
            continue
        user_id = i.id
        if Images.objects.filter(userId_id=user_id).exists():
            photo = Images.objects.get(userId_id=user_id)
            image_url = request.build_absolute_uri(photo.image.url)
        else:
            image_url = 'http://127.0.0.1:8000/media/images/hutao.jpg'
        json_list.append({
            "id": i.id,
            "name": i.username,
            "photoUrl": image_url
        })
    return JsonResponse(json_list, safe=False)


def req_user_balance(request):
    user_list = User.objects.all()
    json_list = []
    for i in user_list:
        if i.privilege is not None:
            continue
        json_list.append({
            "id": i.id,
            "name": i.username,
            "balance": i.balance
        })
    return JsonResponse(json_list, safe=False)


def req_order(request):
    order_data = OrderOfUser.objects.all()
    json_list = []
    for i in order_data:
        if i.buyOrSell:
            action = "委托卖出"
        else:
            action = "委托买入"
        json_list.append({
            "id": i.id,
            "timeSimulate": i.time,
            "userid": i.userId_id,
            "action": action,
            "stock": i.stockId,
            "price": i.price,
            "size": i.orderNum,
            "finish": i.finished
        })
    return JsonResponse(json_list, safe=False)


def delete_photo(request):
    user_id = request.POST.get('userId')
    if Images.objects.filter(userId_id=user_id).exists():
        new_image = Images.objects.get(userId_id=user_id)
        new_image.delete()
        return JsonResponse({
            "success": True,
            "message": "删除用户头像成功"
        })
    else:
        return JsonResponse({
            "success": False,
            "message": "删除用户头像失败，用户只有默认头像"
        })


def delete_user(request):
    user_id = request.POST.get('userId')
    if User.objects.filter(id=user_id).exists():
        user = User.objects.get(id=user_id)
        user.delete()
        return JsonResponse({
            "success": True,
            "message": "删除用户成功"
        })
    else:
        return JsonResponse({
            "success": False,
            "message": "无此用户"
        })
