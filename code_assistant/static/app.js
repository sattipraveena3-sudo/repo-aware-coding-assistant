const $ = id => document.getElementById(id);
let repos = [];
async function api(path, opts={}){const r=await fetch(path,{headers:{'Content-Type':'application/json'},...opts});const data=await r.json();if(!r.ok)throw new Error(data.detail||'Request failed');return data}
async function loadRepos(){const data=await api('/api/repositories');repos=data.repositories;$('repoSelect').innerHTML=repos.length?repos.map(r=>`<option value="${r.id}">${r.name} · ${r.symbols} symbols</option>`).join(''):'<option value="">No repositories indexed</option>';showMeta()}
function showMeta(){const r=repos.find(x=>x.id===$('repoSelect').value);$('repoMeta').textContent=r?JSON.stringify(r,null,2):'No repository selected.'}
async function run(label, fn){$('status').textContent=label;try{await fn();$('status').textContent='Done.'}catch(e){$('status').textContent=e.message}}
$('repoSelect').onchange=showMeta;
$('indexLocal').onclick=()=>run('Indexing local repository…',async()=>{await api('/api/repositories/local',{method:'POST',body:JSON.stringify({path:$('localPath').value})});await loadRepos()});
$('cloneRepo').onclick=()=>run('Cloning and indexing…',async()=>{await api('/api/repositories/clone',{method:'POST',body:JSON.stringify({url:$('gitUrl').value})});await loadRepos()});
$('refreshRepo').onclick=()=>run('Refreshing index…',async()=>{const id=$('repoSelect').value;if(!id)throw new Error('Choose a repository first.');await api(`/api/repositories/${id}/refresh`,{method:'POST'});await loadRepos()});
$('ask').onclick=()=>run('Searching repository context…',async()=>{const id=$('repoSelect').value;if(!id)throw new Error('Choose a repository first.');const data=await api(`/api/repositories/${id}/ask`,{method:'POST',body:JSON.stringify({question:$('question').value,model:$('model').value||null})});$('answer').textContent=`[${data.mode}]\n\n${data.answer}${data.warning?'\n\n'+data.warning:''}`;$('refs').innerHTML=(data.references||[]).map(r=>`<div>${r}</div>`).join('')});
api('/api/health').then(x=>$('health').textContent='API online · '+x.version).catch(()=>$('health').textContent='API offline');loadRepos();
