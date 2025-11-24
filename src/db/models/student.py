from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from src.db.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    age = Column(Integer, nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    batch = relationship("Batch", back_populates="students")
    physical_results = relationship("PhysicalAssessmentDetail", back_populates="student")

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, name='{self.name}')>"

    @property
    def school_id(self) -> int | None:
        return self.batch.school_id if self.batch else None

    @property
    def coach_id(self) -> int | None:
        # Legacy accessor: derive coach from current batch assignment if available
        return self.batch.coach_id if self.batch else None
