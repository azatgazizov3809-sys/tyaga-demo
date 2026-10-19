import copy
import json
import unittest
import engine


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.state = engine.seed()

    def do(self, action, **payload):
        result = json.loads(engine.request(json.dumps(self.state), action, json.dumps(payload)))
        self.assertTrue(result['ok'], result.get('error'))
        self.state = result['state']
        return result

    def invalid(self, action, **payload):
        before = copy.deepcopy(self.state)
        result = json.loads(engine.request(json.dumps(self.state), action, json.dumps(payload)))
        self.assertFalse(result['ok'])
        self.assertNotIn('state', result)
        self.assertEqual(before, self.state)
        return result['error']

    def test_initial_counts_and_private_status_visibility(self):
        result = self.do('bootstrap')
        self.assertEqual(result['summary']['counts'], {'all':6,'active':3,'pending':1,'draft':1,'archived':1})
        ids = self.do('catalog')['result']['ids']
        self.assertEqual(len(ids), 18)
        self.assertTrue(set(ids).isdisjoint({'4','5','6','15'}))

    def test_filters_numeric_geo_keyword_and_order(self):
        ids = self.do('catalog', filters={'category':'tractor','max_price':'9 000 000','sort':'price_asc'})['result']['ids']
        values = [engine.ad_by_id(self.state,i)['price'] for i in ids]
        self.assertEqual(values, sorted(values))
        self.assertNotIn('14', ids)
        self.assertEqual(self.do('catalog', filters={'q':'kamaz','city':'Казань'})['result']['ids'], ['8'])
        nearby = self.do('catalog', filters={'city':'Казань','radius':250})['result']['ids']
        self.assertIn('2',nearby)
        self.assertNotIn('7',nearby)
        self.assertEqual(self.do('catalog', filters={'min_price':999999999})['result']['ids'], [])
        self.invalid('catalog',filters={'min_price':100,'max_price':20})

    def test_favorites_compare_and_limits(self):
        self.do('favorite', id='1')
        self.assertIn('1',self.state['favorites']['azat'])
        self.do('favorite', id='1')
        self.assertNotIn('1',self.state['favorites']['azat'])
        self.do('compare_toggle',id='1'); self.do('compare_toggle',id='2')
        self.invalid('compare_toggle',id='3')
        self.assertEqual(len(self.state['compare']),4)
        self.do('compare_clear')
        self.assertEqual(self.state['compare'],[])

    def test_full_publication_moderation_and_archive(self):
        draft=self.do('save_ad',ad={'category':'tractor','brand':'Volvo'},status='draft')['result']['id']
        self.invalid('save_ad',ad={'id':draft,'category':'tractor','brand':'Volvo'},status='pending')
        values={'id':draft,'category':'tractor','brand':'Volvo','model':'FH 540','year':2022,'price':9900000,'mileage':200000,'city':'Казань','description':'Полное обслуживание, готов к осмотру.','photos':['/assets/volvo.webp']}
        count=len(self.state['ads'])
        self.do('validate_ad',ad=values)
        self.assertEqual(len(self.state['ads']),count)
        self.assertEqual(engine.ad_by_id(self.state,draft)['status'],'draft')
        self.do('save_ad',ad=values,status='pending')
        self.assertNotIn(draft,self.do('catalog')['result']['ids'])
        self.do('demo_user',user='moderator')
        self.do('moderate',id=draft,decision='return',reason='Уточните историю обслуживания техники',revision=engine.ad_by_id(self.state,draft)['revision'])
        self.assertEqual(engine.ad_by_id(self.state,draft)['status'],'rejected')
        self.do('demo_user',user='azat')
        self.do('save_ad',ad=values,status='pending')
        self.do('demo_user',user='moderator')
        self.do('moderate',id=draft,decision='approve',checks={'photos':True,'details':True,'description':True},revision=engine.ad_by_id(self.state,draft)['revision'])
        self.assertIn(draft,self.do('catalog')['result']['ids'])
        self.do('demo_user',user='azat')
        self.do('sold',id=draft)
        self.assertNotIn(draft,self.do('catalog')['result']['ids'])
        self.do('restore',id=draft)
        self.assertNotIn(draft,self.do('catalog')['result']['ids'])
        self.assertEqual(engine.ad_by_id(self.state,draft)['status'],'pending')
        self.do('archive',id=draft)
        self.assertEqual(engine.ad_by_id(self.state,draft)['status'],'archived')
        self.do('delete_ad',id=draft)
        self.assertNotIn(draft,self.do('my_ads')['result']['ids'])

    def test_ownership_and_guest_restrictions(self):
        self.invalid('archive',id='7')
        self.invalid('save_ad',ad={'id':'7'},status='draft')
        self.do('demo_user',user='ilya')
        self.invalid('moderate',id='4',approve=True)
        self.invalid('read_chat',id='c2')
        self.do('logout')
        self.invalid('favorite',id='7')
        self.invalid('my_ads')
        self.assertTrue(self.do('catalog')['result']['ids'])

    def test_chat_unread_two_roles_and_attachment(self):
        self.do('read_chat',id='c1')
        self.assertEqual(self.do('bootstrap')['summary']['unread'],1)
        self.do('send_message',id='c1',text='Да, приезжайте к 15:00',attachment='data:image/png;base64,AA==')
        self.do('demo_user',user='ilya')
        self.assertEqual(self.do('bootstrap')['summary']['unread'],1)
        self.do('read_chat',id='c1')
        self.do('send_message',id='c1',text='Буду!')
        self.do('demo_user',user='azat')
        self.assertEqual(self.do('bootstrap')['summary']['unread'],2)
        cid=self.do('start_chat',id='7')['result']['id']
        self.assertEqual(self.do('start_chat',id='7')['result']['id'],cid)
        self.do('simulate_reply',id=cid)
        self.invalid('send_message',id=cid,text='')
        self.invalid('start_chat',id='1')
        self.invalid('start_chat',id='15')

    def test_search_settings_profile_support(self):
        sid=self.do('save_search',name='До 9 миллионов',filters={'max_price':9000000},notify=True,frequency='daily')['result']['id']
        self.assertGreater(self.do('bootstrap')['summary']['search_new'][sid],0)
        self.do('search_seen',id=sid)
        self.assertEqual(self.do('bootstrap')['summary']['search_new'][sid],0)
        self.do('search_preferences',id=sid,frequency='weekly',notify=False)
        saved=next(s for s in self.state['searches']['azat'] if s['id']==sid)
        self.assertEqual(saved['frequency'],'weekly');self.assertFalse(saved['notify'])
        self.invalid('profile',name='X')
        self.invalid('profile',email='invalid')
        self.do('profile',name='Азат Тест',email='test@example.com',notifications={'messages':False})
        self.assertFalse(self.state['users']['azat']['notifications']['messages'])
        self.do('end_sessions');self.assertEqual(len(self.state['sessions']['azat']),1)
        ticket=self.do('support',text='Проверяю форму обращения',topic='Сообщить об ошибке',ad_id='1')['result']['number']
        self.assertEqual(ticket,1001)
        self.invalid('support',text='Проверяю чужое объявление',ad_id='7')
        self.do('delete_search',id=sid)
        self.assertFalse(any(s['id']==sid for s in self.state['searches']['azat']))

    def test_login_validation_and_reset(self):
        self.do('logout')
        self.invalid('request_code',phone='123')
        self.do('request_code',phone='+7 999 123-45-67')
        self.invalid('verify_code',code='000000')
        self.do('verify_code',code='123456')
        self.assertEqual(self.state['user_id'],'azat')
        self.do('archive',id='1');self.do('reset')
        self.assertEqual(engine.ad_by_id(self.state,'1')['status'],'active')

    def test_bad_photo_and_numeric_fields(self):
        self.invalid('save_ad',ad={'price':'abc'},status='draft')
        self.invalid('save_ad',ad={'year':1750},status='draft')
        self.invalid('save_ad',ad={'photos':['javascript:alert(1)']},status='draft')
        self.invalid('save_ad',ad={'photos':['data:image/svg+xml;base64,AA==']},status='draft')
        self.invalid('save_ad',ad={'photos':['/assets/volvo.webp']*9},status='draft')


if __name__=='__main__':unittest.main()
