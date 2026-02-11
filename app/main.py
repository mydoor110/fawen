from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from app.api import auth, document, proofreading, approval, number, admin, destroy
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.utils.exceptions import (
    base_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler,
    AppBaseException
)
from app.utils.logger import get_logger

# 导入所有模型确保表定义被注册
import app.models  # noqa: F401

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时自动创建表和初始化数据"""
    logger.info("正在初始化数据库...")
    
    # 自动创建所有表（如果不存在）
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")
    
    # 初始化默认数据
    from app.init_data import init_database
    db = SessionLocal()
    try:
        init_database(db)
    finally:
        db.close()
    
    logger.info("系统启动完成")
    yield
    logger.info("系统关闭")


app = FastAPI(
    title=settings.system.name,
    version=settings.system.version,
    description="公文文件号管理系统 API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppBaseException, base_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

app.include_router(auth.router, prefix="/api")
app.include_router(document.router, prefix="/api")
app.include_router(proofreading.router, prefix="/api")
app.include_router(approval.router, prefix="/api")
app.include_router(number.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(destroy.router, prefix="/api")

@app.get("/")
async def root():
    return {
        "name": settings.system.name,
        "version": settings.system.version,
        "environment": settings.system.environment
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
