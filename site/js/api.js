const cache = {};
export async function j(path){
  if(cache[path]) return cache[path];
  const r = await fetch((location.pathname.includes('Nivesify-PMS') ? '/Nivesify-PMS/' : './') + 'data/' + path);
  if(!r.ok) throw new Error(path + ' → ' + r.status);
  const d = await r.json(); cache[path] = d; return d;
}
export const slug = s => s.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'');
export const inr = n => n==null ? '—' : '₹' + Number(n).toLocaleString('en-IN',{maximumFractionDigits:1});
export const num = n => n==null ? '—' : Number(n).toLocaleString('en-IN',{maximumFractionDigits:2});
export const pct = n => n==null ? '—' : (n>0?'+':'') + Number(n).toFixed(2) + '%';
