import React, { useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const PROFILE = import.meta.env.VITE_DEMO_PROFILE_ID;

export default function Workout({ onDone }) {
  const [effort, setEffort] = useState("刚好"); const [notes, setNotes] = useState(""); const [status, setStatus] = useState("idle");
  async function submit() { setStatus("saving"); try { const r = await fetch(`${API}/workout-logs`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({profile_id:PROFILE,workout_name:"下肢力量",duration_min:45,perceived_effort:effort,notes})}); if(!r.ok) throw Error(); setStatus("saved"); } catch { setStatus("error"); } }
  return <section className="panel"><p className="eyebrow">FITLOOP / 训练</p><h1>完成今天的训练</h1><h2>下肢力量 · 45 分钟</h2><p className="hint">深蹲 / 罗马尼亚硬拉 / 弓步蹲</p><label>今天感觉如何？</label><div className="chips">{["轻松","刚好","很累"].map(x=><button className={effort===x?"selected":""} onClick={()=>setEffort(x)}>{x}</button>)}</div><textarea value={notes} onChange={e=>setNotes(e.target.value)} placeholder="例如：深蹲最后一组比较吃力"/><button className="primary" onClick={submit}>{status==="saving"?"正在保存…":status==="saved"?"训练已保存":"完成并生成今日总结"}</button>{status==="saved"&&<button onClick={onDone}>返回今日</button>}{status==="error"&&<p className="message error">保存失败，请稍后重试。</p>}</section>;
}
