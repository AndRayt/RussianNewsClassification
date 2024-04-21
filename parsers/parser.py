from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

import pandas as pd


@dataclass
class ParseEntity:
    id: int
    date: datetime
    link: str
    title: str
    text: str
    tags: List = field(default_factory=list)
    metadata: List = field(default_factory=list)

    def to_dict(self, ru_date_format: bool = True, list_sep: str = ',', stop_symbols: List = None) -> Dict:
        stop_symbols = stop_symbols if stop_symbols else []
        result = deepcopy(self.__dict__)
        date_format = "%d.%m.%Y %H:%M" if ru_date_format else "%m.%d.%Y %H:%M"
        result['date'] = result['date'].strftime(date_format) if result['date'] is not None else ""
        for stop_symbol in stop_symbols:
            result['title'] = result['title'].replace(stop_symbol, ' ')
            result['text'] = result['text'].replace(stop_symbol, ' ')
        result['tags'] = list_sep.join(result['tags'])
        result['metadata'] = list_sep.join(result['metadata'])
        return result


class ParseResult:
    def __init__(self):
        self.entities: Dict[int, ParseEntity] = dict()

    def add_entity(self, entity: ParseEntity):
        self.entities[entity.id] = entity

    def pop_entity(self, entity_id: int) -> ParseEntity:
        return self.entities.pop(entity_id)

    def get_entity(self, entity_id: int) -> ParseEntity:
        return self.entities[entity_id]

    def to_csv(self, save_path: str, ru_date_format=True, sep=';'):
        df = pd.DataFrame([entity.to_dict(ru_date_format, stop_symbols=[sep, ]) for entity in self.entities.values()])
        df.to_csv(save_path, index=False, sep=sep)

    def to_excel(self, save_path: str, ru_date_format=True):
        df = pd.DataFrame([entity.to_dict(ru_date_format) for entity in self.entities.values()])
        df.to_excel(save_path, index=False)


class Parser:
    def __int__(self, start_url: str = ""):
        self.start_url = start_url

    def parse(self, news_num: int) -> ParseResult:
        pass
