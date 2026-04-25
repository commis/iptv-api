import os
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter

from core.logger_factory import LoggerFactory
from services import config_manager

router = APIRouter(prefix="/site", tags=["点播接口"])
logger = LoggerFactory.get_logger(__name__)

# 定义分类 ID 映射（横向导航）
_VOD_CATEGORIES = [
    {"type_id": "1", "type_name": "大语文"},
    {"type_id": "2", "type_name": "数学"},
    {"type_id": "3", "type_name": "物理"},
    {"type_id": "4", "type_name": "化学"},
    {"type_id": "5", "type_name": "生物"},
    {"type_id": "6", "type_name": "历史"},
    {"type_id": "7", "type_name": "政治"},
    {"type_id": "8", "type_name": "地理"},
]


def get_category_name(tid):
    for c in _VOD_CATEGORIES:
        if c['type_id'] == tid:
            return c['type_name']
    return None


@router.get("/vod", summary="查询点播数据")
def get_vod(
    ac: Optional[str] = None,
    t: Optional[str] = None,  # 分类ID
    ids: Optional[str] = None,  # 详情ID (格式: 分类/文件名.txt)
    wd: Optional[str] = None,  # 搜索关键词
    pg: int = 1  # 分页
):
    logger.info(f"Receive vod: ac={ac}, t={t}, ids={ids}, wd={wd}, pg={pg}")
    base_dir = config_manager.site_cnconfig.get("base")

    # 1. 搜索逻辑：必须放在最前面，因为搜索时 ac 可能为 None
    if wd:
        search_results = []
        for cat in _VOD_CATEGORIES:
            cat_name = cat['type_name']
            path = os.path.join(base_dir, cat_name)
            if not os.path.exists(path): continue

            for fname in os.listdir(path):
                if wd.lower() in fname.lower() and fname.endswith('.txt'):
                    pic, remarks = "", ""
                    try:
                        with open(os.path.join(path, fname), 'r', encoding='utf-8') as f:
                            for _ in range(10):
                                line = f.readline().strip()
                                if line.startswith("PIC$"): pic = line.replace("PIC$", "")
                                if line.startswith("REMARKS$"): remarks = line.replace("REMARKS$", "")
                    except:
                        pass

                    search_results.append({
                        "vod_id": f"{cat_name}/{fname}",
                        "vod_name": fname.replace('.txt', ''),
                        "vod_pic": pic,
                        "type_name": cat_name,
                        "vod_remarks": remarks or "搜索结果"
                    })
        return {"list": search_results, "total": len(search_results), "page": 1, "pagecount": 1}

    # 2. 详情逻辑：处理具体的播放视频请求
    if ac == 'detail' and ids:
        file_path = os.path.join(base_dir, unquote(ids))
        if os.path.exists(file_path):
            pic, content, play_urls = "", "暂无简介", []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    if line.startswith("PIC$"):
                        pic = line.replace("PIC$", "")
                    elif line.startswith("CONTENT$"):
                        content = line.replace("CONTENT$", "")
                    elif line.startswith("REMARKS$"):
                        continue
                    else:
                        play_urls.append(line)

            return {
                "list": [{
                    "vod_id": ids,
                    "vod_name": os.path.basename(ids).replace('.txt', ''),
                    "vod_pic": pic,
                    "vod_content": content,
                    "vod_play_from": "在线直链",
                    "vod_play_url": "#".join(play_urls)
                }]
            }

    # 3. 分类内容请求：适配 ac=list&t=1 和 ac=detail&t=1 (OK影视特征)
    if t:
        cat_name = get_category_name(unquote(str(t)))
        cat_path = os.path.join(base_dir, cat_name)
        vlist = []
        if os.path.exists(cat_path):
            for fname in sorted(os.listdir(cat_path)):
                if fname.endswith('.txt'):
                    pic, remarks = "", ""
                    try:
                        with open(os.path.join(cat_path, fname), 'r', encoding='utf-8') as f:
                            for _ in range(5):
                                line = f.readline().strip()
                                if line.startswith("PIC$"):
                                    pic = line.replace("PIC$", "")
                                elif line.startswith("REMARKS$"):
                                    remarks = line.replace("REMARKS$", "")
                    except:
                        pass

                    vlist.append({
                        "vod_id": f"{cat_name}/{fname}",
                        "vod_name": fname.replace('.txt', ''),
                        "vod_pic": pic,
                        "vod_remarks": remarks
                    })
        return {"list": vlist, "total": len(vlist), "page": pg, "pagecount": 1}

    # 4. 兜底逻辑：无参数时返回分类定义
    return {
        "class": _VOD_CATEGORIES,
        "list": [],
        "total": 0, "page": 1, "pagecount": 1, "limit": 20
    }
