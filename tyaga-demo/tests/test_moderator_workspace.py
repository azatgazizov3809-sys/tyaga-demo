import copy
import datetime as dt
import json
import unittest
import engine


class ModeratorWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.state = engine.seed()
        self.state['user_id'] = 'moderator'

    def call(self, action, **data):
        r = json.loads(engine.request(json.dumps(self.state), action, json.dumps(data)))
        self.assertTrue(r['ok'], r.get('error'))
        self.state = r['state']
        return r['result']

    def invalid(self, action, **data):
        r = json.loads(engine.request(json.dumps(self.state), action, json.dumps(data)))
        self.assertFalse(r['ok']); self.assertNotIn('state', r)

    def test_priority_filters_and_seller_search(self):
        self.call('moderation_priority',id='303',revision=1,priority='high')
        q=self.call('moderation_queue')
        self.assertEqual(q['ids'][0],'303');self.assertEqual(q['stats']['priority'],1)
        self.assertEqual(self.call('moderation_queue',focus='high')['ids'],['303'])
        self.assertEqual(self.call('moderation_queue',q='ВолгаТрак')['ids'],['303'])
        self.assertEqual(self.call('moderation_queue',seller_kind='company')['ids'],['303'])
        self.assertEqual(self.call('moderation_queue',q='№103')['ids'],['103'])
        self.call('moderation_priority',id='303',revision=1,priority='normal')
        self.assertEqual(self.call('moderation_queue',focus='high')['ids'],[])

    def test_defer_expiry_resume_and_no_publication(self):
        self.call('moderation_defer',id='4',revision=1,minutes=15,reason='Уточнить состояние')
        self.assertNotIn('4',self.call('moderation_queue')['ids'])
        self.assertEqual(self.call('moderation_queue',status='deferred')['ids'],['4'])
        self.assertNotIn('4',self.call('catalog')['ids'])
        self.state['moderation_work']['4']['deferred_until']=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=1)).isoformat()
        self.assertIn('4',self.call('moderation_queue')['ids'])
        self.assertFalse(self.call('moderation_queue',status='deferred')['ids'])
        self.call('moderation_defer',id='4',revision=1,minutes=1440)
        self.call('moderation_resume',id='4',revision=1)
        self.assertIn('4',self.call('moderation_queue')['ids'])
        self.invalid('moderation_defer',id='1',revision=1,minutes=60)
        self.invalid('moderation_defer',id='4',revision=1,minutes=999)

    def test_internal_notes_history_filters_no_seller_notice(self):
        notices=copy.deepcopy(self.state['notices'])
        self.call('moderation_note',id='4',revision=1,text='Проверить фото гидравлики ещё раз')
        self.assertEqual(self.state['notices'],notices)
        self.assertEqual(self.call('moderation_queue')['info']['4']['notes'][0]['author'],'Анна')
        h=self.call('moderation_queue',status='history',decision='note',q='гидравлики')
        self.assertEqual(len(h['history']),1)
        self.assertEqual(h['stats']['today'],0)
        self.assertEqual(self.call('moderation_queue',status='history',date_to='2000-01-01')['history'],[])
        self.invalid('moderation_queue',status='history',date_from='2026-10-31',date_to='2026-10-01')
        self.invalid('moderation_note',id='4',revision=1,text='x')

    def test_changes_after_return_and_resubmission(self):
        self.call('moderate',id='4',revision=1,decision='return',reason='Уточните описание и стоимость')
        self.call('demo_user',user='azat')
        a=copy.deepcopy(engine.ad_by_id(self.state,'4'))
        a['price']=8000000;a['description']+=' Гидравлика исправна.'
        self.call('save_ad',ad=a,status='pending')
        self.call('demo_user',user='moderator')
        q=self.call('moderation_queue',focus='repeat')
        self.assertEqual(q['ids'],['4'])
        changes={c['key']:c for c in q['info']['4']['changes']}
        self.assertEqual(changes['price']['before'],8600000)
        self.assertEqual(changes['price']['after'],8000000)
        self.assertIn('description',changes)
        self.assertNotIn('photos',changes)
        self.call('moderate',id='4',revision=3,decision='approve',checks=dict(photos=True,details=True,description=True))
        self.assertFalse(self.call('moderation_queue')['info']['4']['repeat'])

    def test_flags_missing_mandatory_fields_cannot_be_approved(self):
        engine.ad_by_id(self.state,'4')['photos']=[]
        self.assertIn('4',self.call('moderation_queue',focus='flags')['ids'])
        self.invalid('moderate',id='4',revision=1,decision='approve',checks=dict(photos=True,details=True,description=True))
        self.call('moderate',id='4',revision=1,decision='return',reason='Добавьте фотографии продаваемой техники')
        self.assertEqual(engine.ad_by_id(self.state,'4')['status'],'rejected')

    def test_role_and_revision_on_all_workflow_actions(self):
        actions=[('moderation_note',{'text':'Служебная заметка'}),('moderation_priority',{'priority':'high'}),('moderation_defer',{'minutes':60}),('moderation_resume',{})]
        for action,args in actions:self.invalid(action,id='4',revision=999,**args)
        self.call('demo_user',user='azat')
        for action,args in actions:self.invalid(action,id='4',revision=1,**args)

    def test_migration_from_v2_preserves_decisions_and_ads(self):
        self.state['version']=2;self.state.pop('moderation_work')
        self.state['ads'][0]['price']=123456
        self.state['moderation_log']=[{'id':'old','ad_id':'4','title':'JCB','section':'commercial','moderator':'moderator','moderator_name':'Анна','decision':'return','reason':'Уточните сведения','before':'pending','after':'rejected','time':engine.now(),'revision':2}]
        self.call('bootstrap')
        self.assertEqual(self.state['version'],3)
        self.assertEqual(self.state['ads'][0]['price'],123456)
        info=self.call('moderation_queue')['info']['4']
        self.assertTrue(info['repeat']);self.assertEqual(info['changes'],[])
        self.assertEqual(len(self.state['moderation_log']),1)


if __name__=='__main__':unittest.main()
