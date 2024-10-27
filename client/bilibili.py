import base64
import json
import random
import time
from hashlib import md5
from urllib.parse import urlencode

import requests


class BilibiliClient:
    def __init__(self):
        self.headers = {
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,zh-TW;q=0.6",
            "authority": "api.client.com",
            "cache-control": "max-age=0",
            "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "macOS",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-size": "none",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/127.0.0.0 Safari/537.36",
        }
        self.update_cookie()

    def update_cookie(self):
        self.headers["cookie"] = "a9a421bb%2C1740663473%2C5a208%2A81CjDVnnSPTduS8x1ubA97dAD_Y8w9lypQPbsqLpSnGDoitLnEflqoYVRHhIz2HSnBt64SVldkaXFmenpGQWo5ZjBFN1gyS244S3picUdaaXh3RGVMRjl5SnlVZU94NUhsenBkdzJWajB1WmZ6OFJPSTB3TWZyei05bWxzRVJjelhPUVJiMXdCV2NBIIEC"
        '''
        with open("/Users/yifu/PycharmProjects/bilibili_cookie.txt", "r") as f:
            self.headers["cookie"] = f.read()
        '''

    @staticmethod
    def base64_encode(words: str, encode="utf-8"):
        return base64.b64encode(words.encode(encode)).decode().strip("=")

    @staticmethod
    def get_dm_cover_img_str(num=640):
        num = random.randrange(360, 651)
        imagine_word = f"ANGEL (Intel Inc., Intel(R) Iris(TM) Plus Graphics {num}, OpenGL 4.1)Google Inc. (Intel Inc.)"
        return BilibiliClient.base64_encode(imagine_word)

    @staticmethod
    def md5_use(text: str):
        return md5(bytes(text, encoding="utf-8")).hexdigest()

    @staticmethod
    def extract_search_response(search_json: dict):
        v_list = search_json.get("data", {}).get("list", {}).get("vlist", [])
        page = search_json.get("data", {}).get("page", {})
        has_more = page.get("pn") * page.get("ps") <= page.get("count")
        vids = []
        for item in v_list:
            vids.append({
                "vid": item.get("vid", ""),
                "created": item.get("created", 0)
            })
        return vids, has_more

    def _get(self, url, timeout=20, **kwargs):
        try:
            res = requests.get(url, timeout=timeout, **kwargs)
            res.raise_for_status()
        except Exception as e:
            print(e)
            raise ConnectionError
        if "风险校验失败" in res.text:
            self.update_cookie()
            raise ConnectionRefusedError
        return res

    def _retrieve_bilibili_cookie(self):
        return self._get(url="https://space.bilibili.com", headers=self.headers)

    def _search_bilibili(self, params, cookies, headers):
        return self._get(
            url="https://api.bilibili.com/x/space/wbi/arc/search",
            params=params,
            cookies=cookies,
            headers=headers,
            proxies={},
            timeout=15
        ).json()

    def _get_video_ids(self, user_id, keyword, page, size=50):
        params = {
            "dm_cover_img_str": BilibiliClient.get_dm_cover_img_str(),
            "dm_img_list": [],
            "keyword": keyword,
            "mid": user_id,
            "order": "pubdate",
            "order_avoided": "true",
            "platform": "web",
            "pn": page,
            "ps": size,
            "tid": "0",
            "web_location": "1550101",
            "wts": str(int(time.time()))
        }
        response = self._retrieve_bilibili_cookie()
        print("!!!!!!!!!!!!!!!!!!!!! cookie", response.cookies)
        params["w_rid"] = BilibiliClient.md5_use(urlencode(params) + "ea1db124af3c7062474693fa704f4ff8")
        return self._search_bilibili(
            params=params,
            cookies=dict(response.cookies),
            headers={**self.headers, "refer": "https://www.bilibili.com/"}
        )

    def get_all_video_ids(self, user_id=None, keyword=None):
        has_more = True
        page = 0
        vids = []
        while has_more:
            try:
                response = self._get_video_ids(user_id, keyword, page)
                t_vids, has_mode = BilibiliClient.extract_search_response(response)
                vids.extend(t_vids)
                page += 1
            except Exception as e:
                return vids
            page += 1
        return vids


if __name__ == '__main__':
    bilibili_client = BilibiliClient()
    response = bilibili_client.get_all_video_ids(user_id="16022714")
    print(response)
