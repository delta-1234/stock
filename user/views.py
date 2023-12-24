import concurrent

from django.http import JsonResponse

from stockData.views import save_data
from user.models import User, StockOfUser, OrderOfUser, FavorOfUser, Images
from stockData.models import StockData, StockInfo
import time
from concurrent.futures import ThreadPoolExecutor
import cryptocode


# Create your views here.

def register(request):  # 继承请求类
    if request.method == 'POST':  # 判断请求方式是否为 POST（此处要求为POST方式）
        username = request.POST.get('username')
        password = request.POST.get('password')
        password = cryptocode.encrypt(password, "delta")
        email = request.POST.get('email')
        user = User.objects.filter(username=username)
        balance = 0
        if user.exists():  # 若用户名重复
            return JsonResponse({'success': False, 'message': "注册失败，用户名重复"})
        else:
            new_user = User(username=username, password=password, email=email, balance=balance)
            new_user.save()  # 一定要save才能保存到数据库中
            return JsonResponse({'success': True, 'message': "注册成功"})
    else:
        return JsonResponse({'success': False, 'message': "非POST"})


def login(request):
    if request.method == 'POST':  # 判断请求方式是否为 POST（此处要求为POST方式）
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            user = User.objects.get(username=username)
            user_password = cryptocode.decrypt(user.password, "delta")
            if user_password == password:
                if user.privilege is None:
                    privilege = False
                else:
                    privilege = True
                return JsonResponse({"success": True, "message": "登录成功", "userId": user.id, "privilege": privilege})
            else:
                return JsonResponse(
                    {"success": False, "message": "登录失败，密码错误", "userId": user.id, "privilege": False})
        except User.DoesNotExist:
            return JsonResponse({"success": False, "message": "登录失败，没有此用户", "userId": "", "privilege": False})
    else:
        return JsonResponse({'success': False, 'message': "非POST"})


