import json
import os
import random
import re
import time
from datetime import datetime
from typing import List

import requests
import urllib3

from api.tv.converter import LiveConverter
from core.constants import Constants
from core.logger_factory import LoggerFactory
from models.counter import Counter
from models.migu_info import MiguCateInfo, MiguDataInfo
from services import channel_manager, config_manager, task_manager
from services.redis import redis_cache
from utils.encry_util import getStringMD5
from utils.string_util import get_xml_cvt_string, seconds_to_time_str, ms2time_str

logger = LoggerFactory.get_logger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLIENT_CONFIG = {
    "h5": {
        # 第11位字符
        "keys": "yzwxcdabgh",
        # 第5 8 14位字母对应下标0 1 3的字符
        "words": ['', 'y', '0', 'w'],
        # 第11位字符替换位置,从0开始
        "thirdReplaceIndex": 1,
        # 加密后链接后缀
        "suffix": "&sv=10000&ct=www"
    },
    "android": {
        "keys": "cdabyzwxkl",
        "words": ['v', 'a', '0', 'a'],
        "thirdReplaceIndex": 6,
        "suffix": "&sv=10004&ct=android"
    }
}


class Parser:
    _tvb_url = "http://121.43.255.31/umigu"
    _txt_url = "https://ak3721.top/tv/json/template.txt"
    _m3u_url = "https://ak3721.top/tv/json/template.m3u"
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
                    config_manager.get_category(category) if category else None
                )
                continue

            if category_stack:
                parts = line.split(",", 1)
                if len(parts) != 2:
                    continue
                channel_name, url = [p.strip() for p in parts]
                if not url:
                    continue

                category_info = config_manager.get_category_object(channel_name, category_stack)
                category_name = category_info.get("name")
                if not config_manager.is_exclude(category_info, channel_name):
                    channel_list.append((category_name, channel_name, url))

        return channel_list

    @staticmethod
    def load_channel_txt(text_data, filters: [str] = None, use_ignore: bool = True):
        from services import config_manager

        category_name = None
        for line in (
            line.strip()
            for line in text_data.splitlines()
            if line.strip() and not line.startswith("#")
        ):
            if line.endswith("#genre#"):
                category_name = None
                parse_category = Constants.CATEGORY_CLEAN_PATTERN.sub(" ", line).strip()
                if filters and parse_category not in filters:
                    continue

                define_category = config_manager.get_category(parse_category)
                if (
                    (use_ignore and config_manager.is_ignore(define_category))
                    or not config_manager.exists(define_category)
                ):
                    continue

                category_name = define_category
                continue

            if category_name:
                # 解析频道信息
                try:
                    subgenre, url = line.split(",", 1)
                    subgenre, url = subgenre.strip(), url.strip()
                    channel_name = config_manager.get_channel(subgenre)
                    if url:
                        channel_manager.add_channel(True, category_name, channel_name, url, subgenre)
                except ValueError:
                    continue

    def _load_remote_url_txt(self, url, filters: [str] = None, use_ignore: bool = True):
        try:
            response = requests.get(url, timeout=Constants.REQUEST_TIMEOUT, verify=False)
            response.raise_for_status()
            self.load_channel_txt(response.text.strip(), filters, use_ignore)
        except Exception as e:
            logger.error(f"access remote url data failed: {e}")

    def load_remote_url_m3u(self, url: str, filters: [str], load_template: bool):
        try:
            if load_template:
                self._load_channel_m3u(self._m3u_url, use_ignore=False)
                self._load_remote_url_txt(self._txt_url, use_ignore=False)
            self._load_channel_m3u(url, filters, True)
            channel_manager.sort()
        except Exception as e:
            logger.error(f"load remote url m3u data failed: {e}")

    def _load_channel_m3u(self, url: str, filters: [str] = None, use_ignore: bool = True):
        try:
            response = requests.get(url, timeout=Constants.REQUEST_TIMEOUT, verify=False)
            response.raise_for_status()
            m3u_data = response.text.strip()

            tvg_id = ""
            tvg_logo = ""
            group_title = ""
            channel_name = None
            for line in (line.strip() for line in m3u_data.splitlines() if line.strip()):
                if line.startswith("#EXTM3U"):
                    continue

                if line.startswith("#EXTINF:"):
                    tag_content = line[8:].strip()
                    params, name = LiveConverter.parse_extinf_params(tag_content)
                    channel_name = config_manager.get_channel(name)
                    tvg_id = config_manager.get_channel_id(params.get("id", ""))
                    tvg_logo = params.get("logo", "")
                    group_title = params.get("title", "")

                elif line.startswith(("http:", "https:")):
                    if filters and group_title not in filters:
                        continue

                    define_category = config_manager.get_category(group_title)
                    if (
                        (use_ignore and config_manager.is_ignore(define_category))
                        or not config_manager.exists(define_category)
                    ):
                        continue
                    do_channel_logo = config_manager.do_channel_logo(define_category)
                    match do_channel_logo:
                        case 0:
                            tvg_new_logo = ''
                        case 3:
                            tvg_new_logo = channel_manager.epg.get_logo(tvg_logo)
                        case _:
                            tvg_new_logo = tvg_logo
                    channel_manager.add_channel(use_ignore, define_category, channel_name, line, tvg_id, tvg_new_logo)
        except Exception as e:
            logger.error(f"load channel m3u data failed: {e}")

    def load_remote_url_migu(self, task_id, epg_file, rate_type, load_template: bool):

        def process_channel_TV(processed_counter, migu_cate_list, epg_f):
            processed_pids = set()
            for cate in migu_cate_list:
                cate_name = config_manager.get_category(cate.name)
                if not config_manager.exists(cate_name):
                    continue
                data_list = self._get_migu_cate_data(processed_pids, cate_name, cate.vid, rate_type)
                for data in data_list:
                    tvg_id = config_manager.get_channel_id(data.name)
                    channel_name = config_manager.get_channel(data.name)
                    # 在get_migu_cate_data函数内部已经做了过滤，古这里不用做重复的过滤了
                    channel_manager.add_channel(False, cate_name, channel_name, data.url, tvg_id, data.pic)
                    self._get_migu_playback_data(cate_name, data, epg_f)
                    processed_pids.add(data.pid)
                    processed_counter.increment()
                task_manager.update_task(task_id, processed=processed_counter.get_value())

        def process_channel_PE(processed_counter, migu_sport_list, epg_f):
            for (date_str, relative_date, data_list) in migu_sport_list:
                for data in data_list:
                    mgdb_id = data.get("mgdbId")
                    pk_info_title = data.get("pkInfoTitle")
                    teams = data.get("confrontTeams")
                    if teams and len(teams) >= 2:
                        pk_info_title = f"{teams[0].get('name')}VS{teams[1].get('name')}"
                    try:
                        url = f"https://vms-sc.miguvideo.com/vms-match/v6/staticcache/basic/basic-data/{mgdb_id}/miguvideo"
                        body = self._get_url_body(url)

                        # 1. 比赛已结束
                        now_ms = int(time.time() * 1000)
                        if body.get("endTime", 0) < now_ms:
                            self._get_migu_sport_overed(
                                processed_counter, task_id,
                                relative_date, data, body, pk_info_title, mgdb_id)
                            continue

                        # 2. 比赛进行中或未开始
                        live_list = body.get("multiPlayList", {}).get("liveList", [])
                        for live in live_list:
                            name = live.get("name", "")
                            start_time_str = live.get("startTimeStr")
                            if re.search(r".*集锦.*", name) or not start_time_str:
                                continue

                            competition_desc = (f"{data.get('competitionName')} "
                                                f"{pk_info_title} {name} {start_time_str[11:16]}")
                            category_info = config_manager.get_category_object(competition_desc, relative_date)
                            if category_info and config_manager.is_exclude(category_info, competition_desc):
                                continue
                            # migu_video_play_url = self.get_migu_video_url(competition_desc, live.get("pID"))
                            migu_video_play_url = f"{self._tvb_url}/{live.get("pID")}"
                            if migu_video_play_url:
                                channel_manager.add_channel(False, relative_date,
                                                            competition_desc,
                                                            migu_video_play_url,
                                                            pk_info_title,
                                                            data.get("competitionLogo"))
                                processed_counter.increment()
                        task_manager.update_task(task_id, processed=processed_counter.get_value())

                    except Exception as e:
                        logger.error(f"process PE data failed: {e}")

        try:
            if load_template:
                self._load_channel_m3u(self._m3u_url, use_ignore=False)
                self._load_remote_url_txt(self._txt_url, use_ignore=False)

            # 确保目录存在
            os.makedirs(os.path.dirname(epg_file), exist_ok=True)
            epg_file_bak = epg_file + ".bak"

            counter = Counter()
            migu_cates = self._get_migu_cate_list()
            migu_sports = self._get_migu_sport_list()
            with open(epg_file_bak, "w", encoding="utf-8") as f:
                f.write(
                    '<?xml version="1.0" encoding="utf-8"?>\n'
                    '<tv generator-info-name="Talk" generator-info-url="https://ak3721.top/tv">\n'
                )
                process_channel_TV(counter, migu_cates, f)
                process_channel_PE(counter, migu_sports, f)
                f.write("</tv>\n")
            os.rename(epg_file_bak, epg_file)
            channel_manager.sort()
        except Exception as e:
            logger.error(f"fetch migu data failed: {e}")

    def _get_migu_cate_list(self) -> List[MiguCateInfo]:
        cache_key = f"migu:live_list"
        cache_data = redis_cache.get(cache_key)
        if cache_data:
            cached = json.loads(cache_data)
            return [MiguCateInfo(item.get("name", ""), item.get("vid", "")) for item in cached]

        migu_cate_url = self._migu_url + "1ff892f2b5ab4a79be6e25b69d2f5d05"
        response = requests.get(migu_cate_url, timeout=Constants.REQUEST_TIMEOUT)
        response.raise_for_status()
        json_cate_data = response.json()

        body = json_cate_data.get("body", {})
        raw_live_list = body.get("liveList", [])
        exclude_names = {"热门", "少儿"}
        appended_cates = set()
        cate_list: List[MiguCateInfo] = []
        for live in raw_live_list:
            name = live.get("name", "")
            if not name or name in appended_cates or name in exclude_names:
                continue
            vid = live.get("vomsID", "")
            cate_list.append(MiguCateInfo(name, vid))
            appended_cates.add(name)

        redis_cache.set(
            cache_key,
            json.dumps([{"name": c.name, "vid": c.vid} for c in cate_list]),
            24 * 3600
        )

        return cate_list

    def _get_migu_playback_data(self, category_name, channel_data, fd):
        try:
            date_str = datetime.now().strftime("%Y%m%d")
            # 过滤掉排除的频道
            category_info = config_manager.get_category_object(channel_data.name, category_name)
            if category_info and not config_manager.is_exclude(category_info, channel_data.name):
                if Constants.cvt_exist(channel_data.name):
                    tv_name = Constants.get_cvt_name(channel_data.name)
                    self._get_migu_playback_data_cctv(channel_data.name, date_str, tv_name, fd)
                else:
                    self._get_migu_playback_data_others(channel_data, date_str, fd)
        except Exception as e:
            logger.error(f"fetch migu playback data failed: {e}")

    def _get_migu_playback_data_cctv(self, name, date_str, tv_name, fd):
        fetch_url = f"https://api.cntv.cn/epg/epginfo3?serviceId=shiyi&d={date_str}&c={tv_name}"
        try:
            resp = requests.get(fetch_url, timeout=Constants.REQUEST_TIMEOUT)
            resp.raise_for_status()
            playback_data = resp.json().get(tv_name, {}).get("program", {})
            if playback_data:
                tvg_id = config_manager.get_channel_id(name)
                display_name = config_manager.get_channel(name)
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
                tvg_id = config_manager.get_channel_id(channel_data.name)
                display_name = config_manager.get_channel(channel_data.name)
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

    def _get_migu_cate_data(self, processed_pids, category_name, pid: str, rate_type: int) -> List[MiguDataInfo]:
        output_data = []

        try:
            migu_url = self._migu_url + pid
            response = requests.get(migu_url, timeout=Constants.REQUEST_TIMEOUT)
            response.raise_for_status()
            json_cate_data = response.json()

            body = json_cate_data.get("body", {})
            data_list = body.get("dataList", [])
            for data in data_list:
                pid = data.get("pID")
                if pid in processed_pids:
                    continue
                pics = data.get("pics", [])
                channel_name = data.get("name")
                # 提前做过滤处理，减少获取URL的调用
                category_info = config_manager.get_category_object(channel_name, category_name)
                if category_info and config_manager.is_exclude(category_info, channel_name):
                    continue
                migu_data_info = MiguDataInfo(channel_name, pid, pics.get("highResolutionH"))
                # migu_video_play_url = self.get_migu_video_url(migu_data_info.name, migu_data_info.pid, rate_type)
                migu_video_play_url = f"{self._tvb_url}/{migu_data_info.pid}"
                if migu_video_play_url:
                    migu_data_info.set_url(migu_video_play_url)
                    output_data.append(migu_data_info)
            return output_data
        except Exception as e:
            logger.error(f"get migu cate data failed: {e}")
            return output_data

    def get_migu_video_url(self, pname, pid, rate_type: int = 3) -> str:
        def _get302URL(source_url):
            target_url = ""
            for retry in range(6):
                try:
                    resp = requests.get(source_url,
                                        allow_redirects=False,
                                        timeout=Constants.REQUEST_TIMEOUT,
                                        verify=False)
                    location = resp.headers.get("Location", "")
                    if not location:
                        continue
                    if not location.startswith("http://bofang"):
                        target_url = location
                        break
                except Exception as e:
                    logger.error(f"请求重试失败: {pname}, {str(e)}")

                if retry < 5:
                    time.sleep(0.15)

            return target_url

        if rate_type >= 3 and (not Constants.MIGU_USERID or not Constants.MIGU_TOKEN):
            url = self._getAndroidURL720p(pname, pid, rate_type)
        else:
            url = self._getAndroidURL(pname, pid, rate_type)

        return _get302URL(url) if url else ""

    def _getAndroidURL720p(self, pname, pid, rate_type: int = 3, enableHDR: bool = True, enableH265: bool = True):
        appVersion = "2600034600"
        appVersionID = f"{appVersion}-99000-201600010010028"
        timestamp = str(round(time.time() * 1000))

        headers = {
            "AppVersion": appVersion,
            "TerminalId": "android",
            "X-UP-CLIENT-CHANNEL-ID": appVersionID,
            "ClientId": getStringMD5(timestamp),
        }

        # 排除 CCTV5 和 CCTV5+
        exclude_pids = {"641886683", "641886773"}
        if pid not in exclude_pids:
            headers["appCode"] = "miguvideo_default_android"

        input_str = timestamp + pid + appVersion[:8]
        md5 = getStringMD5(input_str)

        salt = str(random.randint(0, 999999)).zfill(6) + "25"
        suffix = f"2cac4f2c6c3346a5b34e085725ef7e33migu{salt[:4]}"
        sign = getStringMD5(md5 + suffix)

        enableHDRStr = "&4kvivid=true&2Kvivid=true&vivid=2" if enableHDR else ""
        enableH265Str = "&h265N=true" if enableH265 else ""

        baseURL = "https://play.miguvideo.com/playurl/v1/play/playurl"
        params = (f"?sign={sign}&rateType={rate_type}&contId={pid}&timestamp={timestamp}"
                  f"&salt={salt}&flvEnable=true&super4k=true{enableH265Str}{enableHDRStr}")
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
            logger.debug(f"channel data [{pname}, {pid}], resp [{resp_json.get("code")}, {resp_json.get("rid")}]")
            return playUrl

        pid = respBody.get("content", {}).get("contId", pid)
        return self._getddCalcuURL720p(playUrl, pid)

    def _getddCalcuURL720p(self, puDataURL: str, programId: str) -> str:
        if not puDataURL or not programId:
            return ""

        try:
            puData = puDataURL.split("&puData=")[1]
        except IndexError:
            logger.error("URL中未找到puData参数")
            return ""

        ddCalcu = self._getddCalcu720p(puData, programId)
        return f"{puDataURL}&ddCalcu={ddCalcu}&sv=10004&ct=android"

    def _getddCalcu720p(self, puData, programId) -> str:
        if not puData or not programId:
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

    def _getAndroidURL(self, pname, pid, rate_type: int, enableHDR: bool = True, enableH265: bool = True):
        appVersion = "2600037000"
        appVersionID = f"{appVersion}-99000-200300220100002"
        timestamp = str(round(time.time() * 1000))

        headers = {
            "AppVersion": appVersion,
            "TerminalId": "android",
            "X-UP-CLIENT-CHANNEL-ID": appVersionID,
        }
        if rate_type != 2 and Constants.MIGU_USERID and Constants.MIGU_TOKEN:
            headers["UserId"] = Constants.MIGU_USERID
            headers["UserToken"] = Constants.MIGU_TOKEN

        # 排除 CCTV5 和 CCTV5+
        exclude_pids = {"641886683", "641886773"}
        if pid not in exclude_pids:
            headers["appCode"] = "miguvideo_default_android"

        input_str = timestamp + pid + appVersion[:8]
        md5 = getStringMD5(input_str)

        salt = 1230024
        suffix = f"3ce941cc3cbc40528bfd1c64f9fdf6c0migu0123"
        sign = getStringMD5(md5 + suffix)

        enableHDRStr = "&4kvivid=true&2Kvivid=true&vivid=2" if enableHDR else ""
        enableH265Str = "&h265N=true" if enableH265 else ""

        baseURL = "https://play.miguvideo.com/playurl/v1/play/playurl"
        params = (f"?sign={sign}&rateType={rate_type}&contId={pid}&timestamp={timestamp}"
                  f"&salt={salt}&flvEnable=true&super4k=true"
                  f"{"&ott=true" if rate_type == 9 else ""}"
                  f"{enableH265Str}{enableHDRStr}")

        playUrl = ""
        try:
            resp = requests.get(baseURL + params, headers=headers, timeout=Constants.REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp_json = resp.json()
            if resp_json.get("rid") == 'TIPS_NEED_MEMBER':
                params = (f"?sign={sign}&rateType=3&contId={pid}&timestamp={timestamp}"
                          f"&salt={salt}&flvEnable=true&super4k=true{enableH265Str}{enableHDRStr}")
                resp = requests.get(baseURL + params, headers=headers, timeout=Constants.REQUEST_TIMEOUT)
                resp.raise_for_status()
                resp_json = resp.json()
            respBody = resp_json.get("body", {})
        except Exception as e:
            logger.error("fetch video url failed: ", str(e))
            return playUrl

        url_info = respBody.get("urlInfo")
        if not (url_info and (playUrl := url_info.get("url"))):
            logger.warning(f"channel data [{pname}, {pid}], resp [{resp_json.get("code")}, {resp_json.get("rid")}]")
            return playUrl

        pid = respBody.get("content", {}).get("contId", pid)
        return self._getddCalcuURL(playUrl, pid, "android", rate_type)

    def _getddCalcuURL(self, puDataURL: str, programId: str, client_type: str, rate_type: int) -> str:
        if not puDataURL or not programId:
            return ""

        if client_type not in ["android", "h5"]:
            return ""

        try:
            puData = puDataURL.split("&puData=")[1]
        except IndexError:
            logger.error("URL中未找到puData参数")
            return ""

        ddCalcu = self._getddCalcu(puData, programId, client_type, rate_type)
        suffix = CLIENT_CONFIG[client_type]["suffix"]
        return f"{puDataURL}&ddCalcu={ddCalcu}{suffix}"

    def _getddCalcu(self, puData, programId, client_type: str, rate_type: int) -> str:
        if not puData or not programId:
            return ""

        config = CLIENT_CONFIG.get(client_type)
        keys = config["keys"]
        words = config["words"]
        third_replace_index = config["thirdReplaceIndex"]

        if Constants.MIGU_USERID:
            words1 = CLIENT_CONFIG["android"]["keys"][int(Constants.MIGU_USERID[7])]
            CLIENT_CONFIG["android"]["words"][0] = words1
            CLIENT_CONFIG["h5"]["words"][0] = words1

        if client_type == "android" and rate_type == 2:
            words[0] = "v"

        if 3 < len(Constants.MIGU_USERID) <= 8:
            words[0] = "e"

        ddCalcu = []
        puData_len = len(puData)
        date_prefix = int(datetime.now().strftime("%Y%m%d")[0])
        for i in range(puData_len // 2):
            ddCalcu.append(puData[puData_len - i - 1])
            ddCalcu.append(puData[i])
            match i:
                case 1:
                    ddCalcu.append(words[i - 1])
                case 2:
                    ddCalcu.append(keys[date_prefix])
                case 3:
                    prog_idx = int(programId[third_replace_index])
                    ddCalcu.append(keys[prog_idx])
                case 4:
                    ddCalcu.append(words[i - 1])

        return "".join(ddCalcu)

    def _get_url_body(self, url):
        response = requests.get(url, timeout=Constants.REQUEST_TIMEOUT, verify=False)
        response.raise_for_status()
        resp_json = response.json()
        return resp_json.get("body", {})

    def _get_migu_sport_list(self):
        url = ("https://v0-sc.miguvideo.com/vms-match/v6/staticcache/basic/match-list/normal-match-list/"
               "0/all/default/1/miguvideo/")
        try:
            resp_body = self._get_url_body(url)

            data_list = []
            today_str = datetime.now().strftime("%Y%m%d")
            days = resp_body.get("days", [])
            for i in range(1, min(4, len(days))):
                date_val = days[i]
                if date_val == today_str:
                    relative_date = "体育-今天"
                elif int(date_val) > int(today_str):
                    relative_date = "体育-明天"
                else:
                    relative_date = "体育-昨天"

                if not config_manager.exists(relative_date):
                    continue

                match_list = resp_body.get("matchList", {}).get(date_val, [])
                data_list.append((date_val, relative_date, match_list))

            return data_list
        except Exception:
            return None

    def _get_migu_sport_overed(self, processed_counter, task_id, relative_date, data, body, pk_info_title, mgdb_id):
        try:
            url = f"http://app-sc.miguvideo.com/vms-match/v5/staticcache/basic/all-view-list/{mgdb_id}/2/miguvideo"
            relay_body = self._get_url_body(url)
            replay_list = relay_body.get("replayList")
            if not replay_list:
                replay_list = body.get("multiPlayList", {}).get("replayList")
            if not replay_list:
                return

            for replay in replay_list:
                name = replay.get("name", "")
                if re.search(r".*集锦|训练.*", name):
                    continue
                if re.search(r".*回放|赛.*", name):
                    time_str = body.get("keyword", "")[7:]
                    pre_list = body.get("multiPlayList", {}).get("preList", [])
                    if pre_list:
                        start_time_str = pre_list[-1].get("startTimeStr")
                        if start_time_str:
                            time_str = start_time_str[11:16]
                    competition_desc = f"{data.get('competitionName')} {pk_info_title} {name} {time_str}"
                    category_info = config_manager.get_category_object(competition_desc, relative_date)
                    if category_info and config_manager.is_exclude(category_info, competition_desc):
                        continue
                    # migu_video_play_url = self.get_migu_video_url(competition_desc, replay.get("pID"))
                    migu_video_play_url = f"{self._tvb_url}/{replay.get("pID")}"
                    if migu_video_play_url:
                        channel_manager.add_channel(False, relative_date,
                                                    competition_desc,
                                                    migu_video_play_url,
                                                    pk_info_title,
                                                    data.get("competitionLogo"))
                        processed_counter.increment()
            task_manager.update_task(task_id, processed=processed_counter.get_value())
        except Exception as e:
            logger.error(f"get migo sport overed [{pk_info_title}] failed,  {str(e)}")


parser_manager = Parser()
