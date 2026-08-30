const COLORS = ['#818cf8','#22d3ee','#a78bfa','#34d399','#fbbf24','#f472b6','#60a5fa','#4ade80','#fb7185','#facc15','#5eead4','#c084fc'];
Chart.defaults.color = 'rgba(238,242,255,.6)';
Chart.defaults.borderColor = 'rgba(255,255,255,.07)';
Chart.defaults.font.family = "'Inter',sans-serif";
let live = [];
export function clearCharts(){ live.forEach(c=>c.destroy()); live = []; }
export function bar(id, labels, data, label, color='#818cf8'){
  const c = new Chart(document.getElementById(id), {type:'bar',
    data:{labels, datasets:[{label, data, borderRadius:8, backgroundColor: ctx => {
      const g = ctx.chart.ctx.createLinearGradient(0,0,0,300); g.addColorStop(0,color); g.addColorStop(1,color+'22'); return g;}}]},
    options:{responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
      scales:{x:{grid:{display:false}},y:{beginAtZero:true}}}});
  live.push(c); return c;
}
export function donut(id, labels, data){
  const c = new Chart(document.getElementById(id), {type:'doughnut',
    data:{labels, datasets:[{data, backgroundColor:COLORS, borderColor:'rgba(7,11,20,.9)', borderWidth:3, hoverOffset:10}]},
    options:{responsive:true, maintainAspectRatio:false, cutout:'68%',
      plugins:{legend:{position:'right', labels:{boxWidth:10, usePointStyle:true}}}}});
  live.push(c); return c;
}