def update_hold(user_id):
    order_data = OrderOfUser.objects.filter(userId_id=user_id)
    now_time = int(time.time())
    current_time = now_time
    current_time = (current_time // 3600) * 3600  # 小时对齐
    today = (current_time // 86400) * 86400
    close_time = today + 9 * 3600  # 设定每天17点闭市
    if current_time > close_time:
        current_time = close_time
    # 先更新数据
    save_data(current_time)
    for i in order_data:
        if (now_time - i.time) <= 300:
            continue
        # 委托已经生效
        if i.finished:
            continue
        try:
            data = StockOfUser.objects.get(userId_id=user_id, stockId=i.stockId)
            user = User.objects.get(id=user_id)
            success_time = ((i.time + 300) // 3600) * 3600
            if success_time > close_time:
                success_time = close_time
            price = StockData.objects.get(stockId=i.stockId, timestamp=success_time).closingPrice
            if i.buyOrSell:
                data.holdNum = data.holdNum + i.orderNum
                data.spendMoney = data.spendMoney + price * i.orderNum
                user.balance = user.balance - price * i.orderNum
            else:
                data.holdNum = data.holdNum - i.orderNum
                data.spendMoney = data.spendMoney - price * i.orderNum
                user.balance = user.balance + price * i.orderNum
            user.save()
            data.save()
        except StockOfUser.DoesNotExist:
            try:
                price = StockData.objects.get(stockId=i.stockId, timestamp=current_time).closingPrice
            except StockData.DoesNotExist:
                price = StockData.objects.filter(stockId=i.stockId).order_by('timestamp')
                price = price.values('closingPrice').first()['closingPrice']
            spend = price * i.orderNum
            new_stock_user = StockOfUser(userId_id=user_id, stockId=i.stockId, holdNum=i.orderNum, spendMoney=spend)
            new_stock_user.save()
        i.finished = True
        i.save()


def req_hold(request, user_id):
    update_hold(user_id)
    current_time = int(time.time())
    current_time = (current_time // 3600) * 3600  # 小时对齐
    today = (current_time // 86400) * 86400
    close_time = today + 9 * 3600  # 设定每天17点闭市
    if current_time > close_time:
        current_time = close_time
    data = StockOfUser.objects.filter(userId_id=user_id)
    json_data = []
    for i in data:
        name = StockInfo.objects.get(stockId=i.stockId).stockName
        try:
            new_price = StockData.objects.get(stockId=i.stockId, timestamp=current_time).closingPrice
        except StockData.DoesNotExist:
            new_price = StockData.objects.filter(stockId=i.stockId).order_by('timestamp')
            new_price = new_price.values('closingPrice').first()['closingPrice']
        new_value = new_price * i.holdNum
        spend_money = i.spendMoney
        delta = new_value - spend_money
        if new_value != 0:
            delta_rate = delta / new_value
        else:
            delta_rate = 0
        if i.holdNum != 0:
            hold_price = spend_money / i.holdNum
        else:
            hold_price = 0

        json_data.append({
            "name": name,
            "code": i.stockId,
            "newValue": new_value,
            "delta": delta,
            "deltaRate": "{:.2f}".format(delta_rate),
            "hold": i.holdNum,
            "newPrice": new_price,
            "holdPrice": hold_price,
        })
    return JsonResponse(json_data, safe=False)


def req_order(request, user_id):
    update_hold(user_id)
    data = OrderOfUser.objects.filter(userId_id=user_id)
    json_data = []
    for i in data:
        name = StockInfo.objects.get(stockId=i.stockId).stockName
        if i.buyOrSell:
            order_type = "buy"
        else:
            order_type = "sell"
        price = i.price
        size = i.orderNum
        order_time = i.time
        json_data.append({
            "name": name,
            "type": order_type,
            "time": order_time,
            "price": price,
            "size": size,
            "orderId": i.id,
            "finished": i.finished
        })
    return JsonResponse(json_data, safe=False)


def try_order(request):
    current_time = int(time.time())
    current_time = (current_time // 3600) * 3600  # 小时对齐
    today = (current_time // 86400) * 86400
    close_time = today + 9 * 3600  # 设定每天17点闭市
    yesterday = close_time - 86400
    if current_time > close_time:
        current_time = close_time
    save_data(current_time)
    user_id = request.POST.get('userId')
    stock_id = request.POST.get('stockId')
    action = request.POST.get('action')
    if action == 'buy':
        action = True
    else:
        action = False

    try:
        price = StockData.objects.get(stockId=stock_id, timestamp=current_time).closingPrice
    except StockData.DoesNotExist:
        price = StockData.objects.filter(stockId=stock_id).order_by('timestamp')
        price = price.values('closingPrice').first()['closingPrice']
    size = request.POST.get('size')
    order_type = request.POST.get('type')
    now_time = int(time.time())
    new_order = OrderOfUser(userId_id=user_id, stockId=stock_id, buyOrSell=action,
                            orderNum=size, price=price, time=now_time)
    new_order.save()
    return JsonResponse({"success": True, "message": "委托成功"})


def delete_order(request):
    order_id = request.POST.get('orderId')
    print(order_id)
    now_time = int(time.time())
    try:
        order = OrderOfUser.objects.get(id=order_id)
        if (now_time - order.time) >= 300:
            return JsonResponse({"success": False, "message": "委托已经生效"})
        else:
            order.delete()
            return JsonResponse({"success": True, "message": "撤销成功"})
    except OrderOfUser.DoesNotExist:
        return JsonResponse({"success": False, "message": "委托已经生效"})


def get_data(i):
    current_time = int(time.time())
    current_time = (current_time // 3600) * 3600  # 小时对齐
    today = (current_time // 86400) * 86400
    close_time = today + 9 * 3600  # 设定每天17点闭市
    yesterday = close_time - 86400
    name = StockInfo.objects.get(stockId=i.stockId).stockName
    code = i.stockId
    data = StockData.objects.filter(stockId=code, timestamp=current_time)
    if data.exists():
        newPrice = data.first().closingPrice
    else:
        temp = StockData.objects.filter(stockId=code).order_by('-timestamp').first()
        if temp is None:
            newPrice = 0
        else:
            newPrice = temp.closingPrice
    data = StockData.objects.filter(stockId=code, timestamp=yesterday)
    if data.exists():
        lastPrice = data.first().closingPrice
    else:
        lastPrice = newPrice
    delta = newPrice - lastPrice
    if newPrice == 0:
        deltaRate = 0
    else:
        deltaRate = delta / lastPrice
    delta = "{:.2f}".format(delta)
    deltaRate = deltaRate * 100
    deltaRate = "{:.2f}".format(deltaRate)
    json = {'name': name, 'code': code, 'newPrice': newPrice,
            'delta': delta, 'deltaRate': deltaRate}
    return json


def req_favor(request, user_id):
    current_time = int(time.time())
    current_time = (current_time // 3600) * 3600  # 小时对齐
    today = (current_time // 86400) * 86400
    close_time = today + 9 * 3600  # 设定每天17点闭市
    if current_time > close_time:
        current_time = close_time
    save_data(current_time)
    data = FavorOfUser.objects.filter(userId=user_id)
    executor = ThreadPoolExecutor(max_workers=32)  # 设置最大线程数
    futures = [executor.submit(get_data, i) for i in data]
    executor.shutdown(wait=True)
    json_data = []
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        json_data.append(result)
    return JsonResponse(json_data, safe=False)


def add_favor(request):
    user_id = request.POST.get('userId')
    stock_id = request.POST.get('stockId')
    if not FavorOfUser.objects.filter(userId_id=user_id, stockId=stock_id).exists():
        new_favor = FavorOfUser(userId_id=user_id, stockId=stock_id)
        new_favor.save()
        return JsonResponse({"success": True, "message": "添加成功"})
    else:
        return JsonResponse({"success": False, "message": "添加失败，已添加过"})


def charge(request):
    user_id = request.POST.get('userId')
    money = float(request.POST.get('money'))
    user = User.objects.get(id=user_id)
    user.balance = user.balance + money
    user.save()
    return JsonResponse({"success": True, "message": "充值成功"})


def withdraw(request):
    user_id = request.POST.get('userId')
    money = float(request.POST.get('money'))
    user = User.objects.get(id=user_id)
    user.balance = user.balance - money
    if user.balance < 0:
        return JsonResponse({"success": False, "message": "余额不足，无法提现"})
    user.save()
    return JsonResponse({"success": True, "message": "提现成功"})


def req_balance(request, user_id):
    update_hold(user_id)
    balance = User.objects.get(id=user_id).balance
    return JsonResponse({"balance": balance})


def upload_photo(request):
    user_id = request.POST.get('userId')
    photo = request.FILES['photo']
    if Images.objects.filter(userId_id=user_id).exists():
        new_image = Images.objects.get(userId_id=user_id)
        new_image.image = photo
        new_image.save()
    else:
        new_image = Images(userId_id=user_id, image=photo)
        new_image.save()
    return JsonResponse({"success": True, "message": "头像上传成功"})


def req_photo(request):
    user_id = request.POST.get('userId')
    if Images.objects.filter(userId_id=user_id).exists():
        photo = Images.objects.get(userId_id=user_id)
        image_url = request.build_absolute_uri(photo.image.url)
        return JsonResponse({"success": True, "image_url": image_url})
    else:
        image_url = 'http://127.0.0.1:8000/media/images/hutao.jpg'
        return JsonResponse({"success": True, "image_url": image_url})


def delete_favor(request):
    user_id = request.POST.get('userId')
    stock_id = request.POST.get('stockId')
    try:
        favor = FavorOfUser.objects.get(userId_id=user_id, stockId=stock_id)
        favor.delete()
        return JsonResponse({"success": True, "message": "自选已移除"})
    except FavorOfUser.DoesNotExist:
        return JsonResponse({"success": False, "message": "无此自选"})
