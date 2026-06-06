from typing import Optional
from sqlalchemy.orm import Session
from app.modules.patients.models import Patient


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, patient_id: int) -> Optional[Patient]:
        return self.db.query(Patient).filter(Patient.id == patient_id).first()

    def get_by_user_id(self, user_id: int) -> Optional[Patient]:
        return self.db.query(Patient).filter(Patient.user_id == user_id).first()

    def create(self, **kwargs) -> Patient:
        patient = Patient(**kwargs)
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def update(self, patient: Patient, **kwargs) -> Patient:
        for k, v in kwargs.items():
            if v is not None:
                setattr(patient, k, v)
        self.db.commit()
        self.db.refresh(patient)
        return patient
