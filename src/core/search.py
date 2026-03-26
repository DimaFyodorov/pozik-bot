"""Web search integration."""

import logging

from googlesearch import search

logger = logging.getLogger(__name__)


class SearchEngine:
    """Web search using Google."""

    SEARCH_TRIGGERS = {
        'найди',
        'гугли',
        'поиск',
        'инфо',
        'новости',
        'цена',
        'курс',
        'кто',
        'что',
        'где',
        'когда',
        'почему',
        'проверь',
        'узнай',
    }

    async def search(self, query: str) -> list[str] | None:
        """Search if query contains trigger words."""
        query_lower = query.lower()

        if not any(trigger in query_lower for trigger in self.SEARCH_TRIGGERS):
            return None

        if len(query) < 5:
            return None

        try:
            results = list(search(query, num_results=4, advanced=True))
            logger.info('Found %d search results', len(results))
            return results
        except Exception as e:
            logger.exception('Search failed: %s', e)
            return None

    def format_results(self, results: list[str]) -> str:
        """Format search results for context."""
        if not results:
            return ''

        lines = ['\n📚 Результаты поиска:']
        for i, result in enumerate(results[:4], 1):
            lines.append(f'{i}. {result}')

        return '\n'.join(lines)
