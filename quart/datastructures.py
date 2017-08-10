from typing import Any, List

from multidict import CIMultiDict as AIOCIMultiDict, MultiDict as AIOMultiDict


class MultiDict(AIOMultiDict):

    def getlist(self, key: str) -> List[Any]:
        return self.getall(key)


class CIMultiDict(AIOCIMultiDict):

    def getlist(self, key: str) -> List[Any]:
        return self.getall(key)
