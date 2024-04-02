# stdlib
import os
import sys

# third party
from fastapi import FastAPI
from loguru import logger

# relative
from .cpu_attest import cpu_attest
from .gpu_attest import gpu_attest
from .models import CPUAttestationResponseModel
from .models import GPUAttestationResponseModel
from .models import ResponseModel

# Logging Configuration
log_level = os.getenv("APP_LOG_LEVEL", "INFO").upper()
logger.remove()
logger.add(sys.stderr, colorize=True, level=log_level)

app = FastAPI(title="Attestation API")


@app.get("/", response_model=ResponseModel)
async def read_root() -> ResponseModel:
    return ResponseModel(message="Server is running")


@app.get("/attest/cpu", response_model=CPUAttestationResponseModel)
async def attest_cpu_endpoint() -> CPUAttestationResponseModel:
    cpu_attest_res = cpu_attest()
    return CPUAttestationResponseModel(result=cpu_attest_res)


@app.get("/attest/gpu", response_model=GPUAttestationResponseModel)
async def attest_gpu_endpoint() -> GPUAttestationResponseModel:
    gpu_attest_res = gpu_attest()
    return GPUAttestationResponseModel(result=gpu_attest_res)
