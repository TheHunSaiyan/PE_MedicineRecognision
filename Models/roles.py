from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    NURSE = "nurse"
    DOCTOR = "doctor"
    TECHNICIAN = "technician"