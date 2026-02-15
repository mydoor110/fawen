"""
文件号合规性校验器
用于校验手动调整的文件号是否符合规范
"""
import re
from datetime import datetime
from typing import Tuple, List


class NumberValidator:
    """文件号合规性校验器"""
    
    # 默认格式: 前缀(2-5个大写字母)-年份(4位数字)-序号(4-6位数字)
    DEFAULT_PATTERN = r'^[A-Z]{2,5}-\d{4}-\d{4,6}$'
    
    @staticmethod
    def validate_format(number: str, pattern: str = None) -> Tuple[bool, str]:
        """
        校验文件号格式
        
        Args:
            number: 文件号字符串
            pattern: 正则表达式模式，默认为 DEFAULT_PATTERN
            
        Returns:
            (是否通过, 错误信息或成功信息)
            
        Examples:
            >>> NumberValidator.validate_format("GW-2026-0001")
            (True, "格式正确")
            >>> NumberValidator.validate_format("gw-2026-0001")
            (False, "文件号格式不符合规范...")
        """
        if not number:
            return False, "文件号不能为空"
        
        if not pattern:
            pattern = NumberValidator.DEFAULT_PATTERN
        
        if not re.match(pattern, number):
            return False, f"文件号格式不符合规范，应符合格式: 前缀-年份-序号 (例如: GW-2026-0001)"
        
        return True, "格式正确"
    
    @staticmethod
    def validate_year(number: str) -> Tuple[bool, str]:
        """
        校验年份是否合理
        年份应该在2000年到明年之间
        
        Args:
            number: 文件号字符串
            
        Returns:
            (是否通过, 错误信息或成功信息)
        """
        parts = number.split('-')
        if len(parts) < 2:
            return False, "无法解析年份，文件号格式错误"
        
        try:
            year = int(parts[1])
            current_year = datetime.now().year
            
            if year < 2000:
                return False, f"年份不合理: {year}，年份不能早于2000年"
            
            if year > current_year + 1:
                return False, f"年份不合理: {year}，年份不能超过{current_year + 1}年"
            
            return True, "年份正确"
        except (ValueError, IndexError):
            return False, "年份格式错误，应为4位数字"
    
    @staticmethod
    def validate_sequence(number: str, min_sequence: int = 1, max_sequence: int = 999999) -> Tuple[bool, str]:
        """
        校验序号范围
        
        Args:
            number: 文件号字符串
            min_sequence: 最小序号（默认1）
            max_sequence: 最大序号（默认999999）
            
        Returns:
            (是否通过, 错误信息或成功信息)
        """
        parts = number.split('-')
        if len(parts) < 3:
            return False, "无法解析序号，文件号格式错误"
        
        try:
            seq = int(parts[2])
            
            if seq < min_sequence:
                return False, f"序号不能小于{min_sequence}"
            
            if seq > max_sequence:
                return False, f"序号超出范围，最大值为{max_sequence}"
            
            return True, "序号正确"
        except (ValueError, IndexError):
            return False, "序号格式错误，应为数字"
    
    @staticmethod
    def validate_prefix(number: str, allowed_prefixes: List[str] = None) -> Tuple[bool, str]:
        """
        校验前缀是否在允许的列表中
        
        Args:
            number: 文件号字符串
            allowed_prefixes: 允许的前缀列表，None表示不限制
            
        Returns:
            (是否通过, 错误信息或成功信息)
        """
        if not allowed_prefixes:
            return True, "前缀校验已跳过（未配置允许列表）"
        
        parts = number.split('-')
        if len(parts) < 1:
            return False, "无法解析前缀，文件号格式错误"
        
        prefix = parts[0]
        
        if prefix not in allowed_prefixes:
            return False, f"前缀不在允许列表中，允许的前缀: {', '.join(allowed_prefixes)}"
        
        return True, "前缀正确"
    
    @staticmethod
    def validate_uniqueness(db, number: str, exclude_document_id: str = None) -> Tuple[bool, str]:
        """
        校验文件号唯一性（需要数据库查询）
        
        Args:
            db: 数据库会话
            number: 文件号字符串
            exclude_document_id: 排除的文档ID（用于更新场景）
            
        Returns:
            (是否通过, 错误信息或成功信息)
        """
        from app.models.document import Document
        from sqlalchemy import and_
        
        query = db.query(Document).filter(Document.official_number == number)
        
        if exclude_document_id:
            query = query.filter(Document.id != exclude_document_id)
        
        existing = query.first()
        
        if existing:
            return False, f"文件号'{number}'已被使用，文档ID: {existing.id}"
        
        return True, "文件号唯一性校验通过"
    
    @staticmethod
    def validate_all(
        number: str, 
        db = None,
        allowed_prefixes: List[str] = None,
        exclude_document_id: str = None
    ) -> Tuple[bool, List[str]]:
        """
        执行所有校验
        
        Args:
            number: 文件号字符串
            db: 数据库会话（用于唯一性校验，可选）
            allowed_prefixes: 允许的前缀列表（可选）
            exclude_document_id: 排除的文档ID（可选）
            
        Returns:
            (是否全部通过, 错误信息列表)
            
        Examples:
            >>> valid, errors = NumberValidator.validate_all("GW-2026-0001")
            >>> if not valid:
            ...     print("校验失败:", errors)
        """
        errors = []
        
        # 1. 格式校验
        valid, msg = NumberValidator.validate_format(number)
        if not valid:
            errors.append(f"格式错误: {msg}")
            return False, errors  # 格式错误时不继续校验
        
        # 2. 年份校验
        valid, msg = NumberValidator.validate_year(number)
        if not valid:
            errors.append(f"年份错误: {msg}")
        
        # 3. 序号校验
        valid, msg = NumberValidator.validate_sequence(number)
        if not valid:
            errors.append(f"序号错误: {msg}")
        
        # 4. 前缀校验（如果配置了允许列表）
        if allowed_prefixes:
            valid, msg = NumberValidator.validate_prefix(number, allowed_prefixes)
            if not valid:
                errors.append(f"前缀错误: {msg}")
        
        # 5. 唯一性校验（如果提供了数据库会话）
        if db:
            valid, msg = NumberValidator.validate_uniqueness(db, number, exclude_document_id)
            if not valid:
                errors.append(f"唯一性错误: {msg}")
        
        return len(errors) == 0, errors


# 便捷函数
def validate_number(
    number: str,
    db = None,
    allowed_prefixes: List[str] = None,
    exclude_document_id: str = None
) -> Tuple[bool, str]:
    """
    校验文件号并返回友好的错误信息
    
    Args:
        number: 文件号字符串
        db: 数据库会话（可选）
        allowed_prefixes: 允许的前缀列表（可选）
        exclude_document_id: 排除的文档ID（可选）
        
    Returns:
        (是否通过, 错误消息或成功消息)
    """
    is_valid, errors = NumberValidator.validate_all(
        number, db, allowed_prefixes, exclude_document_id
    )
    
    if is_valid:
        return True, f"文件号'{number}'校验通过"
    else:
        error_msg = "; ".join(errors)
        return False, f"文件号'{number}'校验失败: {error_msg}"
