import re
import requests
from router.router import router
from services.redis import *
from fastapi import Response

# 一些常量
headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'cache-control': 'no-cache',
    'dnt': '1;',
    'origin': 'https://m.bilibili.com',
    'pragma': 'no-cache',
    'referer': 'https://m.bilibili.com/',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1'
}

cid_url = 'http://api.bilibili.com/x/player/pagelist'

video_api_url = 'http://api.bilibili.com/x/player/playurl'
video_api_parms = {
    'platform': 'html5',
    'type': 'mp4',
    'qn': '208',
    'high_quality': '1'
}


def GetBili(vid: str, p: int):
    global headers
    global video_api_url
    global video_api_parms

    match_av = re.match(r'av', vid, re.I)
    match_bv = re.match(r'bv', vid, re.I)

    vid = vid
    p = p
    cid_parms = {
        'bvid': f'{vid}',
        'aid': f'{vid[2:]}'
    }
    if match_bv is not None:
        del cid_parms['aid']
    if match_av is not None:
        del cid_parms['bvid']

    try:
        cid_json = requests.get(url=cid_url, params=cid_parms, headers=headers, timeout=5).json()
    except:
        return "(X_X) 服务器出错！"
    return_code = cid_json['code']
    if return_code == -404:
        return "(?_?) 视频不存在！"
    cid = cid_json['data'][p - 1]['cid']
    if match_av is not None:
        video_api_parms['avid'] = cid_parms['aid']
    if match_bv is not None:
        video_api_parms['bvid'] = vid
    video_api_parms['cid'] = cid
    url = requests.get(url=video_api_url, params=video_api_parms, headers=headers, timeout=5).json()
    url = url['data']['durl'][0]['url']
    return url


@router.get('/bili/{vid}')
async def bili_location(vid: str, p: int = 1):
    match_av = re.match(r'av', vid, re.I)
    match_bv = re.match(r'bv', vid, re.I)
    if vid is None:
        return '(?_?)请输入VID'
    if match_bv is None and match_av is None:
        return '(!_!) 输入视频号错误！'

    cache = await redis.get("bili" + f"{vid}" + f"?p={p}")

    if cache is not None:
        return Response(status_code=307,
                        headers={
                            "Location": cache,
                            "Content-Type": "video/mp4",
                            "Cache-Control": "no-cache",
                            "Referrer-Policy": "no-referrer",
                            "X-Cache-used": "Yes"})
    else:
        url = GetBili(vid, p)
        head = url[0:8]
        if head == 'https://':
            await redis.set("bili" + f"{vid}" + f"?p={p}", url, ex=900)
            return Response(status_code=307,
                            headers={
                                "Location": url,
                                "Content-Type": "video/mp4",
                                "Cache-Control": "no-cache",
                                "Referrer-Policy": "no-referrer"})
        else:
            return url
