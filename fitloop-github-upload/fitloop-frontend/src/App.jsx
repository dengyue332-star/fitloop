import React, { useEffect, useState } from "react";
import Workout from "./Workout";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const PROFILE_ID = import.meta.env.VITE_DEMO_PROFILE_ID;
const quickMeals = ["鸡胸肉 150g、米饭一碗、西兰花一份", "无糖酸奶一杯、香蕉一根", "鸡胸肉饭"];
const labels = ["鸡胸肉饭", "无糖酸奶", "香蕉"];

function Metric({ value, label }) { return <div className="metric"><strong>{value}</strong><span>{label}</span></div>; }
function Navigation({ page, setPage }) {
  return <nav aria-label="主导航">
    <button className={page === "today" ? "active" : ""} onClick={() => setPage("today")}>●<small>今日</small></button>
    <button className={page === "log" ? "active" : ""} onClick={() => setPage("log")}>●<small>记录</small></button>
    <button className={page === "plan" ? "active" : ""} onClick={() => setPage("plan")}>●<small>计划</small></button><button type="button">○<small>我的</small></button>
  </nav>;
}

function Today({ setPage }) {
  const [daily, setDaily] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!PROFILE_ID) { setError("演示用户尚未配置。"); return; }
    fetch(`${API_BASE_URL}/daily-advice`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile_id: PROFILE_ID }) })
      .then(async (response) => { const data = await response.json(); if (!response.ok) throw new Error(data.detail); return data; })
      .then(setDaily).catch((reason) => setError(reason.message || "暂时无法获取今日数据。"));
  }, []);
  const totals = daily?.totals;
  const workout = daily?.workouts?.[0];
  const name = daily?.profile?.nickname || "你";
  return <>
    <header><p className="eyebrow">FITLOOP / 今日</p><h1>早上好，{name}</h1><p className="subhead">今天，先完成一个小目标。</p></header>
    <section className="panel today-food"><div className="section-title"><h2>今日饮食</h2><p>{daily ? `已记录 ${daily.food_log_count} 餐` : "正在读取"}</p></div>
      <div className="metrics">{totals ? <><Metric value={`${totals.calories} kcal`} label="已摄入" /><Metric value={`${totals.protein_g}g`} label="蛋白质" /><Metric value={`${daily.food_log_count} 餐`} label="已记录" /></> : <div className="metrics skeletons"><i /><i /><i /></div>}</div>
      <p className="hint">{daily ? `蛋白质已记录 ${totals.protein_g}g；继续稳定记录，建议会更准确。` : "正在汇总今天的真实记录。"}</p>
    </section>
    <section className="training-card"><p className="training-label">今天的训练</p><h2>{workout ? `${workout.workout_name} · ${workout.duration_min || 0} 分钟` : "今天还没有训练记录"}</h2><p>{workout?.notes || "完成饮食记录后，也别忘记安排一次活动。"}</p><button className="primary" onClick={() => setPage("workout")}>开始训练</button></section>
    <section className="panel advice-card"><p className="estimate-title">FitLoop 建议</p><p className="advice">{daily?.advice || error || "正在生成基于你真实记录的建议…"}</p><p className="why">查看为什么这样建议 →</p></section>
  </>;
}

