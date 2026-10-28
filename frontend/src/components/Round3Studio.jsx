import React, { useEffect, useState } from 'react';
import { api } from '../api';

export default function Round3Studio({ user, token }) {
  const [mode,setMode]=useState('creative');
  const [file,setFile]=useState(null);
  const [creativeText,setCreativeText]=useState('');
  const [palette,setPalette]=useState('#14213D, #FFFFFF, #FCA311');
  const [logo,setLogo]=useState(null);
  const [dossiers,setDossiers]=useState([]);
  const [claim,setClaim]=useState({claim_text:'',source_title:'',source_url:'',source_excerpt:'',verification_note:''});
  const [result,setResult]=useState(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [success,setSuccess]=useState('');

  async function reload() {
    try {setDossiers(await api.fetchDossiers(token));} catch(e) {setError(e.message);}
  }
  useEffect(()=>{if(token)reload();},[token]);

  async function run(callback) {
    setBusy(true);setError('');setSuccess('');
    try {await callback();} catch(e){setError(e.message||'Request failed.');}
    finally {setBusy(false);}
  }
  function downloadableReport() {
    if(!result || mode!=='documents')return;
    const rows=[['Location','Rule ID','Version','Severity','Matched Text','Source','Reason','Suggestion'],
      ...(result.findings||[]).map(f=>[f.location,f.rule_id,f.rule_version,f.severity,f.matched_text,f.source_label,f.reason,f.suggestion])];
    const csv=rows.map(row=>row.map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(',')).join('\r\n');
    const blob=new Blob(['\ufeff',csv],{type:'text/csv;charset=utf-8'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');a.href=url;a.download='brandguard-location-linked-issues.csv';a.click();
    URL.revokeObjectURL(url);
  }
  const tabStyle={padding:'10px 14px',borderRadius:8,border:'1px solid #516080',background:'#1a2a4a',color:'white',cursor:'pointer'};
  const fieldStyle={width:'100%',padding:10,margin:'6px 0 12px',borderRadius:6};
  const wrap={maxWidth:1000,margin:'20px auto',padding:22,background:'#101b32',border:'1px solid #334663',borderRadius:16,color:'#eff4ff'};
  return <section style={wrap}>
    <h2>Round 3 · Brand Governance Studio</h2>
    <p>Image creative checks, document compliance and versioned evidence. Visual AI findings are advisory; final approval always belongs to a reviewer.</p>
    <div style={{display:'flex',gap:8,flexWrap:'wrap',marginBottom:22}}>
      {[['creative','Visual Creative'],['documents','PDF / DOCX'],['dossiers','Evidence Dossiers']].map(([id,name])=><button key={id} style={{...tabStyle,outline:mode===id?'2px solid #7c91ff':'none'}} onClick={()=>{setMode(id);setFile(null);setResult(null);setError('');}}>{name}</button>)}
    </div>
    {error&&<p role="alert" style={{color:'#ffadad'}}>{error}</p>}
    {success&&<p role="status" style={{color:'#a0f6c8'}}>{success}</p>}
    {mode==='creative'&&<>
      <h3>Visual creative and logo governance</h3>
      {user?.role==='admin'&&<div style={{padding:14,border:'1px solid #43537a',borderRadius:10,marginBottom:18}}>
        <h4>Approved brand assets (Admin)</h4>
        <label>Approved colours (comma-separated #RRGGBB)</label>
        <input style={fieldStyle} value={palette} onChange={e=>setPalette(e.target.value)}/>
        <label>Approved reference logo (JPG/PNG, 200 KB maximum)</label>
        <input type="file" accept=".png,.jpg,.jpeg" onChange={e=>setLogo(e.target.files?.[0]||null)}/>
        <p><button disabled={busy} onClick={()=>run(async()=>{const colours=palette.split(',').map(v=>v.trim()).filter(Boolean);await api.updateBrandAssets(token,colours,logo);setSuccess('Approved brand assets saved for your workspace.');})}>Save approved assets</button></p>
      </div>}
      <label>Marketing creative JPG/PNG (maximum 4 MB)</label>
      <input type="file" accept=".png,.jpg,.jpeg" onChange={e=>setFile(e.target.files?.[0]||null)}/>
      <p style={{marginTop:12}}>Optional exact text from creative for deterministic restricted-phrase checks:</p>
      <textarea style={fieldStyle} rows={3} value={creativeText} onChange={e=>setCreativeText(e.target.value)}/>
      <button disabled={!file||busy} onClick={()=>run(async()=>setResult(await api.reviewCreative(token,file,creativeText)))}>{busy?'Reviewing...':'Review creative'}</button>
    </>}
    {mode==='documents'&&<>
      <h3>Multipage marketing document compliance</h3>
      <p>PDF and DOCX up to 5 MB and 25 pages (DOCX up to 250 text sections). Scanned PDF pages without selectable text are marked unreviewed. This is deterministic rule checking, not a claim of full semantic document review.</p>
      <input type="file" accept=".pdf,.docx" onChange={e=>setFile(e.target.files?.[0]||null)}/>
      <p><button disabled={!file||busy} onClick={()=>run(async()=>setResult(await api.reviewDocument(token,file)))}>{busy?'Reviewing...':'Check document'}</button></p>
      {result&&<button onClick={downloadableReport}>Download location-linked CSV issues report</button>}
    </>}
    {mode==='dossiers'&&<>
      <h3>Versioned, evidence-backed approved claims</h3>
      <p>Admins verify dossiers; reviewers use the evidence ID when approving a high-risk draft. An exception instead requires a documented reason of at least 25 characters.</p>
      {user?.role==='admin'&&<div style={{padding:14,border:'1px solid #43537a',borderRadius:10}}>
        {Object.entries({claim_text:'Exact approved claim wording',source_title:'Evidence source title',source_url:'Source URL (optional)',source_excerpt:'Supporting source excerpt',verification_note:'Admin verification rationale'}).map(([key,label])=><label key={key} style={{display:'block'}}>{label}{key==='source_excerpt'||key==='verification_note'?<textarea rows={3} style={fieldStyle} value={claim[key]} onChange={e=>setClaim({...claim,[key]:e.target.value})}/>:<input style={fieldStyle} value={claim[key]} onChange={e=>setClaim({...claim,[key]:e.target.value})}/>}</label>)}
        <button disabled={busy} onClick={()=>run(async()=>{const saved=await api.createDossier(token,claim);await reload();setSuccess('Created verified dossier '+saved.id);})}>Create verified dossier</button>
      </div>}
      <h4>Workspace claim dossiers</h4>
      {!dossiers.length&&<p>No dossiers yet. An admin needs to create verified evidence first.</p>}
      {dossiers.map(d=><article key={d.id} style={{padding:12,borderBottom:'1px solid #334663'}}>
        <strong>{d.claim_text}</strong><div>ID: <code>{d.id}</code> · v{d.version}</div>
        <div>Source: {d.source_title}</div><small>{d.source_excerpt}</small>
        {d.source_url&&<div><a href={d.source_url} target="_blank" rel="noopener noreferrer">Source link</a></div>}
        <button onClick={()=>navigator.clipboard?.writeText(d.id)}>Copy evidence ID</button>
      </article>)}
    </>}
    {result&&<div style={{marginTop:22,padding:14,border:'1px solid #5d7191',borderRadius:10}}>
      <h3>Review results</h3>
      <p>Issues: {result.issue_count??result.findings?.length??0}; status: {result.status||result.ai_status}</p>
      {result.logo_status&&<p>Reference logo: {result.logo_status}</p>}
      {result.scanned_or_empty_sections?.length>0&&<p style={{color:'#ffd99a'}}>Unreviewed scanned/empty sections: {result.scanned_or_empty_sections.join(', ')}</p>}
      <p>{result.limitations||result.ai_note}</p>
      {(result.findings||[]).length===0?<p>No issues identified by the checks that ran. This is not a guarantee of compliance.</p>:result.findings.map((f,i)=><div key={i} style={{padding:12,marginBottom:10,border:'1px solid #334663',borderRadius:8}}>
        <strong>{f.location||f.type} · {f.rule_id||f.colour||'Visual finding'} · {f.severity}</strong>
        <p>{f.reason||f.message}</p><p>{f.matched_text||f.observed_text}</p>
        {f.box&&<small>Image coordinates (0–1): {f.box.map(x=>Number(x).toFixed(2)).join(', ')}</small>}
      </div>)}
    </div>}
  </section>;
}
