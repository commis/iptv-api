class MiguCateInfo:

    def __init__(self, name: str, vid: str):
        self._name = name
        self._vid = vid

    @property
    def name(self):
        return self._name

    @property
    def vid(self):
        return self._vid


class MiguDataInfo:

    def __init__(self, name: str, pid: str, pic: str):
        self._name = name
        self._pid = pid
        self._pic = pic
        self._url = None

    @property
    def name(self):
        return self._name

    @property
    def pid(self):
        return self._pid

    @property
    def pic(self):
        return self._pic

    @property
    def url(self):
        return self._url

    def set_url(self, url):
        self._url = url
