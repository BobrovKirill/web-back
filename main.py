from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
import asyncio
import time

app = FastAPI()


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