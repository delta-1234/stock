import concurrent

from django.http import JsonResponse
from stockData.models import StockData, StockInfo, News
import json
import requests
from bs4 import BeautifulSoup
import re
import time
from concurrent.futures import ThreadPoolExecutor
from django.core.cache import cache


# Create your views here.

def fetch_url(url, timestamp):
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Connection': 'keep-alive',
        'Referer': 'http://quote.eastmoney.com/center/gridlist.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    }
    response = requests.get(
        url=url,
        headers=headers,
        verify=False,
    )
    response.encoding = 'utf-8'
    text = response.text.split("jQuery1124013411786844407758_1699630449403")[1].split("(")[1].split(");")[0]
    text = json.loads(text)
    today = (timestamp // 86400) * 86400
    new_stock_data = []
    for data in text['data']['diff']:
        code = str(data["f12"]).zfill(6)
        close = data['f2']
        volume = data['f5']
        high = data['f15']
        low = data['f16']
        opening = data['f17']
        if not type(close) in [int, float]:
            continue
        if not type(volume) in [int, float]:
            continue
        if not type(high) in [int, float]:
            continue
        if not type(low) in [int, float]:
            continue
        if not type(opening) in [int, float]:
            continue
        temp = StockData.objects.filter(stockId=code, timestamp__range=(today, timestamp + 1))
        for j in temp:
            j.delete()
        new_stock_data.append(StockData(stockId=code, tradingVolume=volume, highestPrice=high, lowestPrice=low,
                                        openingPrice=opening, closingPrice=close, timestamp=timestamp))
    return new_stock_data


def save_data(timestamp):
    if StockData.objects.filter(stockId='000000', timestamp=timestamp).exists():
        return  # 已有数据无需再爬取
    urls = []
    for i in range(1, 149):
        url = 'http://72.push2.eastmoney.com/api/qt/clist/get?cb=jQuery1124013411786844407758_1699630449403&'
        url += 'pn=' + str(i)
        url += '&pz=20&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&wbp2u=|0|0|0|web&fid=f3&fs=m:0+t:6,m:0+t:80&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152&_='
        url += str(timestamp)
        urls.append(url)
    executor = ThreadPoolExecutor(max_workers=32)  # 设置最大线程数
    futures = [executor.submit(fetch_url, i, timestamp) for i in urls]
    # 关闭线程池
    executor.shutdown(wait=True)
    # 获取任务的返回值
    results = []
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        if len(result) != 0:
            results.extend(result)
    # 标记数据，无实际用途
    new_stock_data = StockData(stockId='000000', tradingVolume=0, highestPrice=0, lowestPrice=0,
                               openingPrice=0, closingPrice=0, timestamp=timestamp)
    results.append(new_stock_data)
    StockData.objects.bulk_create(results)


def req_kline(request, stock_id):
    current_time = int(time.time())
    current_time = (current_time // 3600) * 3600  # 小时对齐
    today = (current_time // 86400) * 86400  # 考虑到时差，北京时间其实为8点
    close_time = today + 9 * 3600  # 设定每天17点闭市
    if current_time > close_time:
        current_time = close_time
    # 先更新数据
    save_data(current_time)
    json_data = []
    stock_data = StockData.objects.filter(stockId=stock_id)
    for data in stock_data:
        json_data.append({"close": data.closingPrice, "high": data.highestPrice,
                          "low": data.lowestPrice, "open": data.openingPrice,
                          "timestamp": data.timestamp, "volume": data.tradingVolume})
    return JsonResponse(json_data, safe=False)


def get_brief(stock_id):
    if StockInfo.objects.filter(stockId=stock_id).exists():
        return None  # 已拥有数据不爬取
    if stock_id == 0:
        return None
    url = 'https://www.futunn.com/stock/'
    url += str(stock_id)
    url += '-SZ/'
    try:
        response = requests.get(url=url, timeout=10)
    except (requests.Timeout, requests.HTTPError) as e:
        return None  # 没有找到相关信息
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    temp = soup.prettify()
    pattern = r'\{\"companyProfile.*filedType\":2\}\]\}'  # 匹配邮箱地址的正则表达式
    temp = re.findall(pattern, temp)
    if len(temp) == 0:
        return None
    temp = temp[0]
    pattern = r'\{\"name.*filedType\":2'
    temp = re.findall(pattern, temp)
    temp = (temp[0]).split('},')
    info = ""
    stock_name = ""
    company_name = ""
    for j in temp:
        j += '}'
        js = json.loads(j)
        if js['name'] == '公司简介':
            info = js['value']
        elif js['name'] == 'A股证券简称':
            stock_name = js['value']
        elif js['name'] == '公司名称':
            company_name = js['value']
    if len(info) > 200:
        temp = ""
        for i in info.split('。'):
            temp += i
            if len(temp) > 200:
                break
        info = temp
    new_stockInfo = StockInfo(stockId=stock_id, stockName=stock_name,
                              companyName=company_name, information=info)
    return new_stockInfo


def req_brief(request, stock_id):
    if not StockInfo.objects.filter(stockId=0).exists():
        values_set = set(StockData.objects.values_list('stockId', flat=True))
        executor = ThreadPoolExecutor(max_workers=32)  # 设置最大线程数

        futures = [executor.submit(get_brief, i) for i in values_set]
        executor.shutdown(wait=True)
        # 获取任务的返回值
        results = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)
        print(results)
        StockInfo.objects.bulk_create(results)
        # 标记数据
        new_stockInfo = StockInfo(stockId=0, stockName='', companyName='', information='')
        new_stockInfo.save()
    stock_info = StockInfo.objects.get(stockId=stock_id)
    return JsonResponse({"introduce": stock_info.information, "companyName": stock_info.companyName})


def extract_between_strings(input_string, start_string, end_string):
    start_pattern = re.escape(start_string)
    end_pattern = re.escape(end_string)
    try:
        start_index = re.search(start_pattern, input_string).end()
        end_index = re.search(end_pattern, input_string).start()
    except:
        return ""

    if start_index == -1 or end_index == -1 or start_index >= end_index:
        return ""

    extracted_string = input_string[start_index:end_index]
    return extracted_string


def get_news(url):
    today = (int(time.time()) // 86400) * 86400
    response = requests.get(url=url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    soup = soup.prettify()
    pattern = r'<div class="title">.*?</div>'
    temp = re.findall(pattern, soup, flags=re.DOTALL)
    temp = temp[0]
    start_string = '<div class="title">'
    end_string = '</div>'
    temp = extract_between_strings(temp, start_string, end_string)
    title = temp.replace(" ", "").replace("\n", "")  # 获得新闻标题
    pattern = r'<div class="abstract">.*?<div class="keywords">'
    temp = re.findall(pattern, soup, flags=re.DOTALL)
    if len(temp) > 0:
        temp = temp[0]
        pattern = r'<div class="txt">.*?</div>'
        temp = re.findall(pattern, temp, flags=re.DOTALL)[0]
        start_string = '<div class="txt">'
        end_string = '</div>'
        temp = extract_between_strings(temp, start_string, end_string)
        brief = temp.replace(" ", "").replace("\n", "")  # 获取到摘要
    else:
        brief = ""
    new_news = News(title=title, link=url, timestamp=today, brief=brief)
    return new_news


def req_news(request):
    today = (int(time.time()) // 86400) * 86400
    if not News.objects.filter(timestamp=today).exists():
        url = 'https://www.eastmoney.com/'
        response = requests.get(url=url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        temp = soup.prettify()
        start_string = '<div tracker-eventcode="dfcfwsy_sp_cjdd1_bgl">'
        end_string = '<div tracker-eventcode="dfcfwsy_sp_cjdd2_bgl">'
        temp = extract_between_strings(temp, start_string, end_string)
        pattern = r'<a href=".*?">'
        temp = re.findall(pattern, temp)
        start_string = '<a href="'
        end_string = '">'
        pattern = r'https://finance\.eastmoney\.com/a.*'
        urls = []
        # 获得新闻列表
        for i in temp:
            string = extract_between_strings(i, start_string, end_string)
            if re.match(pattern, string):
                urls.append(string)
        # 爬取单个新闻
        executor = ThreadPoolExecutor(max_workers=16)  # 设置最大线程数

        futures = [executor.submit(get_news, url) for url in urls]
        executor.shutdown(wait=True)
        # 获取任务的返回值
        results = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)
        News.objects.bulk_create(results)

    json_data = []
    for i in News.objects.filter(timestamp=today):
        json_data.append({
            "title": i.title,
            "brief": i.brief,
            "link": i.link
        })
    return JsonResponse(json_data, safe=False)


def req_best_k(request, k):
    current_time = int(time.time())
    url = 'http://72.push2.eastmoney.com/api/qt/clist/get?cb=jQuery1124013411786844407758_1699630449403&'
    url += 'pn=' + str(1)
    url += '&pz=20&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&wbp2u=|0|0|0|web&fid=f3&fs=m:0+t:6,m:0+t:80&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152&_='
    url += str(current_time)
    response = requests.get(
        url=url,
        verify=False,
    )
    response.encoding = 'utf-8'
    text = response.text.split("jQuery1124013411786844407758_1699630449403")[1].split("(")[1].split(");")[0]
    text = json.loads(text)
    i = 0
    json_data = []
    k = int(k)
    for data in text['data']['diff']:
        if i >= k:
            break
        if not StockInfo.objects.filter(stockId=data['f12']).exists():
            continue
        json_data.append({
            'name': data['f14'],
            'code': data['f12'],
            'deltaRate': data['f3']
        })
        i = i + 1
    return JsonResponse(json_data, safe=False)


def get_new_data(i, stock_list, current_time, yesterday):
    data = StockData.objects.filter(stockId=stock_list[i].stockId, timestamp=current_time)
    if data.exists():
        name = stock_list[i].stockName
        code = stock_list[i].stockId
        data = data.first()
        newPrice = data.closingPrice
        high = data.highestPrice
        low = data.lowestPrice
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
        deltaRate = deltaRate * 100
        deltaRate = "{:.2f}".format(deltaRate)
        json = {'stockName': name, 'stockId': code, 'newPrice': newPrice,
                'high': high, "low": low, 'deltaRate': deltaRate}
    else:
        json = {'stockName': None, 'stockId': None, 'newPrice': None,
                'high': None, "low": None, 'deltaRate': None}
    return json


def show_stock(request):
    page = int(request.POST.get('page'))
    num = int(request.POST.get('numInPage'))
    cached_data = cache.get('key' + str(page) + '_' + str(num))
    if cached_data is not None:
        return JsonResponse(cached_data, safe=False)
    current_time = int(time.time())
    current_time = (current_time // 3600) * 3600  # 小时对齐
    today = (current_time // 86400) * 86400
    close_time = today + 9 * 3600  # 设定每天17点闭市
    yesterday = close_time - 86400
    if current_time > close_time:
        current_time = close_time
    save_data(current_time)
    stock_list = StockInfo.objects.order_by('stockId')
    begin = (num - 1) * page
    executor = ThreadPoolExecutor(max_workers=32)  # 设置最大线程数
    futures = [executor.submit(get_new_data, i, stock_list, current_time, yesterday) for i in range(begin, begin + num)]
    executor.shutdown(wait=True)
    json_data = []
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        json_data.append(result)
    cache.set('key' + str(page) + '_' + str(num), json_data, 60 * 15)
    return JsonResponse(json_data, safe=False)
