from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from ..database import Base


class IDSRulepackRuntimeState(Base):
    __tablename__ = "ids_rulepack_runtime_state"

    id = Column(Integer, primary_key=True, index=True)
    active_rulepack_key = Column(String(64), nullable=False, default="legacy-inline", index=True)
    updated_by = Column(String(64), default="")
    update_note = Column(Text, default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class IDSRulepackActivation(Base):
    __tablename__ = "ids_rulepack_activations"

    id = Column(Integer, primary_key=True, index=True)
    rulepack_key = Column(String(64), nullable=False, index=True)
    pack_version = Column(String(64), nullable=False, default="", index=True)
    trust_classification = Column(String(32), nullable=False, default="", index=True)
    detector_family = Column(String(32), nullable=False, default="", index=True)
    result_status = Column(String(32), nullable=False, default="activated", index=True)
    activation_detail = Column(Text, default="")
    triggered_by = Column(String(64), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
