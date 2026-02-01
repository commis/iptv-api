import os
import random
import time
from datetime import datetime
from typing import List

import requests

from api.tv.converter import LiveConverter
from core.constants import Constants
from core.logger_factory import LoggerFactory
from models.counter import Counter
from models.migu_info import MiguCateInfo, MiguDataInfo
from services import channel_manager, category_manager, task_manager
from utils.encry_util import getStringMD5
from utils.string_util import get_xml_cvt_string, seconds_to_time_str, ms2time_str

logger = LoggerFactory.get_logger(__name__)


class Parser:
    _txt_url = "http://ak3721.top/tv/json/template.txt"
    _m3u_url = "http://ak3721.top/tv/json/template.m3u"
    _migu_url = "https://program-sc.miguvideo.com/live/v2/tv-data/"

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
                category_stack = (
                    category_manager.get_category(category) if category else None
                )
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

    def load_remote_url_m3u(self, url: str, is_recursion: bool = False):
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
                    tvg_new_logo = (
                        channel_manager.epg.get_logo(tvg_logo)
                        if change_logo
                        else tvg_logo
                    )
                    channel_manager.add_channel(
                        define_category, channel_name, line, tvg_id, tvg_new_logo
                    )

            if not is_recursion:
                # 处理自建频道
                self.load_remote_url_txt(self._txt_url)
                self.load_remote_url_m3u(self._m3u_url, True)
                channel_manager.sort()
        except Exception as e:
            logger.error(f"parse m3u data failed: {e}")

    def load_remote_url_migu(self, task_id, epg_file):
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(epg_file), exist_ok=True)
            migu_cates = self._migu_cate_list()
            epg_file_bak = epg_file + ".bak"
            with open(epg_file_bak, "w", encoding="utf-8") as f:
                f.write(
                    '<?xml version="1.0" encoding="utf-8"?>\n'
                    '<tv generator-info-name="Talk" generator-info-url="https://ak3721.top/tv">\n'
                )
                processed_counter = Counter()
                for cate in migu_cates:
                    cate_name = category_manager.get_category(cate.name)
                    data_list = self._get_migu_cate_data(cate.vid)
                    for data in data_list:
                        tvg_id = category_manager.get_channel_id(data.name)
                        channel_name = category_manager.get_channel(data.name)
                        channel_manager.add_channel(cate_name, channel_name, data.url, tvg_id, data.pic)
                        self._get_migu_playback_data(cate_name, data, f)
                        processed_counter.increment()
                    task_manager.update_task(task_id, processed=processed_counter.get_value())
                f.write("</tv>\n")
            os.rename(epg_file_bak, epg_file)
            # 处理自建频道
            self.load_remote_url_txt(self._txt_url)
            self.load_remote_url_m3u(self._m3u_url, True)
            channel_manager.sort()
        except Exception as e:
            logger.error(f"fetch migu data failed: {e}")

    def _migu_cate_list(self) -> List[MiguCateInfo]:
        migu_cate_url = self._migu_url + "1ff892f2b5ab4a79be6e25b69d2f5d05"
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

    def _get_migu_playback_data(self, category_name, channel_data, fd):
        try:
            date_str = datetime.now().strftime("%Y%m%d")
            # 过滤掉排除的频道
            category_info = category_manager.get_category_object(channel_data.name, category_name)
            if category_info and not category_manager.is_exclude(category_info, channel_data.name):
                if Constants.cvt_exist(channel_data.name):
                    tv_name = Constants.get_cvt_name(channel_data.name)
                    self._get_migu_playback_data_cctv(channel_data.name, date_str, tv_name, fd)
                else:
                    self._get_migu_playback_data_others(channel_data, date_str, fd)
        except Exception as e:
            logger.error(f"fetch migu playback data failed: {e}")

    def _get_migu_playback_data_cctv(self, name, date_str, tv_name, fd):
        fetch_url = (
            f"https://api.cntv.cn/epg/epginfo3?serviceId=shiyi&d={date_str}&c={tv_name}"
        )
        try:
            resp = requests.get(fetch_url, timeout=Constants.REQUEST_TIMEOUT)
            resp.raise_for_status()
            playback_data = resp.json().get(tv_name, {}).get("program", {})
            if playback_data:
                tvg_id = category_manager.get_channel_id(name)
                display_name = category_manager.get_channel(name)
                fd.write(
                    f'    <channel id="{tvg_id}">\n'
                    f'        <display-name lang="zh">{display_name}</display-name>\n'
                    "    </channel>\n"
                )
                for data in playback_data:
                    st_str = seconds_to_time_str(data.get("st"))
                    et_str = seconds_to_time_str(data.get("et"))
                    cont_name = get_xml_cvt_string(data.get("t"))
                    fd.write(
                        f'    <programme channel="{tvg_id}" start="{st_str} +0800" stop="{et_str} +0800">\n'
                        f'        <title lang="zh">{cont_name}</title>\n'
                        "    </programme>\n"
                    )
        except Exception as e:
            logger.error(f"get migu playback data for CCTV failed: {e}")

    def _get_migu_playback_data_others(self, channel_data, date_str, fd):
        try:
            fetch_url = f"https://program-sc.miguvideo.com/live/v2/tv-programs-data/{channel_data.pid}/{date_str}"
            resp = requests.get(fetch_url, timeout=Constants.REQUEST_TIMEOUT)
            resp.raise_for_status()
            playback_data = (
                resp.json().get("body", {}).get("program")[0].get("content", [])
            )
            if playback_data:
                tvg_id = category_manager.get_channel_id(channel_data.name)
                display_name = category_manager.get_channel(channel_data.name)
                fd.write(
                    f'    <channel id="{tvg_id}">\n'
                    f'        <display-name lang="zh">{display_name}</display-name>\n'
                    "    </channel>\n"
                )
                for data in playback_data:
                    st_str = ms2time_str(data.get("startTime"))
                    et_str = ms2time_str(data.get("endTime"))
                    cont_name = get_xml_cvt_string(data.get("contName"))
                    fd.write(
                        f'    <programme channel="{tvg_id}" start="{st_str} +0800" stop="{et_str} +0800">\n'
                        f'        <title lang="zh">{cont_name}</title>\n'
                        "    </programme>\n"
                    )
        except Exception as e:
            logger.error(f"get migu playback data failed: {e}")

    def _get_migu_cate_data(self, pid: str) -> List[MiguDataInfo]:
        output_data = []
        try:
            migu_url = self._migu_url + pid
            response = requests.get(migu_url, timeout=Constants.REQUEST_TIMEOUT)
            response.raise_for_status()
            json_cate_data = response.json()

            body = json_cate_data.get("body", {})
            data_list = body.get("dataList", [])
            for data in data_list:
                pics = data.get("pics", [])
                migu_data_info = MiguDataInfo(data.get("name"), data.get("pID"), pics.get("highResolutionH"))
                migu_play_url = self._get_migo_video_url(migu_data_info.name, migu_data_info.pid)
                if migu_play_url:
                    migu_data_info.set_url(migu_play_url)
                    output_data.append(migu_data_info)
            return output_data
        except Exception as e:
            logger.error(f"get migu cate data failed: {e}")
            return output_data

    def _get_migo_video_url(self, pname, pid) -> str:
        url = self._getAndroidURL720p(pname, pid)
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

    def _getAndroidURL720p(self, pname, pid, enableHDR: bool = True, enableH265: bool = True):
        appVersion = "2600034600"
        appVersionID = f"{appVersion}-99000-201600010010028"
        timestamp = str(round(time.time() * 1000))

        headers = {
            "AppVersion": appVersion,
            "TerminalId": "android",
            "X-UP-CLIENT-CHANNEL-ID": appVersionID,
        }
        # if Constants.MIGU_USERID and Constants.MIGU_TOKEN:
        #     headers["UserId"] = Constants.MIGU_USERID
        #     headers["UserToken"] = Constants.MIGU_TOKEN

        # 排除 CCTV5 和 CCTV5+
        exclude_pids = {"641886683", "641886773"}
        if pid not in exclude_pids:
            headers["appCode"] = "miguvideo_default_android"

        input_str = timestamp + pid + appVersion[:8]
        md5 = getStringMD5(input_str)

        salt = str(random.randint(0, 999999)).zfill(6) + "25"
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

        playUrl = ""
        try:
            resp = requests.get(full_url, headers=headers, timeout=Constants.REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp_json = resp.json()
            respBody = resp_json.get("body", {})
        except Exception as e:
            logger.error("fetch video url failed: ", str(e))
            return playUrl

        url_info = respBody.get("urlInfo")
        if not (url_info and (playUrl := url_info.get("url"))):
            logger.error(
                f"channel data [{pname}, {pid}], resp [{resp_json.get("code")}, {resp_json.get("rid")}]"
            )
            return playUrl

        pid = respBody.get("content", {}).get("contId", pid)
        return self._getddCalcuURL720p(playUrl, pid)

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

            match i:
                case 1:
                    dd_calcu.append("v")
                case 2:
                    date_str = datetime.now().strftime("%Y%m%d")
                    dd_calcu.append(keys[int(date_str[2])])
                case 3:
                    dd_calcu.append(keys[int(programId[6])])
                case 4:
                    dd_calcu.append("a")
                case _:
                    pass

        return "".join(dd_calcu)
