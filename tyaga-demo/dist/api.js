let serial = 0;
let queue = Promise.resolve();
const requests = new Map();
let worker;
if (!window.TYAGA_SERVER) {
  worker = new Worker(new URL('./python-worker.js', import.meta.url), {type:'module'});
  worker.onmessage = ({data}) => {
    if (data.progress) { const p = document.querySelector('#boot-status'); if (p) p.textContent = data.progress; return; }
    const request = requests.get(data.id);
    if (request) { requests.delete(data.id); request.resolve(data.response); }
  };
  worker.onerror = () => {
    for (const r of requests.values()) r.reject(new Error('Не удалось запустить Python. Обновите страницу и проверьте соединение.'));
    requests.clear();
  };
}
export function request(action, payload = {}) {
  const run = () => window.TYAGA_SERVER
    ? fetch('/api/action', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,payload})}).then(async r => { const data = await r.json(); return data; })
    : new Promise((resolve,reject) => {const id=++serial; requests.set(id,{resolve,reject}); worker.postMessage({id,action,payload});});
  const current = queue.then(run);
  queue = current.catch(() => {});
  return current;
}
