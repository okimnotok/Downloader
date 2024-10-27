import cyberdb

from db.base import Base


client = cyberdb.connect(
    host="127.0.0.1",
    port=10000,
    password="1234567890",
    encrypt=True,
    time_out=900
)


class CyberDB(Base):
    def save(self, table_name, pk, data):
        proxy = client.get_proxy()
        proxy.connect()
        try:
            table = proxy.get_cyberdict(table_name)
        except:
            proxy.create_cyberdict(table_name)
            table = proxy.get_cyberdict(table_name)
        table[pk] = data
        proxy.close()

    def delete(self, table_name, pk):
        proxy = client.get_proxy()
        proxy.connect()
        try:
            table = proxy.get_cyberdict(table_name)
            del table[pk]
        except:
            pass
        proxy.close()

    def get(self, table_name, pk):
        proxy = client.get_proxy()
        proxy.connect()
        try:
            table = proxy.get_cyberdict(table_name)
            proxy.close()
            return table[pk]
        except:
            proxy.close()
            raise KeyError(f"{table_name} or {pk} does not exist")


db_client = CyberDB()
