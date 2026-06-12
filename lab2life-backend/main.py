from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Form,
    Depends,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from sqlalchemy import text
from pydantic import BaseModel, EmailStr

import pdfplumber
import os
import uuid
import json
import re

from groq import Groq
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
)

from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    relationship,
    Session,
)

from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta

import razorpay

# OCR
import cv2
import numpy as np
import pytesseract

# -------------------- LOAD ENV --------------------
load_dotenv()

# -------------------- FASTAPI --------------------
app = FastAPI()

# -------------------- CORS --------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://lab2life-frontendd.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- GROQ --------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found")

client = Groq(api_key=GROQ_API_KEY)

# -------------------- RAZORPAY --------------------
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    raise ValueError("Razorpay keys missing")

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)

# -------------------- SECURITY --------------------
SECRET_KEY = os.getenv("SECRET_KEY", "lab2life-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12

pwd_context = CryptContext(
    schemes=["bcrypt_sha256"],
    deprecated="auto",
)

security = HTTPBearer(auto_error=False)

# -------------------- DATABASE --------------------
DATABASE_URL = "sqlite:///./lab2life.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

# -------------------- UPLOADS --------------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------- TESSERACT PATH --------------------
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# -------------------- LANGUAGE MAP --------------------
LANGUAGE_MAP = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "ta": "Tamil",
    "bn": "Bengali",
    "gu": "Gujarati",
    "te": "Telugu",
    "fr": "French",
    "es": "Spanish",
    "ar": "Arabic",
}

# =========================================================
# DATABASE MODELS
# =========================================================

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)

    phone = Column(String(10), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)

    password_hash = Column(String(255), nullable=False)

    is_subscribed = Column(String(10), default="false")

    reports = relationship("Report", back_populates="patient")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(100), nullable=False)

    email = Column(String(100), unique=True, nullable=False)

    password_hash = Column(String(255), nullable=False)

    specialization = Column(String(100), nullable=False)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False,
    )

    file_name = Column(String(255), nullable=False)

    file_path = Column(String(255), nullable=False)

    language = Column(String(20), nullable=False)

    summary = Column(Text, nullable=True)

    health_score = Column(Integer, nullable=True)

    risk_level = Column(String(100), nullable=True)

    normal_factors = Column(Text, nullable=True)

    abnormal_factors = Column(Text, nullable=True)

    recommendations = Column(Text, nullable=True)

    doctor_advice = Column(Text, nullable=True)

    # doctor verification
    verification_status = Column(
        String(20),
        default="Pending",
    )

    doctor_corrected_summary = Column(
        Text,
        nullable=True,
    )

    verified_by_doctor = Column(
        String(100),
        nullable=True,
    )
    verification_status = Column(String(50), default="Pending")

    verified_by_doctor = Column(String(100), nullable=True)
    is_verified = Column(String(10), default="false")
    doctor_updated_summary = Column(Text, nullable=True)
    patient = relationship("Patient", back_populates="reports")


# CREATE TABLES
from sqlalchemy import inspect

inspector = inspect(engine)

columns = [
    column["name"]
    for column in inspector.get_columns("reports")
]

with engine.connect() as conn:

    if "is_verified" not in columns:
        conn.execute(
            text(
                "ALTER TABLE reports ADD COLUMN is_verified VARCHAR(10) DEFAULT 'false'"
            )
        )

    if "doctor_updated_summary" not in columns:
        conn.execute(
            text(
                "ALTER TABLE reports ADD COLUMN doctor_updated_summary TEXT"
            )
        )

    conn.commit()
Base.metadata.create_all(bind=engine)

# =========================================================
# REQUEST MODELS
# =========================================================

class AskDoctorRequest(BaseModel):
    question: str
    summary: str
    language: str = "en"


class RegisterRequest(BaseModel):
    full_name: str
    age: int
    gender: str
    phone: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DoctorRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    specialization: str


