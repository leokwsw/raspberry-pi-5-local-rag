import React,{useEffect,useState} from "react";import{createRoot}from"react-dom/client";import"./style.css";
function App(){const[docs,setDocs]=useState([]),[q,setQ]=useState(""),[answer,setAnswer]=useState("");
const refresh=()=>fetch("/documents").then(r=>r.json()).then(setDocs);useEffect(refresh,[]);
async function ask(){const r=await fetch("/chat",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({question:q})});setAnswer(await r.text())}
return <main><h1>Pi Local RAG</h1><nav>Documents · Chat · System Status · Benchmark Results</nav>
<section><h2>Documents</h2><input type="file" onChange={async e=>{const f=new FormData();f.append("file",e.target.files[0]);await fetch("/documents",{method:"POST",body:f});refresh()}}/><ul>{docs.map(d=><li key={d.id}>{d.name}</li>)}</ul></section>
<section><h2>Chat</h2><textarea value={q} onChange={e=>setQ(e.target.value)}/><button onClick={ask}>Ask</button><pre>{answer}</pre></section></main>}createRoot(document.getElementById("root")).render(<App/>);