function FoodLog({ setPage }) {
  const [foodText, setFoodText] = useState(quickMeals[0]); const [estimate, setEstimate] = useState(null); const [status, setStatus] = useState("idle"); const [message, setMessage] = useState("");
  async function estimateMeal() { if (foodText.trim().length < 2) { setMessage("请先写下这餐吃了什么。"); return; } setStatus("estimating"); setMessage(""); try { const response = await fetch(`${API_BASE_URL}/food/estimate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ food_text: foodText.trim() }) }); const data = await response.json(); if (!response.ok) throw new Error(data.detail); setEstimate(data); setStatus("estimated"); } catch (error) { setStatus("idle"); setMessage(error.message || "网络连接失败，请检查后端是否已启动。"); } }
  async function saveMeal() { if (!PROFILE_ID) { setMessage("演示用户还未配置。"); return; } setStatus("saving"); setMessage(""); try { const response = await fetch(`${API_BASE_URL}/food-logs`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile_id: PROFILE_ID, meal_type: "午餐", food_text: foodText.trim(), ...estimate }) }); const data = await response.json(); if (!response.ok) throw new Error(data.detail); setStatus("saved"); setMessage("已保存到今天的饮食记录。"); } catch (error) { setStatus("estimated"); setMessage(error.message || "网络连接失败，请检查后端是否已启动。"); } }
  const text = status === "estimating" ? "正在估算…" : status === "saving" ? "正在保存…" : status === "saved" ? "已保存" : estimate ? "确认并保存" : "查询营养";
  return <><header><p className="eyebrow">FITLOOP / 记录</p><h1>记录这一餐</h1><p className="subhead">用一句话告诉我你吃了什么。</p></header>
    <section className="panel meal-panel"><label htmlFor="meal">午餐</label><textarea id="meal" value={foodText} onChange={(event) => { setFoodText(event.target.value); setEstimate(null); setStatus("idle"); }} placeholder="例如：鸡胸肉 150g、米饭一碗、西兰花一份" /><p className="hint">支持食物名称和大致份量，稍后你可以确认。</p></section>
    {estimate ? <section className="estimate-card" aria-live="polite"><p className="estimate-title">AI 估算营养</p><div className="metrics"><Metric value={`${estimate.calories} kcal`} label="热量" /><Metric value={`${estimate.protein_g}g`} label="蛋白质" /><Metric value={`${estimate.carbs_g}g`} label="碳水" /></div><p className="hint">{estimate.assumptions?.[0] || "请确认份量后保存，估算不替代专业营养建议。"}</p></section> : <section className="estimate-card loading-card"><p className="estimate-title">AI 估算营养</p><div className="metrics skeletons"><i /><i /><i /></div><p className="hint">点击查询营养后，AI 会先给出估算。</p></section>}
    <section className="panel recent-panel"><h2>最近常吃</h2><div className="chips">{quickMeals.map((meal, index) => <button key={meal} type="button" onClick={() => { setFoodText(meal); setEstimate(null); setStatus("idle"); }}>{labels[index]}</button>)}</div></section>
    <button className="primary" type="button" disabled={status === "estimating" || status === "saving" || status === "saved"} onClick={estimate ? saveMeal : estimateMeal}>{text}</button>{message && <p className={`message ${status === "saved" ? "success" : "error"}`}>{message}</p>}
  </>;
}

function WeeklyReview() {
  const [draft, setDraft] = useState(null); const [state, setState] = useState("loading");
  useEffect(() => { const monday = new Date(); monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7)); const week_start = monday.toISOString().slice(0, 10); fetch(`${API_BASE_URL}/weekly-reviews/draft`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({profile_id:PROFILE_ID,week_start})}).then(r=>r.json()).then(x=>{setDraft(x);setState("ready");}).catch(()=>setState("error")); }, []);
  async function confirm() { setState("saving"); const r=await fetch(`${API_BASE_URL}/weekly-reviews/confirm`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({profile_id:PROFILE_ID,week_start:draft.week_start,training_completion_rate:Math.min(100,draft.training_count*33.3),protein_target_days:draft.protein_target_days,summary:draft.summary,next_week_focus:draft.next_week_focus})}); setState(r.ok ? "saved" : "error"); }
  if (!draft) return <><header><p className="eyebrow">FITLOOP / 周报</p><h1>这一周，做得很好</h1></header><section className="estimate-card"><p>{state === "error" ? "暂时无法生成周报。" : "正在汇总本周记录…"}</p></section></>;
  return <><header><p className="eyebrow">FITLOOP / 周报</p><h1>这一周，做得很好</h1><p className="subhead">{draft.week_start} 起的一周</p></header><section className="estimate-card score"><p className="estimate-title">本周执行评分</p><strong>{draft.execution_score} / 100</strong><p className="hint">{draft.summary}</p></section><section className="panel overview"><h2>本周概览</h2><p>训练完成 <b>{draft.training_count} 次</b></p><p>蛋白质达标 <b>{draft.protein_target_days} / 7 天</b></p><p>饮食记录 <b>{draft.food_log_days} / 7 天</b></p></section><section className="training-card"><p className="training-label">下周只做一件重点事</p><h2>{draft.next_week_focus}</h2><p>从这一件小事开始，保持稳定执行。</p></section><button className="primary" disabled={state === "saving" || state === "saved"} onClick={confirm}>{state === "saving" ? "正在保存…" : state === "saved" ? "下周计划已确认" : "确认下周计划"}</button></>;
}

export default function App() { const [page, setPage] = useState("today"); return <main className="phone-shell">{page === "today" ? <Today setPage={setPage} /> : page === "workout" ? <Workout onDone={() => setPage("today")} /> : page === "plan" ? <WeeklyReview /> : <FoodLog setPage={setPage} />}<Navigation page={page} setPage={setPage} /></main>; }
