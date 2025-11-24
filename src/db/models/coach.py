from sqlalchemy import Column, Integer, String, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from src.db.database import Base


class Coach(Base):
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    permissions = relationship(
        "UserPermission",
        foreign_keys="UserPermission.coach_id",
        back_populates="coach",
        cascade="all, delete-orphan",
    )
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="coach",
        cascade="all, delete-orphan",
    )
    batch_assignments = relationship(
        "CoachBatch",
        back_populates="coach",
        cascade="all, delete-orphan",
    )
    school_assignments = relationship(
        "CoachSchool",
        back_populates="coach",
        cascade="all, delete-orphan",
    )
    sessions = relationship("PhysicalAssessmentSession", back_populates="coach")

    batches = association_proxy("batch_assignments", "batch")
    schools = association_proxy("school_assignments", "school")

    def __repr__(self) -> str:
        return f"<Coach(id={self.id}, username='{self.username}')>"

    @property
    def password_hash(self) -> str:
        return self.password

    @password_hash.setter
    def password_hash(self, value: str) -> None:
        self.password = value

    @property
    def role(self) -> str:
        return "coach"

    @property
    def school_id(self) -> int | None:
        assignment = self.school_assignments[0] if self.school_assignments else None
        return assignment.school_id if assignment else None