class CreateSubscriptionOrderRequest(BaseModel):
    plan: str


class VerifyReportRequest(BaseModel):
    summary: str
    recommendations: list[str]
    doctor_advice: str


# =========================================================
# DATABASE HELPERS
# =========================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
):
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        hours=ACCESS_TOKEN_EXPIRE_HOURS
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

# =========================================================
# AUTH HELPERS
# =========================================================

def get_current_patient(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        patient_id = payload.get("sub")
        role = payload.get("role", "patient")

        if role != "patient":
            raise HTTPException(
                status_code=401,
                detail="Invalid patient token",
            )

        patient = (
            db.query(Patient)
            .filter(Patient.id == int(patient_id))
            .first()
        )

        if not patient:
            raise HTTPException(
                status_code=401,
                detail="Patient not found",
            )

        return patient

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )


def get_current_patient_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials:
        return None

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        role = payload.get("role", "patient")

        if role != "patient":
            return None

        patient_id = payload.get("sub")

        return (
            db.query(Patient)
            .filter(Patient.id == int(patient_id))
            .first()
        )

    except:
        return None


def get_current_doctor(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Doctor login required",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        role = payload.get("role")

        if role != "doctor":
            raise HTTPException(
                status_code=401,
                detail="Invalid doctor token",
            )

        doctor_id = payload.get("sub")

        doctor = (
            db.query(Doctor)
            .filter(Doctor.id == int(doctor_id))
            .first()
        )

        if not doctor:
            raise HTTPException(
                status_code=401,
                detail="Doctor not found",
            )

        return doctor

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

# =========================================================
# OCR HELPERS
# =========================================================

def extract_text_from_pdf(file_path: str):
    text = ""

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

    return text.strip()


def extract_text_from_image(file_path: str):
    try:
        img = cv2.imread(file_path)

        if img is None:
            return ""

        # resize
        img = cv2.resize(
            img,
            None,
            fx=2,
            fy=2,
            interpolation=cv2.INTER_CUBIC,
        )

        # grayscale
        gray = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2GRAY,
        )

        # denoise
        gray = cv2.fastNlMeansDenoising(
            gray,
            None,
            30,
            7,
            21,
        )

        # threshold
        thresh = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )

        # morphology
        kernel = np.ones((1, 1), np.uint8)

        thresh = cv2.morphologyEx(
            thresh,
            cv2.MORPH_CLOSE,
            kernel,
        )

        custom_config = r'--oem 3 --psm 6'

        text = pytesseract.image_to_string(
            thresh,
            config=custom_config,
        )

        return text.strip()

    except Exception as e:
        print("OCR Error:", e)
        return ""

# =========================================================
# JSON HELPER
# =========================================================

def extract_json_from_response(content: str):
    try:
        return json.loads(content)

    except json.JSONDecodeError:
        match = re.search(
            r"\{.*\}",
            content,
            re.DOTALL,
        )

        if match:
            return json.loads(match.group(0))

        raise ValueError("Invalid JSON")

# =========================================================
# AI ANALYSIS
# =========================================================

def generate_report_analysis(
    text: str,
    target_lang: str = "en",
):
    language_name = LANGUAGE_MAP.get(
        target_lang,
        "English",
    )

    prompt = f"""
Analyze this medical report.

Return ONLY VALID JSON.

Language: {language_name}

JSON format:
{{
    "summary": "",
    "health_score": 80,
    "risk_level": "",
    "normal_factors": [],
    "abnormal_factors": [],
    "recommendations": [],
    "doctor_advice": ""
}}

Medical Report:
{text}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.3,
        )

        content = (
            response
            .choices[0]
            .message.content
            .strip()
        )

        parsed = extract_json_from_response(content)

        return {
            "summary": parsed.get("summary", ""),
            "health_score": int(
                parsed.get("health_score", 0)
            ),
            "risk_level": parsed.get(
                "risk_level",
                "",
            ),
            "normal_factors": parsed.get(
                "normal_factors",
                [],
            ),
            "abnormal_factors": parsed.get(
                "abnormal_factors",
                [],
            ),
            "recommendations": parsed.get(
                "recommendations",
                [],
            ),
            "doctor_advice": parsed.get(
                "doctor_advice",
                "",
            ),
        }

    except Exception as e:
        print("AI Error:", e)

        return {
            "summary": f"Analysis failed: {str(e)}",
            "health_score": 0,
            "risk_level": "Unknown",
            "normal_factors": [],
            "abnormal_factors": [],
            "recommendations": [],
            "doctor_advice": "",
        }


def generate_doctor_answer(
    question: str,
    summary: str,
    language: str = "en",
):
    language_name = LANGUAGE_MAP.get(
        language,
        "English",
    )

    prompt = f"""
