from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class EpgRequest(BaseModel):
    file: Optional[str] = Field(default="/tmp/migu-e.xml", description="直播源回放信息文件")
    url: Optional[str] = Field(default="https://ak3721.top/tv/epg/migu-e.xml",
                               description="直播源回放信息URL")
    source: Optional[str] = Field(default="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}",
                                  description="直播源回放查找参数")
    domain: Optional[str] = Field(default="", description="访问视频的地址")
    show_logo: Optional[bool] = Field(default=True, description="全局开关，是否打开Logo显示")
    rename_cid: Optional[bool] = Field(default=True, description="是否替换图片后缀")


class UpdateLiveRequest(BaseModel):
    """更新直播源请求"""

    output: str = Field(default="/tmp/result.txt", description="直播源输出文件名")
    url: Optional[List[str]] = Field(default=[], description="直播源同步URL")
    epg: Optional[EpgRequest] = Field(default=None, description="EPG源信息")
    group: Optional[List[str]] = Field(default=[], description="原始数据的分类过滤保留项")
    rate_type: Optional[int] = Field(default=3, description="分辨率，仅在Migu视频有效[2:标清,3:高清,4:蓝光,7:原画,9:4k]")
    check_m3u8: Optional[bool] = Field(False, description="是否检查视频的有效性")
    load_template: Optional[bool] = Field(True, description="是否加载本地模板文件")
    load_mediaurl: Optional[bool] = Field(True, description="是否生成MIGU视频地址")
    is_clear: Optional[bool] = Field(True, description="是否清空已有频道数据")


class UpdateVodRequest(BaseModel):
    """更新点播源请求"""

    sp: str = Field("v-docs", description="来源标识，不能为空")
    is_full: bool = Field(False, description="True=强制更新所有缓存")


class ChannelQuery(BaseModel):
    speed: int = Field(..., description="频道速率")

    @field_validator("speed")
    def check_speed(cls, values):
        if not values.speed or values.speed.strip() == "":
            raise ValueError("频道速率不能为空")
        return values
