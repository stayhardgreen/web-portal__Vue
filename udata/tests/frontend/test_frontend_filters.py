# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date

from flask import url_for, render_template_string, g, Blueprint

from . import FrontTestCase

from udata.i18n import I18nBlueprint
from udata.models import db, TerritorialCoverage, GeoCoverage, TerritoryReference
from udata.frontend.helpers import in_url
from udata.core.territories import register_level


class FrontEndRootTest(FrontTestCase):
    def test_rewrite(self):
        '''url_rewrite should replace a parameter in the URL if present'''
        url = url_for('front.home', one='value', two='two')
        expected = self.full_url('front.home', one='other-value', two=2)

        with self.app.test_request_context(url):
            result = render_template_string("{{ url_rewrite(one='other-value', two=2) }}")

        self.assertEqual(result, expected)

    def test_rewrite_append(self):
        '''url_rewrite should replace a parameter in the URL if present'''
        url = url_for('front.home')
        expected = self.full_url('front.home', one='value')

        with self.app.test_request_context(url):
            result = render_template_string("{{ url_rewrite(one='value') }}")

        self.assertEqual(result, expected)

    def test_url_add(self):
        '''url_add should add a parameter to the URL'''
        url = url_for('front.home', one='value')

        result = render_template_string("{{ url|url_add(two='other') }}", url=url)

        self.assertEqual(result, url_for('front.home', one='value', two='other'))

    def test_url_add_append(self):
        '''url_add should add a parameter to the URL even if exists'''
        url = url_for('front.home', one='value')
        expected = url_for('front.home', one=['value', 'other-value'])

        result = render_template_string("{{ url|url_add(one='other-value') }}", url=url)

        self.assertEqual(result, expected)

    def test_url_del_by_name(self):
        '''url_del should delete a parameter by name from the URL'''
        url = url_for('front.home', one='value', two='other')
        expected = url_for('front.home', two='other')

        result = render_template_string("{{ url|url_del('one') }}", url=url)

        self.assertEqual(result, expected)

    def test_url_del_by_value(self):
        '''url_del should delete a parameter by value from the URL'''
        url = url_for('front.home', one=['value', 'other-value'], two='other')
        expected = url_for('front.home', one='value', two='other')

        result = render_template_string("{{ url|url_del(one='other-value') }}", url=url)

        self.assertEqual(result, expected)

    def test_url_del_by_value_not_string(self):
        '''url_del should delete a parameter by value from the URL'''
        url = url_for('front.home', one=['value', 42], two='other')
        expected = url_for('front.home', one='value', two='other')

        result = render_template_string("{{ url|url_del(one=42) }}", url=url)

        self.assertEqual(result, expected)

    def test_args_in_url(self):
        '''in_url() should test the presence of a key in url'''
        url = url_for('front.home', key='value', other='other')

        with self.app.test_request_context(url):
            self.assertTrue(in_url('key'))
            self.assertTrue(in_url('other'))
            self.assertTrue(in_url('key', 'other'))
            self.assertFalse(in_url('fake'))
            self.assertFalse(in_url('key', 'fake'))

    def test_kwargs_in_url(self):
        '''in_url() should test the presence of key/value pair in url'''
        url = url_for('front.home', key='value', other='other')

        with self.app.test_request_context(url):
            self.assertTrue(in_url(key='value'))
            self.assertTrue(in_url(key='value', other='other'))
            self.assertFalse(in_url(key='other'))
            self.assertFalse(in_url(key='value', other='value'))

            self.assertTrue(in_url('other', key='value'))

    def test_as_filter(self):
        '''URL helpers should exists as filter'''
        url = url_for('front.home', one='value')

        self.assertEqual(
            render_template_string("{{ url|url_rewrite(one='other-value') }}", url=url),
            url_for('front.home', one='other-value')
        )
        self.assertEqual(
            render_template_string("{{ url|url_add(two='other-value') }}", url=url),
            url_for('front.home', one='value', two='other-value')
        )
        self.assertEqual(
            render_template_string("{{ url|url_del('one') }}", url=url),
            url_for('front.home')
        )

    def test_as_global(self):
        '''URL helpers should exists as global function'''
        url = url_for('front.home', one='value')

        self.assertEqual(
            render_template_string("{{ url_rewrite(url, one='other-value') }}", url=url),
            url_for('front.home', one='other-value')
        )
        self.assertEqual(
            render_template_string("{{ url_add(url, two='other-value') }}", url=url),
            url_for('front.home', one='value', two='other-value')
        )
        self.assertEqual(
            render_template_string("{{ url_del(url, 'one') }}", url=url),
            url_for('front.home')
        )

    def test_as_global_default(self):
        '''URL helpers should exists as global function without url parameter'''
        url = url_for('front.home', one='value')

        with self.app.test_request_context(url):
            self.assertEqual(
                render_template_string("{{ url_rewrite(one='other-value') }}"),
                self.full_url('front.home', one='other-value')
            )
            self.assertEqual(
                render_template_string("{{ url_add(two='other-value') }}"),
                self.full_url('front.home', one='value', two='other-value')
            )
            self.assertEqual(
                render_template_string("{{ url_del(None, 'one') }}"),
                self.full_url('front.home')
            )
            self.assertEqual(
                render_template_string("{{ in_url('one') }}"),
                'True'
            )
            self.assertEqual(
                render_template_string("{{ in_url('one') }}"),
                'True'
            )
            self.assertEqual(
                render_template_string("{{ in_url('two') }}"),
                'False'
            )

    def test_daterange(self):
        '''Daterange filter should display range in an adaptive'''
        g.lang_code = 'en'
        iso2date = lambda s: date(*[int(v) for v in s.split('-')])
        dr = lambda s, e: db.DateRange(start=iso2date(s), end=iso2date(e))

        specs = (
            (dr('2014-02-01', '2014-02-01'), '2014/02/01'),
            (dr('2012-01-01', '2012-01-31'), '2012/01'),
            (dr('2012-01-01', '2012-01-14'), '2012/01/01 to 2012/01/14'),
            (dr('2012-01-01', '2012-03-31'), '2012/01 to 2012/03'),
            (dr('2012-01-01', '2012-02-29'), '2012/01 to 2012/02'),
            (dr('2012-01-01', '2012-12-31'), '2012'),
            (dr('2012-01-01', '2014-12-31'), '2012 to 2014'),
            (dr('2012-02-02', '2014-12-25'), '2012/02/02 to 2014/12/25'),
        )
        for given, expected in specs:
            self.assertEqual(
                render_template_string('{{given|daterange}}', given=given),
                expected
            )

    def test_daterange_before_1900(self):
        '''Daterange filter should display range in an adaptive'''
        g.lang_code = 'en'
        iso2date = lambda s: date(*[int(v) for v in s.split('-')])
        dr = lambda s, e: db.DateRange(start=iso2date(s), end=iso2date(e))

        specs = (
            (dr('1234-02-01', '1234-02-01'), '1234/02/01'),
            (dr('1232-01-01', '1232-01-31'), '1232/01'),
            (dr('1232-01-01', '1232-01-14'), '1232/01/01 to 1232/01/14'),
            (dr('1232-01-01', '1232-03-31'), '1232/01 to 1232/03'),
            (dr('1232-01-01', '1232-02-29'), '1232/01 to 1232/02'),
            (dr('1232-01-01', '1232-12-31'), '1232'),
            (dr('1232-01-01', '1234-12-31'), '1232 to 1234'),
            (dr('1232-02-02', '1234-12-25'), '1232/02/02 to 1234/12/25'),
        )
        for given, expected in specs:
            self.assertEqual(
                render_template_string('{{given|daterange}}', given=given),
                expected
            )

    def test_daterange_bad_type(self):
        '''Daterange filter should only accept db.DateRange as parameter'''
        with self.assertRaises(ValueError):
            render_template_string('{{"value"|daterange}}')

    def test_ficon(self):
        '''Should choose a font icon between glyphicon and font-awesome'''
        self.assertEqual(render_template_string('{{ficon("icon")}}'), 'glyphicon glyphicon-icon')
        self.assertEqual(render_template_string('{{ficon("fa-icon")}}'), 'fa fa-icon')

    def test_i18n_alternate_links(self):
        test = I18nBlueprint('test', __name__)

        @test.route('/i18n/<key>/')
        def i18n(key):
            return render_template_string('{{ i18n_alternate_links() }}')

        self.app.register_blueprint(test)
        self.app.config['DEFAULT_LANGUAGE'] = 'en'
        self.app.config['LANGUAGES'] = {
            'en': 'English',
            'fr': 'Français',
            'de': 'German',
        }

        response = self.get(url_for('test.i18n', key='value', param='other'))
        self.assertEqual(response.data, ''.join([
            '<link rel="alternate" href="/fr/i18n/value/?param=other" hreflang="fr" />',
            '<link rel="alternate" href="/de/i18n/value/?param=other" hreflang="de" />',
        ]))

    def test_i18n_alternate_links_outside_i18n_blueprint(self):
        test = Blueprint('test', __name__)

        @test.route('/not-i18n/<key>/')
        def i18n(key):
            return render_template_string('{{ i18n_alternate_links() }}')

        self.app.register_blueprint(test)
        self.app.config['DEFAULT_LANGUAGE'] = 'en'
        self.app.config['LANGUAGES'] = {
            'en': 'English',
            'fr': 'Français',
            'de': 'German',
        }

        response = self.get(url_for('test.i18n', key='value', param='other'))
        self.assertEqual(response.data, '')

    def test_territorial_coverage_empty(self):
        test = Blueprint('test', __name__)

        @test.route('/coverage/')
        def coverage():
            coverage = TerritorialCoverage()
            return render_template_string('{{ coverage|territorial_coverage }}', coverage=coverage)

        self.app.register_blueprint(test)

        response = self.get(url_for('test.coverage'))
        self.assertEqual(response.data, '')

    def test_territorial_coverage_labelize(self):
        test = Blueprint('test', __name__)

        specs = {
            'MetropoleOfCountry/FR/FRANCE METROPOLITAINE': 'France Metropolitaine',
            'Country/FR/FRANCE': 'France',
            'OverseasOfCountry/FR/FRANCE D OUTRE MER': 'France D Outre Mer',  # Ugly
            'RegionOfFrance/02/MARTINIQUE': 'Martinique',
            'CommuneOfFrance/44109/44000 NANTES': '44000 Nantes',
            'InternationalOrganization/UE/UNION EUROPEENNE': 'Union Europeenne',
            'OverseasCollectivityOfFrance/975/975 ST PIERRE ET MIQUELON': '975 St Pierre Et Miquelon',
            'IntercommunalityOfFrance/241300177/SAN OUEST PROVENCE': 'San Ouest Provence',
            'DepartmentOfFrance/60/60 OISE': '60 Oise',
        }

        @test.route('/coverage/<path:value>/')
        def coverage(value):
            coverage = TerritorialCoverage(codes=[value])
            return render_template_string('{{ coverage|territorial_coverage }}', coverage=coverage)

        self.app.register_blueprint(test)

        for value, expected in specs.items():
            response = self.get(url_for('test.coverage', value=value))
            self.assertEqual(response.data, expected)

    def test_territorial_coverage_priority(self):
        test = Blueprint('test', __name__)

        codes = [
            'MetropoleOfCountry/FR/FRANCE METROPOLITAINE',
            'Country/FR/FRANCE',
            'OverseasOfCountry/FR/FRANCE D OUTRE MER',
            'RegionOfFrance/02/MARTINIQUE',
            'CommuneOfFrance/44109/44000 NANTES',
            'InternationalOrganization/UE/UNION EUROPEENNE',
            'OverseasCollectivityOfFrance/975/975 ST PIERRE ET MIQUELON',
            'IntercommunalityOfFrance/241300177/SAN OUEST PROVENCE',
            'DepartmentOfFrance/60/60 OISE',
        ]

        @test.route('/coverage/')
        def coverage():
            coverage = TerritorialCoverage(codes=codes)
            return render_template_string('{{ coverage|territorial_coverage }}', coverage=coverage)

        self.app.register_blueprint(test)

        response = self.get(url_for('test.coverage'))
        self.assertEqual(response.data, 'Union Europeenne')

    def test_geolabel_empty(self):
        test = Blueprint('test', __name__)

        @test.route('/geolabel/')
        def geolabel():
            coverage = GeoCoverage()
            return render_template_string('{{ coverage|geolabel }}', coverage=coverage)

        self.app.register_blueprint(test)

        response = self.get(url_for('test.geolabel'))
        self.assertEqual(response.data, '')

    def test_geolabel(self):
        test = Blueprint('test', __name__)

        specs = {
            ('country', 'fr'): 'France',
            ('region', '02'): 'Martinique',
            ('town', '44109'): 'Nantes',
            ('country-group', 'ue'): 'Union Europeenne',
            ('epci', '241300177'): 'San Ouest Provence',
            ('county', '60'): 'Oise',
        }

        @test.route('/geolabel/<level>/<code>/')
        def geolabel(level, code):
            label = specs[(level, code)]
            territory = TerritoryReference(name=label, level=level, code=code)
            coverage = GeoCoverage(territories=[territory])
            return render_template_string('{{ coverage|geolabel}}', coverage=coverage)

        self.app.register_blueprint(test)

        for (level, code), label in specs.items():
            response = self.get(url_for('test.geolabel', level=level, code=code))
            self.assertEqual(response.data, label)

    def test_geolabel_priority(self):
        test = Blueprint('test', __name__)

        register_level('country', 'fake', 'Fake level')

        coverage = GeoCoverage(territories=[
            TerritoryReference(name='France', level='country', code='fr'),
            TerritoryReference(name='Fake', level='fake', code='fake'),
            TerritoryReference(name='Union Européenne', level='country-group', code='ue'),
        ])

        @test.route('/geolabel/')
        def geolabel():
            return render_template_string('{{ coverage|geolabel }}', coverage=coverage)

        self.app.register_blueprint(test)

        response = self.get(url_for('test.geolabel'))
        self.assertEqual(response.data.decode('utf8'), 'Union Européenne')
