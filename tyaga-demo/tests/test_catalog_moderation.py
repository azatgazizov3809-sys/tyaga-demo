import copy
import json
import unittest
import engine
from catalog_schema import CATEGORIES, CATEGORY_GROUPS, FIELDS, applicable


class CatalogModerationTests(unittest.TestCase):
    def setUp(self): self.state = engine.seed()

    def call(self, action, **data):
        result = json.loads(engine.request(json.dumps(self.state), action, json.dumps(data)))
        self.assertTrue(result['ok'], result.get('error'))
        self.state = result['state']
        return result['result']

    def rejected(self, action, **data):
        result = json.loads(engine.request(json.dumps(self.state), action, json.dumps(data)))
        self.assertFalse(result['ok'], result)
        self.assertNotIn('state', result)

    def ids(self, **f): return self.call('catalog', filters=f)['ids']

    def test_categories_aliases_budget_and_suggestions(self):
        self.assertEqual(set(CATEGORY_GROUPS), {'cars','commercial','moto','water'})
        self.assertEqual(self.ids(section='cars', q='тойота камри до 3 млн'), ['102'])
        self.assertEqual(set(self.ids(q='ямаха')), {'201','202'})
        self.assertEqual(set(self.ids(q='вольво')), {'1','7'})
        self.assertEqual(set(self.ids(section='water')), {'301','302'})
        self.assertEqual(set(self.ids(section='commercial')), set(str(i) for i in (1,2,3,7,8,9,10,11,12,13,14,16)))
        self.assertTrue(self.call('search_suggest',q='тойота')['items'])
        self.assertFalse(self.call('search_suggest',q='тойота',section='moto')['items'])
        self.rejected('catalog',filters={'section':'cars','category':'tractor'})

    def test_facets_or_within_and_across(self):
        self.assertEqual(set(self.ids(brand='Toyota,Yamaha')), {'101','102','201','202'})
        self.assertEqual(set(self.ids(section='cars', brand=['Toyota','Yamaha'], max_engine_cc=2100)), {'102'})
        self.assertEqual(self.ids(section='water',min_length='5,5',max_motor_power=120), ['302'])
        self.assertEqual(set(self.ids(section='moto',vehicle_class='Дорожный',abs='Есть')), {'201','202'})
        self.assertEqual(self.ids(section='cars',seller_kind='company'), ['102'])
        self.assertEqual(self.ids(availability='order'), [])
        self.rejected('catalog',filters={'min_length':8,'max_length':5})
        self.rejected('catalog',filters={'sort':'distance'})
        self.rejected('catalog',filters={'min_price':'NaN'})

    def test_unknown_values_and_separate_meters(self):
        self.assertIsNone(engine.ad_by_id(self.state,'3')['mileage'])
        self.assertEqual(engine.ad_by_id(self.state,'3')['hours'],6400)
        self.assertNotIn('3',self.ids(max_mileage=100000))
        self.assertIn('3',self.ids(max_hours=7000))
        self.assertEqual(self.ids(section='cars',min_battery=20), [])
        self.assertEqual(set(self.ids(section='cars',min_battery=20,include_unknown=True)), {'101','102'})
        a=engine.ad_by_id(self.state,'101');a['mileage']=0
        self.assertIn('101', self.ids(max_mileage=0))
        engine.ad_by_id(self.state,'101')['mileage']=None
        self.assertNotIn('101', self.ids(max_mileage=0))

    def test_schema_and_each_category_can_be_published(self):
        electric={'fuel':'Электро'}
        carfields={x['key'] for x in FIELDS if applicable(x,'cars','car',electric)}
        self.assertIn('battery',carfields);self.assertNotIn('engine_cc',carfields)
        for cat in CATEGORIES:
            a={'category':cat,'brand':'Демо','model':'Тест','year':2022,'price':100000,'city':'Казань','description':'Рабочее состояние, осмотр по договорённости.','photos':['/assets/car.webp']}
            result=self.call('save_ad',ad=a,status='pending')
            created=engine.ad_by_id(self.state,result['id'])
            self.assertEqual(created['category'],cat)
            self.assertEqual(created['section'],engine.CATEGORY_SECTIONS[cat])

    def test_migration_keeps_custom_data_and_runs_once(self):
        legacy=copy.deepcopy(self.state)
        legacy['version']=1
        legacy['ads']=[a for a in legacy['ads'] if int(a['id'])<100]
        legacy['ads'][0]['price']=123456
        legacy['users']['azat']['name']='Сохранённое имя'
        legacy['favorites']['azat']=['1']
        for a in legacy['ads']:
            if a.get('hours') is not None:a['mileage']=a.pop('hours')
        before=copy.deepcopy(legacy['conversations'])
        self.state=legacy
        self.call('bootstrap')
        self.assertEqual(engine.ad_by_id(self.state,'1')['price'],123456)
        self.assertEqual(self.state['users']['azat']['name'],'Сохранённое имя')
        self.assertEqual(self.state['favorites']['azat'],['1'])
        self.assertEqual(self.state['conversations'],before)
        count=len(self.state['ads']);self.call('bootstrap')
        self.assertEqual(len(self.state['ads']),count)
        self.assertEqual(engine.ad_by_id(self.state,'3')['hours'],6400)

    def test_moderator_permissions_reason_checklist_and_stale_version(self):
        self.rejected('moderation_queue')
        self.rejected('moderate',id='4',decision='approve',revision=1)
        self.call('demo_user',user='moderator')
        self.assertEqual(set(self.call('moderation_queue')['ids']),{'4','103','203','303'})
        self.rejected('moderate',id='4',decision='return',reason='',revision=1)
        self.rejected('moderate',id='4',decision='approve',revision=1)
        self.rejected('moderate',id='4',decision='approve',revision=999,checks={'photos':True,'details':True,'description':True})
        self.call('moderate',id='4',decision='return',reason='Добавьте сведения о состоянии гидравлики',revision=1)
        self.assertEqual(self.state['moderation_log'][0]['moderator'],'moderator')
        self.assertEqual(self.state['notices'][0]['user'],'azat')
        self.assertNotIn('4',self.ids())
        self.rejected('moderate',id='4',decision='approve',revision=2,checks={'photos':True,'details':True,'description':True})
        self.call('demo_user',user='azat')
        a=copy.deepcopy(engine.ad_by_id(self.state,'4'));a['description']+=' Гидравлика исправна.'
        self.call('save_ad',ad=a,status='pending')
        self.call('demo_user',user='moderator')
        self.call('moderate',id='4',decision='approve',revision=3,checks={'photos':True,'details':True,'description':True})
        self.assertIn('4',self.ids())
        self.assertEqual(len(self.call('moderation_queue',status='history')['history']),2)

    def test_no_bypass_via_edit_archive_restore(self):
        self.call('demo_user',user='moderator')
        self.call('moderate',id='1',decision='remove',revision=1,reason='Исправьте сведения о комплектации')
        self.call('demo_user',user='azat')
        self.call('archive',id='1');self.call('restore',id='1')
        self.assertNotIn('1',self.ids())
        a=copy.deepcopy(engine.ad_by_id(self.state,'2'))
        self.call('save_ad',ad=a,status='keep')
        self.assertNotIn('2',self.ids())
        self.assertEqual(engine.ad_by_id(self.state,'2')['status'],'pending')


if __name__ == '__main__': unittest.main()
