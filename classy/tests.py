import unittest
from datetime import datetime

import classy.app

class MockClient():
    _terms = [
        {
            u'id': u'201700',
            u'type': u'term',
            u'attributes': {u'code': u'201700',
                            u'description': u'Summer 2016',
                            u'startDate': u'2016-06-20',
                            u'endDate': u'2016-09-02',
                            u'financialAidYear': u'1617',
                            u'housingEndDate': u'2016-09-03',
                            u'housingStartDate': u'2016-06-19'},
            u'links': None,
        },
        {
            u'id': u'201701',
            u'type': u'term',
            u'attributes': {u'code': u'201701',
                            u'description': u'Fall 2017',
                            u'startDate': u'2016-09-20',
                            u'endDate': u'2017-01-01',
                            u'financialAidYear': u'1718',
                            u'housingEndDate': u'2016-09-21',
                            u'housingStartDate': u'2017-01-01'},
            u'links': None,
        },
    ]

    def __init__(self):
        self.calls = 0

    def open_terms(self):
        self.calls += 1
        return {u'data': self._terms}

    def term(self, id):
        for term in self._terms:
            if term[u'id'] == id:
                return {u'data': term}
        assert False, "looked up term which doesn't exist"

class ClassyTestCase(unittest.TestCase):
    def test_current_term(self):
        client = MockClient()

        # Summer
        now = datetime(2016, 7, 1)
        term = classy.app.get_current_term(client, _now=lambda: now)
        assert term is not None and term[u'id'] == '201700', "expected the current term to be summer"
        assert client.calls == 1, "open_terms called %d times, expected 1" % client.calls
        assert classy.app._current_term is not None, "expected a cached term"
        assert classy.app._current_term[u'id'] == u'201700', "expected the cached term to be summer"

        # test that caching works
        term = classy.app.get_current_term(client, _now=lambda: now)
        assert term is not None and term[u'id'] == '201700', "expected the current term to be summer"
        assert client.calls == 1, "open_terms called %d times, expected 1" % client.calls

        # Between terms
        now = datetime(2016, 9, 10)
        term = classy.app.get_current_term(client, _now=lambda: now)
        assert term is None, "expected no current term"
        assert client.calls == 2, "open_terms called %d times, expected 2" % client.calls
        assert classy.app._current_term is not None, "expected a cached term"
        assert classy.app._current_term['id'] == u'201701', "expected the cached term to be fall"

        # test that caching works
        term = classy.app.get_current_term(client, _now=lambda: now)
        assert term is None, "expected no current term"
        assert client.calls == 2, "open_terms called %d times, expected 2" % client.calls

        # Fall
        now = datetime(2016, 10, 1)
        term = classy.app.get_current_term(client, _now=lambda: now)
        assert term is not None and term[u'id'] == '201701', "current term is %s, expected fall" % repr(term)
        assert client.calls == 2, "open_terms called %d times, expected 2" % client.calls
        assert classy.app._current_term is not None, "expected a cached term"
        assert classy.app._current_term[u'id'] == u'201701', "expected the cached term to be fall"

        # test that caching works
        term = classy.app.get_current_term(client, _now=lambda: now)
        assert term is not None and term[u'id'] == '201701', "current term is %s, expected fall" % repr(term)
        assert client.calls == 2, "open_terms called %d times, expected 2" % client.calls

if __name__ == '__main__':
    unittest.main()
