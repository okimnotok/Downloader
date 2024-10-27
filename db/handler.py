from db.cyberdb.client import db_client


class DBBase:

    @staticmethod
    def retrieve_pk_value(value, keys):
        keys = keys.split(".")
        for key in keys:
            value = value.get(key, {})
        return value

    def save(self):
        if not getattr(self, "Meta") or not self.Meta.table_name or not self.Meta.pk:
            raise ValueError("请定义Meta，并提供table_name和pk信息")
        if not type(self).__base__.__name__ == "BaseModel":
            raise ValueError("类型需要按照顺序继承(BaseModel, DBBase)")
        table_name, pk = self.Meta.table_name, self.Meta.pk
        data = self.to_original_dict()
        db_client.save(table_name, DBBase.retrieve_pk_value(data, pk), data)

    def delete(self):
        if not getattr(self, "Meta") or not self.Meta.table_name or not self.Meta.pk:
            raise ValueError("请定义Meta，并提供table_name和pk信息")
        if not type(self).__base__.__name__ == "BaseModel":
            raise ValueError("类型需要按照顺序继承(BaseModel, DBBase)")
        table_name, pk = self.Meta.table_name, self.Meta.pk
        data = self.to_original_dict()
        db_client.delete(table_name, DBBase.retrieve_pk_value(data, pk))
        self.__dict__ = {}

    @classmethod
    def get(cls, pk):
        if not getattr(cls, "Meta") or not cls.Meta.table_name or not cls.Meta.pk:
            raise ValueError("请定义Meta，并提供table_name和pk信息")
        if not cls.__base__.__name__ == "BaseModel":
            raise ValueError("类型需要按照顺序继承(BaseModel, DBBase)")
        table_name = cls.Meta.table_name
        data = db_client.get(table_name, pk)
        return cls(**data)
