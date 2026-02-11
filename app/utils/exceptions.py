from fastapi import HTTPException, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from loguru import logger
from typing import Union, Any
from sqlalchemy.exc import SQLAlchemyError


class AppBaseException(Exception):
    """基础异常类"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class PermissionDeniedException(AppBaseException):
    """权限不足异常"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ResourceNotFoundException(AppBaseException):
    """资源不存在异常"""
    def __init__(self, resource: str = "资源"):
        super().__init__(f"{resource}不存在", status.HTTP_404_NOT_FOUND)


class BusinessLogicException(AppBaseException):
    """业务逻辑异常"""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, status_code)


class DocumentLockedException(AppBaseException):
    """文档锁定异常"""
    def __init__(self, message: str = "文档已锁定，无法操作"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class InvalidStatusTransitionException(AppBaseException):
    """无效状态转换异常"""
    def __init__(self, message: str = "无效的状态转换"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


async def base_exception_handler(request: Request, exc: AppBaseException):
    """基础异常处理器"""
    logger.error(f"BaseException: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    logger.error(f"HTTPException: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """数据库异常处理器"""
    logger.error(f"SQLAlchemyError: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "数据库操作失败"}
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "服务器内部错误"}
    )
