import asyncio
import concurrent.futures
import json
import re
import requests
import time
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count
from typing import Optional

import execjs
from bs4 import BeautifulSoup

from client.base import Base
from model.xhs.commons import SearchSort, NoteType
from model.xhs.elements import User, Comment
from model.xhs.entities import XHSSearchItem, XHSDetailedItem


class XHSClient(Base):
    def __init__(self, cookie: str):
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "cache-control": "no-cache",
            "content-type": "application/json;charset=UTF-8",
            "dnt": "1",
            "origin": "https://www.xiaohongshu.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://www.xiaohongshu.com/",
            "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "macOS",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        }
        super().__init__()
        self.api_prefix = "https://edith.xiaohongshu.com"
        self.xhs_sign_obj = execjs.compile(open("../lib/js/xhs.js", encoding="utf-8").read())
        self.cookie = cookie

    def _sign_request(self, uri: str, params: Optional[dict], headers: dict, need_sign: bool):
        if need_sign:
            return self.xhs_sign_obj.call("sign", uri, params, headers.get("cookie", ""))
        return {}

    def _post(self, uri: str, params: dict, headers: dict, need_sign: bool = True):
        url = f"{self.api_prefix}{uri}"
        headers.update(self.headers)
        headers.update(self._sign_request(uri, params, headers, need_sign))
        body = json.dumps(params, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        response = requests.post(url, data=body, headers=headers)
        response.raise_for_status()
        return response.json()

    def _get(self, uri: str, params: dict, headers: dict, need_sign: bool = True):
        if params.get("image_formats", None):
            params["image_formats"] = ",".join(params["image_formats"])
        params_str = "&".join(f"{k}={v}" for k, v in params.items())
        uri = f"{uri}?{params_str}"
        url = f"{self.api_prefix}{uri}"
        headers.update((self._sign_request(uri, None, headers, need_sign)))
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def _search_xhs(self, keyword: str, page: int, page_size: int, sort: SearchSort, note_type: NoteType):
        headers = {
            "cookie": self.cookie
        }
        params = {
            "ext_flags": [],
            "image_formats": ["jpg", "webp", "avif"],
            "keyword": keyword,
            "note_type": note_type.value,
            "sort": sort.value,
            "page": page,
            "page_size": page_size,
            "search_id": self.xhs_sign_obj.call("searchId"),
        }
        response = self._post("/api/sns/web/v1/search/notes", params=params, headers=headers, need_sign=True)
        if response.get("code") == 0:
            return response.get("data").get("items")
        else:
            print(response.get("msg"))
            return []

    async def _xhs_search_items(
            self, keyword: str, offset: int, limit: int, page_size: int, sort: SearchSort, note_type: NoteType
    ):
        start_page = int(offset/page_size) + 1
        end_page = int((offset+limit-1)/page_size)+1
        futs = []
        with ThreadPoolExecutor(max_workers=min(end_page-start_page+1, cpu_count()*4)) as executor:
            futs.extend([
                executor.submit(self._search_xhs, keyword, page, page_size, sort, note_type)
                for page in range(start_page, end_page+1)
            ])
        results = []
        for future in concurrent.futures.as_completed(futs):
            results.extend(future.result())
        return results

    def search_items(
            self, keyword: str, offset: int = 0, limit: int = 100, page_size: int = 20,
            sort: SearchSort = SearchSort.GENERAL, search_type: NoteType = NoteType.GENERAL
    ):
        return asyncio.run(self._xhs_search_items(keyword, offset, limit, page_size, sort, search_type))

    def _retrieve_note(self, note_id):
        url = f"https://www.xiaohongshu.com/explore/{note_id}"
        headers = {"cookie": self.cookie}
        headers.update(self.headers)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            pattern = re.compile("window\\.__INITIAL_STATE__={.*}")
            text = soup.body.find(
                "script", string=pattern
            ).text.replace(
                "window.__INITIAL_STATE__=", ""
            ).replace(
                "undefined", '""'
            )
            target = json.loads(text)
            return target.get("note", {}).get("noteDetailMap", {}).get(note_id, {})
        except:
            return {}

    def _sub_comments(self, note_id: str, root_comment_id: str, cursor: str, limit: int):
        headers = {"cookie": self.cookie}
        sub_comments = []
        has_more = True
        while has_more and len(sub_comments) < limit:
            data = {
                "note_id": note_id,
                "root_comment_id": root_comment_id,
                "num": 10,
                "cursor": cursor,
                "image_formats": ["jpg", "webp", "avif"]
            }
            response = self._get("/api/sns/web/v2/comment/sub/page", params=data, headers=headers, need_sign=True)
            has_more = response.get("data", {}).get("has_more", False)
            cursor = response.get("data", {}).get("cursor", "")
            sub_comments.extend(response.get("data", {}).get("comments", []))
        return {"sub_comments": sub_comments}

    def _retrieve_sub_comments(self, comment: dict, limit: int):
        note_id = comment.pop("note_id")
        root_comment_id = comment.pop("id")
        cursor = comment.pop("sub_comment_cursor")
        limit = min(int(comment.pop("sub_comment_count")), limit)
        if comment.pop("sub_comment_has_more", False):
            return {**self._sub_comments(note_id, root_comment_id, cursor, limit)}
        return comment

    def _retrieve_comments(self, note_id: str, limit: int, sub_limit: int):
        headers = {"cookie": self.cookie}
        comments = []
        has_more = True
        cursor = ""
        while has_more and len(comments) < limit:
            data = {
                "note_id": note_id,
                "cursor": cursor,
                "top_comment_id": "",
                "image_formats": ["jpg", "webp", "avif"],
            }
            response = self._get("/api/sns/web/v2/comment/page", params=data, headers=headers, need_sign=True)
            has_more = response.get("data", {}).get("has_more", False)
            cursor = response.get("data", {}).get("cursor", "")
            comments.extend([
                self._retrieve_sub_comments(item, sub_limit)
                for item in response.get("data", {}).get("comments", [])
            ])
        return comments

    def _retrieve_xhs_note(self, note_id: str, limit: int, sub_limit: int):
        result = self._retrieve_note(note_id)
        result.update({"comments": self._retrieve_comments(note_id, limit, sub_limit)})
        print(result)
        a = XHSDetailedItem(**result)
        print(a)
        return a

    async def _retrieve_xhs_notes(self, note_ids: list, limit: int, sub_limit: int):
        futs = []
        with ThreadPoolExecutor(max_workers=min(len(note_ids), cpu_count()*4)) as executor:
            futs.extend([
                executor.submit(self._retrieve_xhs_note, note_id, limit, sub_limit)
                for note_id in note_ids
            ])
        results = []
        for future in concurrent.futures.as_completed(futs):
            results.append(future.result())
        return results

    def retrieve_detail_items(self, ids: list, limit: int = 100, sub_limit: int = 100):
        return asyncio.run(self._retrieve_xhs_notes(ids, limit, sub_limit))

    async def _retrieve_xhs_comments(self, note_ids: list, limit: int, sub_limit: int):
        futs = []
        with ThreadPoolExecutor(max_workers=min(len(note_ids), cpu_count()*4)) as executor:
            futs.extend([
                executor.submit(self._retrieve_comments, note_id, limit, sub_limit)
                for note_id in note_ids
            ])
        results = []
        for future in concurrent.futures.as_completed(futs):
            comments = future.result()
            if comments:
                for comment in comments:
                    results.append(Comment(**comment))
        return results

    def search_comments(self, ids: list, limit: int = 100, sub_limit: int = 100):
        return asyncio.run(self._retrieve_xhs_comments(ids, limit, sub_limit))

    def _search_user(self, user_id: str):
        headers = {"cookie": self.cookie}
        page = 1
        has_more = True
        while has_more:
            params = {
                "search_user_request": {
                    "keyword": user_id,
                    "search_id": self.xhs_sign_obj.call("searchId"),
                    "page": page,
                    "page_size": 15,
                    "biz_type": "web_search_user",
                    "request_id": f"{int(round(time.time()))}-{int(round(time.time()*1000))}"
                }
            }
            response = self._post("/api/sns/web/v1/search/usersearch", params=params, headers=headers, need_sign=True)
            if response.get("success", False):
                users = list(filter(lambda item: item.get("red_id")==user_id, response.get("data", {}).get("users")))
                if users:
                    return User(nickname=users[0].get("name"), user_id=users[0].get("id"))
                has_more = response.get("data", {}).get("has_more", True)
                page += 1
            else:
                return None
        return None

    async def _search_users(self, user_ids: list):
        futs = []
        with ThreadPoolExecutor(max_workers=min(len(user_ids), cpu_count()*4)) as executor:
            futs.append(
                executor.submit(self._search_user, user_id)
                for user_id in user_ids
            )
        results = []
        for future in concurrent.futures.as_completed(futs):
            element = future.result()
            if element:
                results.append(element)
        return results

    def search_users(self, user_ids: list):
        return asyncio.run(self._search_users(user_ids))


if __name__ == "__main__":
    cookie = "abRequestId=4d064806-0185-5529-ad15-bbfb23db6c7a; xsecappid=xhs-pc-web; a1=18ac71f625ddn75phy5ezo84uw6zq0y9q0102j1i230000260817; webId=c1d7af2bfe37831864c56a30ba6fc37a; gid=yY0SWyiKWyAWyY0SWyiKJ8Vy2ffIW2Uxv2duy3JlY47EK8q8uA8vjJ888JK8YyW8jJDyYW88; webBuild=4.35.0; websectiga=f47eda31ec99545da40c2f731f0630efd2b0959e1dd10d5fedac3dce0bd1e04d; sec_poison_id=24d810eb-4f9b-4bc6-885e-d94031f905e1; acw_tc=2bd638d416240bc60bb200ac41a4551c91d158a22696bb95b83a2c79685fc126; web_session=0400697ea1909a8470f86ef3da344b6c451cff; unread={%22ub%22:%2266ed58fa000000000c01be56%22%2C%22ue%22:%2266ee80030000000026033d26%22%2C%22uc%22:14}"
    xhs_client = XHSClient(cookie)
    '''
    result = xhs_client.search_items("演唱会")
    print(result)
    '''
    result = xhs_client.retrieve_detail_items(["66e6be0b00000000270004db"])
    print(result)