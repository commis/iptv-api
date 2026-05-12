import base64

from core.logger_factory import LoggerFactory

logger = LoggerFactory.get_logger(__name__)


def base64_encode(text: str, url_safe: bool = False) -> str:
    """
    将文本进行 Base64 编码

    参数:
        text (str): 待编码的文本
        url_safe (bool): 是否使用 URL 安全的编码方式，默认为 False
    返回:
        str: Base64 编码后的字符串
    """
    try:
        # 将文本转换为字节
        text_bytes = text.encode('utf-8')
        if url_safe:
            # 使用 URL 安全的 Base64 编码（替换 '+' 为 '-'，'/' 为 '_'）
            encoded_bytes = base64.urlsafe_b64encode(text_bytes)
            encoded_str = encoded_bytes.decode('ascii').rstrip('=')
        else:
            # 使用标准的 Base64 编码
            encoded_bytes = base64.b64encode(text_bytes)
            encoded_str = encoded_bytes.decode('ascii')

        return encoded_str
    except Exception as e:
        logger.error(f"error: Base64 encode failed - {str(e)}")
        raise Exception(f"Base64 encode failed - {str(e)}")


def base64_decode(encoded_text: str, url_safe: bool = False) -> str:
    """
    对 Base64 编码的文本进行解码

    参数:
        encoded_text (str): 待解码的 Base64 编码字符串
        url_safe (bool): 是否使用 URL 安全的解码方式，默认为 False
    返回:
        str: 解码后的原始文本
    """
    try:
        # 确保编码字符串长度是 4 的倍数（补充 '=' 填充）
        missing_padding = len(encoded_text) % 4
        if missing_padding:
            encoded_text += '=' * (4 - missing_padding)

        if url_safe:
            # 使用 URL 安全的 Base64 解码
            encoded_bytes = encoded_text.encode('ascii')
            decoded_bytes = base64.urlsafe_b64decode(encoded_bytes)
        else:
            # 使用标准的 Base64 解码
            encoded_bytes = encoded_text.encode('ascii')
            decoded_bytes = base64.b64decode(encoded_bytes)

        # 转换为 UTF-8 字符串
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"error: Base64 decode failed - {str(e)}")
        raise Exception(f"Base64 decode failed - {str(e)}")
