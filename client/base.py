class Base:
    def __init__(self):
        pass

    def search_items(self, keyword: str, offset: int, limit: int, page_size: int, sort, search_type):
        pass

    def retrieve_detail_items(self, ids: list, limit: int, sub_limit: int):
        pass

    def search_comments(self, ids: list, limit: int, sub_limit: int):
        pass

    def search_users(self, user_ids: list):
        pass
