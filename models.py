from sqlalchemy import Column, Integer, String
from database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    table_id = Column(Integer)
    customer_name = Column(String)
    customer_phone = Column(String)
    item = Column(String)
    status = Column(String)