import { loadPyodide } from './runtime/pyodide.mjs';

let state = '';
let db;
let chain = Promise.resolve();
async function storage() {
  db = await new Promise((resolve, reject) => {
    const req = indexedDB.open('tyaga-python-demo', 1);
    req.onupgradeneeded = () => req.result.createObjectStore('data');
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  state = await new Promise((resolve, reject) => {
    const req = db.transaction('data').objectStore('data').get('state');
    req.onsuccess = () => resolve(req.result || ''); req.onerror = () => reject(req.error);
  });
}
async function save(value) {
  if (!db) throw new Error('Хранилище браузера недоступно. Изменения не сохранены.');
  await new Promise((resolve, reject) => {
    const tx = db.transaction('data', 'readwrite');
    tx.objectStore('data').put(value, 'state');
    tx.oncomplete = resolve; tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error);
  });
}
const ready = (async () => {
  postMessage({progress:'Загружаем Python. При первом открытии это займёт немного времени…'});
  await storage();
  const py = await loadPyodide({indexURL: new URL('./runtime/', import.meta.url).href});
  for (const name of ['catalog_schema.py','engine.py']) {
    const response = await fetch('./'+name);
    if (!response.ok) throw new Error('Не удалось загрузить Python-логику');
    py.FS.writeFile('/'+name, await response.text());
  }
  py.runPython("import sys; sys.path.insert(0, '/'); import engine");
  postMessage({progress:'Открываем каталог…'});
  return py;
})();
self.onmessage = event => {
  const {id, action, payload} = event.data;
  chain = chain.then(async () => {
    try {
      const py = await ready;
      py.globals.set('_state', state); py.globals.set('_action', action); py.globals.set('_payload', JSON.stringify(payload || {}));
      const response = JSON.parse(py.runPython('engine.request(_state, _action, _payload)'));
      if (response.ok) {
        const next = JSON.stringify(response.state);
        if (next !== state) await save(next);
        state = next;
      }
      postMessage({id, response});
    } catch (e) { postMessage({id, response:{ok:false,error:{message:e.message || 'Не удалось запустить демо'}}}); }
  });
};
