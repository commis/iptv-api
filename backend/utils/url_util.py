from urllib.parse import unquote, quote

from core.logger_factory import LoggerFactory

logger = LoggerFactory.get_logger(__name__)


def url_encode(text: str, safe: str = '') -> str:
    """
    对字符串进行 URL 编码，将特殊字符转换为 %xx 格式

    参数:
        text (str): 待编码的原始字符串
        safe (str): 指定不需要编码的字符，默认为 '/'
    返回:
        str: URL 编码后的字符串
    """
    try:
        # 使用 urllib.parse.quote 进行编码
        encoded_text = quote(text, safe=safe)
        return encoded_text
    except Exception as e:
        print(f"error: URL encoding failed - {str(e)}")
        raise Exception(f"URL encoding failed - {str(e)}")


def url_decode(encoded_text: str) -> str:
    """
    对 URL 编码的字符串进行解码

    参数:
        encoded_text (str): 待解码的 URL 编码字符串
    返回:
        str: 解码后的原始字符串
    """
    try:
        # 使用 urllib.parse.unquote 进行解码
        decoded_content = unquote(encoded_text)
        return decoded_content
    except Exception as e:
        logger.error(f"error: URL decoding failed - {str(e)}")
        raise Exception(f"URL decoding failed - {str(e)}")
