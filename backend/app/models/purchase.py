from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(32), unique=True, nullable=False, index=True)
    status = Column(String(32), default="pending")  # pending, approved, confirmed, stocked_in, stocked_out, delivering, completed, rejected
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_reason = Column(String(256), nullable=True)
    destination = Column(String(200), default="")
    receiver_name = Column(String(50), default="")
    handoff_code = Column(String(64), default="")
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("PurchaseItem", back_populates="purchase")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False)
    goods_name = Column(String(128), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(32), default="")

    purchase = relationship("Purchase", back_populates="items")