Answer in {language_name}.

Summary:
{summary}

Question:
{question}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Medical assistant",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.4,
        )

        return (
            response
            .choices[0]
            .message.content
            .strip()
        )

    except Exception as e:
        return str(e)

# =========================================================
# AUTH ROUTES
# =========================================================

@app.post("/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Patient)
        .filter(Patient.email == data.email)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already exists",
        )

    patient = Patient(
        full_name=data.full_name,
        age=data.age,
        gender=data.gender,
        phone=data.phone,
        email=data.email,
        password_hash=hash_password(data.password),
    )

    db.add(patient)
    db.commit()

    return {
        "message": "Patient registered successfully"
    }


@app.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    patient = (
        db.query(Patient)
        .filter(Patient.email == data.email)
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    if not verify_password(
        data.password,
        patient.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    token = create_access_token({
        "sub": str(patient.id),
        "role": "patient",
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "full_name": patient.full_name,
        "is_subscribed": patient.is_subscribed,
    }


@app.post("/doctor-register")
def doctor_register(
    data: DoctorRegisterRequest,
    db: Session = Depends(get_db),
):

    # ✅ Check existing email
    existing_doctor = (
        db.query(Doctor)
        .filter(Doctor.email == data.email)
        .first()
    )

    if existing_doctor:
        raise HTTPException(
            status_code=400,
            detail="Doctor email already registered"
        )

    # ✅ Password validation
    if len(data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    # ✅ Create doctor
    doctor = Doctor(
        full_name=data.full_name.strip(),
        email=data.email,
        password_hash=hash_password(data.password),
        specialization=data.specialization.strip(),
    )

    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    return {
        "message": "Doctor registered successfully"
    }
@app.post("/doctor-login")
def doctor_login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    doctor = (
        db.query(Doctor)
        .filter(Doctor.email == data.email)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    if not verify_password(
        data.password,
        doctor.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    token = create_access_token({
        "sub": str(doctor.id),
        "role": "doctor",
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "doctor_name": doctor.full_name,
    }

# =========================================================
# PAYMENT
# =========================================================

@app.post("/create-subscription-order")
def create_subscription_order(
    data: CreateSubscriptionOrderRequest,
    current_patient: Patient = Depends(get_current_patient),
):
    amount = 19900

    order_data = {
        "amount": amount,
        "currency": "INR",
        "receipt": f"sub_{uuid.uuid4().hex[:6]}",
    }

    order = razorpay_client.order.create(
        data=order_data
    )

    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key": RAZORPAY_KEY_ID,
    }


@app.post("/verify-payment")
def verify_payment(
    payment_data: dict,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": payment_data.get(
                "razorpay_order_id"
            ),
            "razorpay_payment_id": payment_data.get(
                "razorpay_payment_id"
            ),
            "razorpay_signature": payment_data.get(
                "razorpay_signature"
            ),
        })

        current_patient.is_subscribed = "true"

        db.commit()

        return {
            "message": "Subscription activated"
        }

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Payment verification failed",
        )

# =========================================================
# UPLOAD REPORT
# =========================================================

@app.post("/upload-report")
async def upload_report(
    file: UploadFile = File(...),
    language: str = Form("en"),
    current_patient: Patient = Depends(
        get_current_patient_optional
    ),
    db: Session = Depends(get_db),
):
    file_path = None

    try:
        filename = file.filename.lower()

        if not (
            filename.endswith(".pdf")
            or filename.endswith(".jpg")
            or filename.endswith(".jpeg")
            or filename.endswith(".png")
        ):
            raise HTTPException(
                status_code=400,
                detail="Only PDF/JPG/PNG allowed",
            )

        unique_name = (
            f"{uuid.uuid4()}_{file.filename}"
        )

        file_path = os.path.join(
            UPLOAD_FOLDER,
            unique_name,
        )

        with open(file_path, "wb") as f:
            f.write(await file.read())

        # text extraction
        if filename.endswith(".pdf"):
            pdf_text = extract_text_from_pdf(file_path)
        else:
            pdf_text = extract_text_from_image(file_path)

        if not pdf_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text found",
            )

        analysis = generate_report_analysis(
            pdf_text,
            language,
        )

        # save only logged in users
        if current_patient:

            report = Report(
                patient_id=current_patient.id,
                file_name=file.filename,
                file_path=file_path,
                language=language,

                summary=analysis["summary"],

                health_score=analysis[
                    "health_score"
                ],

                risk_level=analysis[
                    "risk_level"
                ],

                normal_factors=json.dumps(
                    analysis["normal_factors"]
                ),

                abnormal_factors=json.dumps(
                    analysis["abnormal_factors"]
                ),

                recommendations=json.dumps(
                    analysis["recommendations"]
                ),

                doctor_advice=analysis[
                    "doctor_advice"
                ],

                verification_status="Pending",
            )

            db.add(report)
            db.commit()

        return analysis

    except Exception as e:
        print("Upload Error:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

# =========================================================
# ASK DOCTOR
# =========================================================

@app.post("/ask-doctor")
async def ask_doctor(
    data: AskDoctorRequest,
    current_patient: Patient = Depends(get_current_patient),
):
    answer = generate_doctor_answer(
        data.question,
        data.summary,
        data.language,
    )

    return {"answer": answer}

# =========================================================
# MY REPORTS
# =========================================================

@app.get("/my-reports")
def get_my_reports(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    reports = (
        db.query(Report)
        .filter(
            Report.patient_id == current_patient.id
        )
        .order_by(Report.id.desc())
        .all()
    )

    result = []

    for report in reports:
        result.append({
            "id": report.id,
            "file_name": report.file_name,
            "file_path": report.file_path,

            "summary": report.summary,

            "doctor_corrected_summary":
                report.doctor_corrected_summary,

            "verification_status":
                report.verification_status,

            "verified_by_doctor":
                report.verified_by_doctor,

            "health_score":
                report.health_score,

            "risk_level":
                report.risk_level,

            "normal_factors":
                json.loads(report.normal_factors)
                if report.normal_factors else [],

            "abnormal_factors":
                json.loads(report.abnormal_factors)
                if report.abnormal_factors else [],

            "recommendations":
                json.loads(report.recommendations)
                if report.recommendations else [],

            "doctor_advice":
                report.doctor_advice,

            "language":
                report.language,

            "verification_status": report.verification_status,
            "verified_by_doctor": report.verified_by_doctor,
        })

    return {"reports": result}
# -------------------- DOCTOR REPORTS --------------------

@app.get("/doctor/reports")
def get_doctor_reports(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):

    try:

        token = credentials.credentials

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        role = payload.get("role")

        if role != "doctor":
            raise HTTPException(
                status_code=403,
                detail="Doctor access required"
            )

    except:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    reports = (
        db.query(Report)
        .join(Patient)
        .filter(Patient.is_subscribed == "true")
        .order_by(Report.id.desc())
        .all()
    )

    result = []

    for report in reports:

        result.append({

            "id": report.id,

            "patient_name":
                report.patient.full_name,

            "file_name":
                report.file_name,

            "file_path":
                report.file_path,

            "summary":
                report.doctor_updated_summary
                if report.doctor_updated_summary
                else report.summary,

            "health_score":
                report.health_score,

            "risk_level":
                report.risk_level,

            "is_verified":
                report.is_verified == "true",

            "language":
                report.language,
        })

    return {
        "reports": result
    }

@app.put("/doctor/verify-report/{report_id}")
def verify_report(
    report_id: int,
    data: VerifyReportRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):

    report = (
        db.query(Report)
        .filter(Report.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    # ✅ Update report
    report.summary = data.summary

    report.recommendations = json.dumps(
        data.recommendations
    )

    report.doctor_advice = data.doctor_advice

    report.verification_status = "Verified"

    report.verified_by_doctor = current_doctor.full_name

    db.commit()

    return {
        "message": "Report verified successfully"
    }
# =========================================================
# DOWNLOAD REPORT
# =========================================================

@app.get("/download-report/{file_name}")
def download_report(
    file_name: str,
    current_patient: Patient = Depends(get_current_patient),
):
    file_path = os.path.join(
        UPLOAD_FOLDER,
        file_name,
    )

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/octet-stream",
    )

# =========================================================
# DOCTOR DASHBOARD
# =========================================================

@app.get("/doctor/reports")
def get_reports_for_doctor(
    current_doctor: Doctor = Depends(
        get_current_doctor
    ),
    db: Session = Depends(get_db),
):
    reports = (
        db.query(Report)
        .join(Patient)
        .filter(Patient.is_subscribed == "true")
        .order_by(Report.id.desc())
        .all()
    )

    result = []

    for report in reports:
        result.append({
            "id": report.id,

            "patient_name":
                report.patient.full_name,

            "file_name":
                report.file_name,

            "summary":
                report.summary,

            "doctor_corrected_summary":
                report.doctor_corrected_summary,

            "verification_status":
                report.verification_status,

            "file_path":
                report.file_path,
        })

    return {"reports": result}

@app.get("/doctor/pending-reports")
def get_pending_reports(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):

    # ✅ Get only subscribed patients reports
    reports = (
        db.query(Report)
        .join(Patient)
        .filter(Patient.is_subscribed == "true")
        .filter(Report.verification_status == "Pending")
        .order_by(Report.id.desc())
        .all()
    )

    result = []

    for report in reports:
        patient = (
            db.query(Patient)
            .filter(Patient.id == report.patient_id)
            .first()
        )

        result.append({
            "report_id": report.id,

            "patient_name": patient.full_name,

            "patient_age": patient.age,

            "patient_gender": patient.gender,

            "file_name": report.file_name,

            "file_path": report.file_path,

            "summary": report.summary,

            "health_score": report.health_score,

            "risk_level": report.risk_level,

            "normal_factors": json.loads(report.normal_factors)
            if report.normal_factors else [],

            "abnormal_factors": json.loads(report.abnormal_factors)
            if report.abnormal_factors else [],

            "recommendations": json.loads(report.recommendations)
            if report.recommendations else [],

            "doctor_advice": report.doctor_advice,

            "verification_status": report.verification_status,
        })

    return {
        "reports": result
    }

@app.put("/doctor/verify-report/{report_id}")
def verify_report(
    report_id: int,
    data: VerifyReportRequest,
    current_doctor: Doctor = Depends(
        get_current_doctor
    ),
    db: Session = Depends(get_db),
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    report.verification_status = (
        data.verification_status
    )

    report.doctor_corrected_summary = (
        data.corrected_summary
    )

    report.verified_by_doctor = (
        current_doctor.full_name
    )

    db.commit()

    return {
        "message": "Report verified successfully"
    }

# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "Lab2Life API Running Successfully"
    }

# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )