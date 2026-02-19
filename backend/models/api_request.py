import re
from typing import Optional, List
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class SingleCheckRequest(BaseModel):
    """单个频道检查请求模型"""

    url: str = Field(..., description="频道URL")
    rule: str = Field(default="/{i}/", description="解析规则，必须包含{i}占位符")

    @field_validator("url")
    def valid_url(cls, value):
        """验证URL格式是否有效"""
        try:
            result = urlparse(value)
            if not all([result.scheme, result.netloc]):
                raise ValueError("无效的URL格式")
            return value
        except ValueError as e:
            raise ValueError(f"URL验证失败: {str(e)}")

    @field_validator("rule")
    def rule_contains_placeholder(cls, value):
        """验证规则中是否包含{i}占位符"""
        if "{i}" not in value:
            raise ValueError("规则必须包含{i}占位符")
        return value

    def extract_id(self, url: str) -> str:
        """从URL中提取频道ID，若未找到则返回1"""
        pattern = re.escape(self.rule).replace("\\{i\\}", "(\\d+)")
        match = re.search(pattern, url)
        return match.group(1) if match else "index"


class BatchCheckRequest(BaseModel):
    """批量频道检查请求模型"""

    url: str = Field(..., description="包含{i}占位符的基础URL")
    start: int = Field(1, ge=1, description="起始频道ID")
    size: int = Field(10, ge=1, le=1000, description="检查数量上限1000")
    resolution: Optional[str] = Field("1920*1080", description="过滤掉指定分辨率数据")
    is_clear: Optional[bool] = Field(True, description="是否清空已有频道数据")
    thread_size: Optional[int] = Field(20, ge=1, le=64, description="并发线程数上限50")


class EpgRequest(BaseModel):
    file: Optional[str] = Field(default="/tmp/e.xml", description="直播源回放信息文件")
    url: Optional[str] = Field(default="https://gh-proxy.org/github.com/develop202/migu_video/blob/main/playback.xml",
                               description="直播源回放信息URL")
    source: Optional[str] = Field(default="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}",
                                  description="直播源回放查找参数")
    domain: Optional[str] = Field(default="", description="LOGO文件域名")
    show_logo: Optional[bool] = Field(default=True, description="全局开关，是否打开Logo显示")
    rename_cid: Optional[bool] = Field(default=True, description="是否替换Channel ID")


class UpdateLiveRequest(BaseModel):
    """更新直播源请求"""

    output: str = Field(default="/tmp/migu3721.txt", description="直播源输出文件名")
    url: Optional[List[str]] = Field(default=[], description="直播源同步URL")
    epg: Optional[EpgRequest] = Field(default=None, description="EPG源信息")
    rate_type: Optional[int] = Field(default=3, description="分辨率，仅在Migu视频有效[2:标清,3:高清,4:蓝光,7:原画,9:4k]")
    is_clear: Optional[bool] = Field(True, description="是否清空已有频道数据")
    thread_size: Optional[int] = Field(20, ge=1, le=64, description="并发线程数上限64")
    low_limit: Optional[int] = Field(5, ge=5, le=300, description="自动更新频道数量下限")


class ChannelQuery(BaseModel):
    speed: int = Field(..., description="频道速率")

    @field_validator("speed")
    def check_speed(cls, values):
        if not values.speed or values.speed.strip() == "":
            raise ValueError("频道速率不能为空")
        return values
