import random
import time
from datetime import datetime
from typing import List

import requests
from bs4 import BeautifulSoup

from api.tv.converter import LiveConverter
from core.constants import Constants
from core.logger_factory import LoggerFactory
from models.migu_info import MiguCateInfo, MiguDataInfo
from services import channel_manager, category_manager
from utils.encry_util import getStringMD5

logger = LoggerFactory.get_logger(__name__)


class Parser:
    _live_url = "http://ak3721.top/tvbox/json/live.txt"

    @staticmethod
    def get_channel_data(text_data: str) -> list:
        """
        将用户提供的频道数据文本解析为 [(类别, 子类型, URL), ...] 格式的元组列表
        """
        category_stack = None
        channel_list = []

        for line in text_data.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.endswith("#genre#"):
                category = Constants.CATEGORY_CLEAN_PATTERN.sub(" ", line[:-7]).strip()
                category_stack = category_manager.get_category(category) if category else None
                continue

            if category_stack:
                parts = line.split(",", 1)
                if len(parts) != 2:
                    continue
                channel_name, url = [p.strip() for p in parts]
                if not url:
                    continue

                category_info = category_manager.get_category_object(
                    channel_name, category_stack
                )
                category_name = category_info.get("name")
                if not category_manager.is_exclude(category_info, channel_name):
                    channel_list.append((category_name, channel_name, url))

        return channel_list

    def load_remote_sitemap(self, url: str):
        try:
            response = requests.get(url, timeout=Constants.REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "xml")
            for loc in soup.find_all("loc"):
                url = loc.text.strip()
                if not url.endswith("iptv4.txt"):
                    continue
                self.load_remote_url_txt(url, True)

            # 处理自建频道
            self.load_remote_url_txt(self._live_url)
            channel_manager.sort()
        except Exception as e:
            logger.error(f"parse sitemap data failed: {e}")

    def load_remote_url_txt(self, url, use_ignore=False):
        try:
            response = requests.get(url, timeout=Constants.REQUEST_TIMEOUT)
            response.raise_for_status()
            self.load_channel_txt(response.text.strip(), use_ignore)
        except Exception as e:
            logger.error(f"access remote url data failed: {e}")

    @staticmethod
    def load_channel_txt(text_data, use_ignore: bool = False):
        from services import category_manager

        category_name = None
        for line in (
                line.strip()
                for line in text_data.splitlines()
                if line.strip() and not line.startswith("#")
        ):
            if line.endswith("#genre#"):
                category_name = None
                parse_category = Constants.CATEGORY_CLEAN_PATTERN.sub(" ", line).strip()
                define_category = category_manager.get_category(parse_category)
                if define_category is None or (
                        use_ignore and category_manager.is_ignore(define_category)
                ):
                    continue
                if category_manager.exists(define_category):
                    category_name = define_category
                continue

            if category_name:
                # 解析频道信息
                try:
                    subgenre, url = line.split(",", 1)
                    subgenre, url = subgenre.strip(), url.strip()
                    channel_name = category_manager.get_channel(subgenre)
                    if url:
                        channel_manager.add_channel(category_name, channel_name, url)
                except ValueError:
                    continue

    def load_remote_url_m3u(self, url: str):
        try:
            response = requests.get(url, timeout=Constants.REQUEST_TIMEOUT)
            response.raise_for_status()
            m3u_data = response.text.strip()

            tvg_id = ""
            tvg_logo = ""
            group_title = ""
            channel_name = None
            for line in (
                    line.strip() for line in m3u_data.splitlines() if line.strip()
            ):
                if line.startswith("#EXTM3U"):
                    continue

                if line.startswith("#EXTINF:"):
                    tag_content = line[8:].strip()
                    params, name = LiveConverter.parse_extinf_params(tag_content)
                    channel_name = category_manager.get_channel(name)
                    tvg_id = category_manager.get_channel_id(params.get("id", ""))
                    tvg_logo = params.get("logo", "")
                    group_title = params.get("title", "")

                elif line.startswith(("http:", "https:")):
                    define_category = category_manager.get_category(group_title)
                    if (
                            define_category is None
                            or (category_manager.is_ignore(define_category))
                            or not category_manager.exists(define_category)
                    ):
                        continue
                    change_logo = category_manager.change_logo(define_category)
                    tvg_new_logo = channel_manager.epg.get_logo(tvg_logo) if change_logo else tvg_logo
                    channel_manager.add_channel(
                        define_category, channel_name, line, tvg_id, tvg_new_logo
                    )

            # 处理自建频道
            self.load_remote_url_txt(self._live_url)
            channel_manager.sort()
        except Exception as e:
            logger.error(f"parse m3u data failed: {e}")

    def load_remote_migu(self):
        try:
            migu_cates = self._migu_cate_list()
            for cate in migu_cates:
                data_list = self._get_migu_cate_data(cate.vid)
                for data in data_list:
                    tvg_id = category_manager.get_channel_id(data.name)
                    cate_name = category_manager.get_category(cate.name)
                    channel_manager.add_channel(cate_name, data.name, data.url, tvg_id, data.pic)

            # 处理自建频道
            self.load_remote_url_txt(self._live_url)
            channel_manager.sort()
        except Exception as e:
            logger.error(f"fetch migu data failed: {e}")

    def _migu_cate_list(self) -> List[MiguCateInfo]:
        migu_cate_url = "https://program-sc.miguvideo.com/live/v2/tv-data/1ff892f2b5ab4a79be6e25b69d2f5d05"
        response = requests.get(migu_cate_url, timeout=Constants.REQUEST_TIMEOUT)
        response.raise_for_status()
        json_cate_data = response.json()

        output_data = []
        body = json_cate_data.get("body", {})
        live_list = body.get("liveList", [])
        for live in live_list:
            name = live.get("name", "")
            if name != "热门":
                output_data.append(MiguCateInfo(name, live.get("vomsID")))

        return output_data

    def _get_migu_cate_data(self, id: str) -> List[MiguDataInfo]:
        migu_data_url = "https://program-sc.miguvideo.com/live/v2/tv-data/"
        output_data = []
        try:
            migu_url = migu_data_url + id
            response = requests.get(migu_url, timeout=Constants.REQUEST_TIMEOUT)
            response.raise_for_status()
            json_cate_data = response.json()

            body = json_cate_data.get("body", {})
            data_list = body.get("dataList", [])
            for data in data_list:
                pics = data.get("pics", [])
                migu_data_info = MiguDataInfo(data.get("name"), data.get("pID"), pics.get("highResolutionH"))
                migu_play_url = self._get_migo_video_url(migu_data_info.pid)
                migu_data_info.set_url(migu_play_url)
                output_data.append(migu_data_info)
            return output_data
        except Exception as e:
            return output_data

    def _get_migo_video_url(self, pid: str) -> str:
        url = self._getAndroidURL720p(pid)
        if not url:
            return url

        for retry in range(6):
            try:
                resp = requests.get(url, allow_redirects=False, timeout=Constants.REQUEST_TIMEOUT)
                location = resp.headers.get("Location", "")
                if not location:
                    continue
                if not location.startswith("http://bofang"):
                    url = location
                    break
            except Exception as e:
                logger.error(f"请求重试失败: {str(e)}")

            if retry < 5:
                time.sleep(0.15)

        return url

    def _getAndroidURL720p(self, pid: str, enableHDR: bool = True, enableH265: bool = True):
        appVersion = "2600034600"
        appVersionID = f"{appVersion}-99000-201600010010028"
        timestamp = str(round(time.time() * 1000))

        headers = {
            "AppVersion": appVersion,
            "TerminalId": "android",
            "X-UP-CLIENT-CHANNEL-ID": appVersionID,
        }

        # 排除 CCTV5 和 CCTV5+
        exclude_pids = {"641886683", "641886773"}
        if pid not in exclude_pids:
            headers["appCode"] = "miguvideo_default_android"

        input_str = timestamp + pid + appVersion[:8]
        md5 = getStringMD5(input_str)

        salt = str(random.randint(0, 999999)).zfill(6) + '25'
        suffix = f"2cac4f2c6c3346a5b34e085725ef7e33migu{salt[:4]}"
        sign = getStringMD5(md5 + suffix)

        # 2: 标清, 3: 高清, 4: 蓝光, 7: 原画, 9: 4k
        rateType = 3
        enableHDRStr = "&4kvivid=true&2Kvivid=true&vivid=2" if enableHDR else ""
        enableH265Str = "&h265N=true" if enableH265 else ""

        baseURL = "https://play.miguvideo.com/playurl/v1/play/playurl"
        params = (
            f"?sign={sign}&rateType={rateType}&contId={pid}&timestamp={timestamp}"
            f"&salt={salt}&flvEnable=true&super4k=true{enableH265Str}{enableHDRStr}"
        )
        full_url = baseURL + params

        try:
            resp = requests.get(full_url, headers=headers, timeout=Constants.REQUEST_TIMEOUT)
            resp.raise_for_status()
            respBody = resp.json().get("body", {})
        except Exception as e:
            logger.error("fetch video url failed: ", str(e))
            return ""

        url_info = respBody.get("urlInfo", {})
        url = url_info.get("url", "")
        if not url:
            return ""

        pid = respBody.get("content", {}).get("contId", pid)
        return self._getddCalcuURL720p(url, pid)

    def _getddCalcuURL720p(self, puDataURL: str, programId: str) -> str:
        if puDataURL is None or programId is None:
            return ""

        try:
            puData = puDataURL.split("&puData=")[1]
        except IndexError:
            logger.error("URL中未找到puData参数")
            return ""

        ddCalcu = self._getddCalcu720p(puData, programId)
        return f"{puDataURL}&ddCalcu={ddCalcu}&sv=10004&ct=android"

    def _getddCalcu720p(self, puData, programId) -> str:
        if puData is None or programId is None:
            return ""

        keys = "cdabyzwxkl"
        dd_calcu = []
        loop_times = int(len(puData) / 2)
        for i in range(loop_times):
            dd_calcu.append(puData[len(puData) - i - 1])
            dd_calcu.append(puData[i])

            if i == 1:
                dd_calcu.append("v")
            elif i == 2:
                date_str = datetime.now().strftime("%Y%m%d")
                dd_calcu.append(keys[int(date_str[2])])
            elif i == 3:
                dd_calcu.append(keys[int(programId[6])])
            elif i == 4:
                dd_calcu.append("a")

        return "".join(dd_calcu)
