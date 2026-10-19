import http.cookiejar
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
import app


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        app.DB_PATH=Path(cls.temp.name)/'test.sqlite3'
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup()

    def client(self):
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def action(self,client,action,payload=None,origin=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.base+'/api/action',data=json.dumps({'action':action,'payload':payload or {}}).encode(),headers=headers)
        return json.load(client.open(req))

    def test_two_browser_sessions_persist_independently(self):
        first=self.client();second=self.client()
        self.action(first,'archive',{'id':'1'})
        ids=self.action(first,'catalog')['result']['ids']
        self.assertNotIn('1',ids)
        self.assertIn('1',self.action(second,'catalog')['result']['ids'])
        self.assertNotIn('1',self.action(first,'catalog')['result']['ids'])

    def test_html_and_local_mode(self):
        content=urllib.request.urlopen(self.base+'/').read().decode()
        self.assertIn('ТЯГА',content)
        self.assertIn('true',urllib.request.urlopen(self.base+'/server-mode.js').read().decode())
        with urllib.request.urlopen(self.base+'/assets/volvo.webp') as response:
            self.assertEqual(response.headers.get_content_type(),'image/webp')
            self.assertGreater(len(response.read()),1000)

    def test_cross_origin_mutation_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.action(self.client(),'reset',origin='https://elsewhere.example')
        self.assertEqual(error.exception.code,403)

    def test_bad_action_returns_recoverable_json(self):
        client=self.client()
        with self.assertRaises(urllib.error.HTTPError) as error:self.action(client,'save_ad',{'ad':{'year':'bad'}})
        self.assertEqual(error.exception.code,400)
        self.assertFalse(json.loads(error.exception.read())['ok'])
        self.assertTrue(self.action(client,'bootstrap')['ok'])


if __name__=='__main__':unittest.main()
