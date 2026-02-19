import json
import re
import uuid
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, field_validator, EmailStr
app = FastAPI(title="Сервис обращений абонентов")

STORAGE_DIR = Path("appeals")
STORAGE_DIR.mkdir(exist_ok=True)

class ReasonEnum(str, Enum):
    no_network = "нет доступа к сети"
    phone_not_working = "не работает телефон"
    no_mail = "не приходят письма"


class CalculateRequest(BaseModel):
    numbers: List[float] = Field(..., min_items=1)
    delays: List[float] = Field(..., min_items=1)


class ResultItem(BaseModel):
    number: float
    square: float
    delay: float
    time: float


class CalculateResponse(BaseModel):
    results: List[ResultItem]
    total_time: float
    parallel_faster_than_sequential: bool

def validate_cyrillic_capitalized(value: str, field_name: str) -> str:
    if not re.fullmatch(r"[А-ЯЁ][а-яё]+", value):
        raise ValueError(
            f"{field_name} должно начинаться с заглавной буквы "
            f"и содержать только кириллицу"
        )
    return value

class AppealTask1(BaseModel):
    last_name: str
    first_name: str
    birth_date: date
    phone: str
    email: EmailStr

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: str) -> str:
        return validate_cyrillic_capitalized(v, "Фамилия")

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        return validate_cyrillic_capitalized(v, "Имя")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.fullmatch(r"(\+7|7|8)\d{10}", cleaned):
            raise ValueError(
                "Номер телефона должен быть в формате +7XXXXXXXXXX или 8XXXXXXXXXX"
            )
        return cleaned

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, v: date) -> date:
        if v >= date.today():
            raise ValueError("Дата рождения должна быть в прошлом")
        return v

class AppealTask2(AppealTask1):
    reason: ReasonEnum
    problem_detected_at: datetime

    @field_validator("problem_detected_at")
    @classmethod
    def validate_problem_detected_at(cls, v: datetime) -> datetime:
        if v > datetime.now():
            raise ValueError("Дата обнаружения проблемы не может быть в будущем")
        return v


class AppealTask3(AppealTask1):
    reasons: List[ReasonEnum]
    problem_detected_at: datetime

    @field_validator("reasons")
    @classmethod
    def validate_reasons(cls, v: List[ReasonEnum]) -> List[ReasonEnum]:
        if not v:
            raise ValueError("Укажите хотя бы одну причину обращения")
        if len(set(v)) != len(v):
            raise ValueError("Причины обращения не должны повторяться")
        return v

    @field_validator("problem_detected_at")
    @classmethod
    def validate_problem_detected_at(cls, v: datetime) -> datetime:
        if v > datetime.now():
            raise ValueError("Дата обнаружения проблемы не может быть в будущем")
        return v

def save_appeal(data: dict, prefix: str = "appeal") -> str:
    appeal_id = str(uuid.uuid4())
    file_path = STORAGE_DIR / f"{prefix}_{appeal_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return str(file_path)

async def calc_square(number: float, delay: float) -> ResultItem:
    start = time.perf_counter()
    await asyncio.sleep(delay)
    elapsed = time.perf_counter() - start

    return ResultItem(
        number=number,
        square=number ** 2,
        delay=delay,
        time=round(elapsed, 2),
    )

@app.post("/appeal/task1", summary="Задача 1: базовое обращение")
def create_appeal_task1(appeal: AppealTask1):
    data = appeal.model_dump()
    file_path = save_appeal(data, prefix="task1")
    return {"status": "saved", "file": file_path, "data": data}


@app.post("/appeal/task2", summary="Задача 2: обращение с причиной")
def create_appeal_task2(appeal: AppealTask2):
    data = appeal.model_dump()
    file_path = save_appeal(data, prefix="task2")
    return {"status": "saved", "file": file_path, "data": data}


@app.post("/appeal/task3", summary="Задача 3: обращение с несколькими причинами")
def create_appeal_task3(appeal: AppealTask3):
    data = appeal.model_dump()
    file_path = save_appeal(data, prefix="task3")
    return {"status": "saved", "file": file_path, "data": data}

@app.post("/calculate/", response_model=CalculateResponse)
async def calculate(data: CalculateRequest):
    if len(data.numbers) != len(data.delays):
        raise HTTPException(
            status_code=400,
            detail="numbers and delays must have the same length",
        )

    start_parallel = time.perf_counter()
    tasks = [
        calc_square(n, d)
        for n, d in zip(data.numbers, data.delays)
    ]
    results = await asyncio.gather(*tasks)
    total_parallel_time = time.perf_counter() - start_parallel

    sequential_time = sum(data.delays)

    return CalculateResponse(
        results=results,
        total_time=round(total_parallel_time, 2),
        parallel_faster_than_sequential=total_parallel_time < sequential_time,
    )