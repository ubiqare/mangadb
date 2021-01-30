import re
import datetime

import bs4

from typing import Pattern, Optional, Match, cast, ClassVar, Dict, Any, TYPE_CHECKING

from .base import BaseMangaExtractor, MangaExtractorData
from ..constants import STATUS_IDS, CENSOR_IDS

if TYPE_CHECKING:
    from ..ext_info import ExternalInfo


class ManganeloExtractor(BaseMangaExtractor):
    site_name: ClassVar[str] = "Manganelo"
    site_id: ClassVar[int] = 4

    URL_PATTERN_RE: ClassVar[Pattern] = re.compile(
            r"(?:https?://)?(m\.|chap\.)?manganelo\.com/manga-([a-z]{2}\d+)")

    # subdomain = m|chap; you can't use m. for chap. but the other way around works!?!??!
    BASE_URL: ClassVar[str] = "https://{subdomain}.manganelo.com"
    # use double braces to get on brace
    MANGA_URL: ClassVar[str] = f"{BASE_URL}/manga-{{manga_id}}"

    def __init__(self, url: str):
        super().__init__(url)
        self.id_onpage: str = self.book_id_from_url(url)
        self.cover_url: Optional[str] = None
        self.export_data: Optional[MangaExtractorData] = None

    @classmethod
    def match(cls, url: str) -> bool:
        """
        Returns True on URLs the extractor is compatible with
        """
        return bool(cls.URL_PATTERN_RE.match(url))

    def extract(self) -> Optional[MangaExtractorData]:
        if self.export_data is None:
            html = self.get_html(self.url)
            if html is None:
                return None
            data_dict = self._extract_info(html)

            self.export_data = MangaExtractorData(
                pages=0,
                language='Unknown',
                category=['Manga'],
                collection=[],
                groups=[],
                parody=[],
                character=[],
                url=self.url,
                id_onpage=self.id_onpage,
                imported_from=ManganeloExtractor.site_id,
                uploader=None,
                favorites=None,
                censor_id=cast(int, CENSOR_IDS['Unknown']),
                **data_dict)

        return self.export_data

    def _extract_info(self, html: str) -> Dict[str, Any]:
        res: Dict[str, Any] = {}

        soup = bs4.BeautifulSoup(html, "html.parser")
        cover_url = soup.select_one("div.story-info-left span.info-image img")
        self.cover_url = cover_url['src']

        book_data = soup.select_one("div.panel-story-info div.story-info-right")
        res['title_eng'] = book_data.find("h1").text

        # table_labels = book_data.select("td.table-label")
        table_vals = book_data.select("td.table-value")

        # assuming the following order in the table: 1. alternative 2. authors 3. status 4. genres

        # separated by ';'
        alternative_titles = [s.strip() for s in table_vals[0].text.split(';')]
        if alternative_titles:
            # @Incomplete take first non-latin title; alnum() supports unicode and thus returns
            # true for """"alphanumeric"""" japanese symbols !?!?
            non_latin = [s for s in alternative_titles if ord(s[0]) > 128]
            if non_latin:
                res['title_foreign'] = non_latin[0]
            else:
                res['title_foreign'] = alternative_titles[0]

        # as anchor text
        res['artist'] = [anch.text.strip() for anch in table_vals[1].select('a')]

        status = table_vals[2].text
        try:
            res['status_id'] = STATUS_IDS[status]
        except KeyError:
            res['status_id'] = STATUS_IDS['Unknown']

        # genres
        res['tag'] = [anch.text.strip() for anch in table_vals[3].select('a')]
        res['nsfw'] = 1 if ('Ecchi' in res['tag'] or 'Mature' in res['tag']) else 0

        # could use Updated as upload_date, but it really doesn't have _one_
        res['upload_date'] = datetime.date.min

        # e.g.: MangaNelo.com rate : 4.82 / 5 - 2470 votes
        # some mangas dont have a rating e.g.: https://chap.manganelo.com/manga-hc121796
        # (presumably ones on chap. subdomain)
        rate_cont = book_data.select_one('#rate_row_cmd')
        if rate_cont:
            rating, ratings = rate_cont.text.split(' / ')
            rating = rating.split()[-1]
            ratings = ratings.split('-')[1].split()[0]
            res['rating'] = float(rating)
            res['ratings'] = int(ratings)
        else:
            res['rating']  = None
            res['ratings'] = None

        # description @CleanUp passed as note + ignoring formatting
        description = soup.select_one('#panel-story-info-description')
        res['note'] = description.text if description else None

        return res

    def get_cover(self) -> Optional[str]:
        return self.cover_url

    @classmethod
    def book_id_from_url(cls, url: str) -> str:
        # assumes this is only called on urls that already match the extractor
        match = cast(Match, cls.URL_PATTERN_RE.match(url))
        # omit '.' at end of subdomain
        return f"{match.group(1)[:-1]}##{match.group(2)}"

    @classmethod
    def url_from_ext_info(cls, ext_info: 'ExternalInfo') -> str:
        subdomain, manga_id = ext_info.id_onpage.split('##')
        return cls.MANGA_URL.format(subdomain=subdomain, manga_id=manga_id)
        
    @classmethod
    def read_url_from_ext_info(cls, ext_info: 'ExternalInfo') -> str:
        # @CleanUp just uses first chapter currently
        # must use chap. subdomain for chapter view
        _, manga_id = ext_info.id_onpage.split('##')
        return f"{cls.MANGA_URL.format(subdomain='chap', manga_id=manga_id)}/chapter-1"
