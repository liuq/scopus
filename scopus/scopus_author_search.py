import os
import sys
import xml.etree.ElementTree as ET
import json

from scopus.utils import download, ns
from scopus.scopus_api import ScopusAbstract

SCOPUS_AUTHOR_SEARCH_DIR = os.path.expanduser('~/.scopus/author_search')

if not os.path.exists(SCOPUS_AUTHOR_SEARCH_DIR):
    os.makedirs(SCOPUS_AUTHOR_SEARCH_DIR)


FIELDS = ['eid', 'preferred-name', 'affiliation-current']

class ScopusAuthorSearch(object):
    @property
    def authors(self):
        """List of Authors retrieved."""
        return self._AUTHORS

    def __init__(self, query, fields=FIELDS, count=200, start=0, max_entries=5000, 
                 refresh=False):
        """Class to search a query, and retrieve a list of author IDs as results.

        Parameters
        ----------
        query : str
            A string of the query. E.g. "authlast(Einstein) and authfirst(Albert)"
        
        fields : str (optional, default=['eid', 'preferred-name', 
            'affiliation-current'])
            The fields you want returned.  Allowed fields are specified in
            https://dev.elsevier.com/guides/AuthorSearchViews.htm.  
        
        count : int (optional, default=200)
            The number of entries to be displayed at once.  A smaller number
            means more queries with each query having less results.

        start : int (optional, default=0)
            The entry number of the first search item to start with.

        refresh : bool (optional, default=False)
            Whether to refresh the cached file if it exists or not.
            
        max_entries : int (optional, default=5000)
            Raise error when the number of results is beyond this number.
            The Scopus Search Engine does not allow more than 5000 entries.
        
        Raises
        ------
        Exception
            If the number of search results exceeds max_entries.

        Notes
        -----
        XML results are cached in ~/.scopus/author_search/{query}.

        The Authors are stored as a property named Authors.
        """

        qfile = os.path.join(SCOPUS_AUTHOR_SEARCH_DIR,
                             # We need to remove / in a DOI here so we can save
                             # it as a file.
                             query.replace('/', '_slash_'))

        if os.path.exists(qfile) and not refresh:
            self._AUTHORS = []
            with open(qfile) as f:
                for r in f.readlines():
                    self._AUTHORS.append(json.loads(r))
        else:
            # No cached file exists, or we are refreshing.
            # First, we get a count of how many things to retrieve
            url = 'https://api.elsevier.com/content/search/author'
            params = { 'query': query, 'count': 0, 'start': 0 }
            xml = download(url=url, params=params).text.encode('utf-8')
            results = ET.fromstring(xml)

            N = results.find('opensearch:totalResults', ns)
            try:
                N = int(N.text)
            except:
                N = 0

            if N > max_entries:
                raise Exception(('N = {}. '
                                 'Set max_entries to a higher number or '
                                 'change your query ({})').format(N, query))

            self._AUTHORS = []
            while N > 0:
                params = {'query': query, 
                          'count': count, 'start': start}
                resp = download(url=url, params=params, accept="json")
                results = resp.json()

                if 'entry' in results.get('search-results', []):
                    for r in results['search-results']['entry']:
                        self._AUTHORS.append({f: r[f] for f in fields if f in r})
                start += count
                N -= count

            with open(qfile, 'wb') as f:
                for author in self._AUTHORS:
                    f.write('{}\n'.format(json.dumps(author)).encode('utf-8'))

    def __str__(self):
        s = """{query}
        Resulted in {N} hits.
    {entries}"""
        return s.format(self=self,
                        N=len(self._AUTHORS),
                        entries='\n    '.join(self._AUTHORS))
   