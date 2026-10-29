export const LEVELS = ['Low','Moderate','High','Severe','No Travel'];
export const COLORS = ['#169b78','#dba437','#ed7939','#d64c4c','#783c70'];
export function classify(wind,rain,snow,load){
  if([wind,rain,snow,load].some(v=>!Number.isFinite(v)||v<0)) throw Error('Invalid risk inputs');
  let w=[25,35,45,55].filter(x=>wind>=x).length;
  if(wind>=55||(wind>=45&&load>30000)) w=4;
  else if(wind>=35&&load>40000) w=Math.max(3,w);
  return Math.max(w,rain>1?4:rain>=.5?3:rain>=.25?2:rain>=.1?1:0,snow>3?4:snow>=2?3:snow>=1?2:snow>=.5?1:0);
}
export function summarize(cps){
  const miles=[0,0,0,0,0];
  cps.slice(1).forEach((p,i)=>miles[Math.max(p.risk,cps[i].risk)]+=p.mile-cps[i].mile);
  const total=miles.reduce((a,b)=>a+b,0);
  return {risk_miles:miles,average_risk:total?miles.reduce((a,m,i)=>a+m*i,0)/total:0,eligible:miles[4]===0};
}
export function recommend(routes){
  return [...routes].filter(r=>r.eligible).sort((a,b)=>a.risk_miles[3]-b.risk_miles[3]||a.risk_miles[2]-b.risk_miles[2]||a.average_risk-b.average_risk||a.duration-b.duration)[0]?.id??null;
}
