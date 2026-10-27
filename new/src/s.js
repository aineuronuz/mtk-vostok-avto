(()=>{
const $=s=>document.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const RM=matchMedia('(prefers-reduced-motion:reduce)').matches;
const mob=()=>innerWidth<=760;
const clamp=(v,a=0,b=1)=>Math.min(b,Math.max(a,v));
const nf=n=>String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g,' ');

// меню на телефоне
// три чёрточки меню на телефоне шевелятся, пока меню ни разу не открывали (Юрий 27.10.2026)
const bg=$('.burger');if(bg){try{if(localStorage.mbSeen)bg.classList.add('seen')}catch(e){}
  bg.onclick=()=>{document.body.classList.toggle('open');bg.classList.add('seen');try{localStorage.mbSeen=1}catch(e){}}}
$$('.drawer a').forEach(a=>a.addEventListener('click',()=>document.body.classList.remove('open')));

// плавный переход: фото карточки «перелетает» на страницу модели или машины
document.addEventListener('click',e=>{const a=e.target.closest('a[data-vt]');if(!a)return;
  $$('.mpic,.gmain').forEach(x=>x.style.viewTransitionName='none');const im=a.querySelector('img');if(im)im.style.viewTransitionName='car'});
addEventListener('pageshow',()=>$$('a[data-vt] img').forEach(i=>i.style.viewTransitionName=''));

// появление
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{rootMargin:'0px 0px -8% 0px'});
$$('.rv,.deck').forEach(e=>io.observe(e));
// счётчики
const co=new IntersectionObserver(es=>es.forEach(e=>{if(!e.isIntersecting)return;co.unobserve(e.target);const b=e.target,n=+b.dataset.n,f=+(b.dataset.from||0),t0=performance.now();
  const st=t=>{const p=clamp((t-t0)/1600),v=Math.round(f+(n-f)*(1-Math.pow(1-p,3)));b.textContent=v;if(p<1)requestAnimationFrame(st)};if(!RM)requestAnimationFrame(st)}),{threshold:.6});
$$('[data-n]').forEach(e=>co.observe(e));

// первый экран: видео идёт без остановки
const hv=$('#hv');
if(hv){hv.muted=hv.defaultMuted=true;
  const go=()=>{const p=hv.play();if(p&&p.catch)p.catch(()=>{})};
  ['pause','ended','loadedmetadata','canplay'].forEach(e=>hv.addEventListener(e,go));
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)go()});
  ['pointerdown','touchstart','keydown'].forEach(e=>addEventListener(e,go,{passive:true}));
  setInterval(()=>{if(hv.paused)go()},1000);go()}

// блоки на главной: ролик грузится, когда блок близко, и играет, пока его видно
const dvs=$$('.dv');
if(dvs.length){const run=v=>{const p=v.play();if(p&&p.catch)p.catch(()=>{})};
  const dvo=new IntersectionObserver(es=>es.forEach(e=>{const v=e.target;v._in=e.isIntersecting;
    if(v._in){if(!v.src){v.src=mob()?v.dataset.srcM:v.dataset.src;v.addEventListener('playing',()=>v.classList.add('on'),{once:true})}run(v)}else if(v.src)v.pause()}),{rootMargin:'300px 0px'});
  dvs.forEach(v=>{v.muted=v.defaultMuted=true;dvo.observe(v)});
  ['pointerdown','touchstart','keydown'].forEach(e=>addEventListener(e,()=>dvs.forEach(v=>{if(v._in&&v.src&&v.paused)run(v)}),{passive:true}))}

// шапки разделов: ролик справа (Каталог, Премиум) и калькулятор «Стоимости» (Юрий 26.10.2026)
$$('.phv video').forEach(v=>{if(RM)return;v.muted=v.defaultMuted=true;v.src=mob()?v.dataset.srcM:v.dataset.src;
  const go=()=>{const p=v.play();if(p&&p.catch)p.catch(()=>{})};v.addEventListener('canplay',go,{once:true});go();
  ['pointerdown','touchstart'].forEach(e=>addEventListener(e,go,{once:true,passive:true}))});
const CF=$('.phcalc');
// калькулятор «Стоимости» (Юрий 27.10.2026): двигатель, возраст, объём, мощность → под ключ и расшифровка, как в КП «Авто»
if(CF){const d=JSON.parse(CF.dataset.calc),el=CF.elements,$c=s=>$(s,CF),out=$c('[data-total]'),ccl=$c('.cc'),pl=$c('[data-pl]'),hint=$c('[data-hint]'),ut=$c('[data-ut]'),
    warn=$c('[data-warn]'),wt=$c('[data-wt]'),brk=$c('[data-brk]');
  const step=(t,v,top)=>{for(const[k,x]of t)if(v<=k)return x;return top};
  const coef=(t,kw)=>{for(const[m,c]of t)if(m==null||kw<=m)return c;return t[t.length-1][1]};
  const akc=hp=>{for(const[t,r]of d.akc)if(t==null||hp<=t)return r};
  const R=n=>nf(n)+' ₽';
  const run=()=>{const y=+el.y.value||0,t=el.t.value,a=+el.a.value,c=+el.cc.value||0,el3=t!='ice',kwIn=el.u.value=='kw',p=+el.p.value||0;
    ccl.style.display=el3?'none':'';pl.textContent=el3?'Максимальная мощность':'Мощность';
    const hp=kwIn?p*1.35962:p,kw=kwIn?p:p*.7355;
    const car=Math.round(y*d.vtb),del=Math.round(d.deliv*d.vtb),ld=Math.round(d.load*d.vtb),bank=Math.round((car+del)*d.bank),cv=Math.round((y+d.deliv)*d.cny);
    const fee=step(d.fee,cv,d.feeTop),ak=a==0?'less_3':'over_3',L=[[`Автомобиль с доставкой (${nf(y+d.deliv)} ¥)`,car+del],['Погрузка и доставка по Китаю',ld],['Комиссия банка ВТБ 2%',bank]];
    let duty,akz=0,vat=0,rec,kw30=kw,pref;
    if(el3){kw30=kw*d.k30;const hp30=Math.round(kw30*1.35962);duty=Math.round(cv*.15);akz=hp30*akc(hp30);vat=Math.round((cv+duty+akz)*.22);
      rec=Math.round(20000*coef(d.rec.electric_sequential[ak],kw30));
      L.push(['Пошлина 15%',duty]);if(akz)L.push([`Акциз (${hp30} л.с.)`,akz]);L.push(['НДС 22%',vat]);
      hint.textContent=`Сбор и акциз считаются по 30-минутной мощности: ≈${Math.round(kw30)} кВт (${hp30} л.с.) — 45% от максимальной. Точную берём из документов машины.`}
    else{if(a==0){const[pc,ec]=step(d.lt3,cv/d.eur,d.lt3Top);duty=Math.round(Math.max(cv*pc,ec*c*d.eur))}else{duty=Math.round(c*step(d.gt3,c,d.gt3Top)[a==1?0:1]*d.eur)}
      const tk=c<=1000?'ice_upto_1000':c<=2000?'ice_1000_2000':c<=3000?'ice_2000_3000':c<=3500?'ice_3000_3500':'ice_over_3500';
      rec=Math.round(20000*coef(d.rec[tk][ak],kw));L.push(['Пошлина',duty]);
      hint.textContent='У гибрида — суммарная мощность системы. Льготный утильсбор — до 160 л.с. и объёма до 3 л.'}
    pref=rec<=5200;
    L.push(['Таможенный сбор',fee],['Утильсбор'+(pref?' — льготный':' — полный'),rec],['Склад временного хранения',d.svh],['Оформление: растаможка, СБКТС, ЭПТС',d.clr],['Подбор и сопровождение сделки',d.svc]);
    const ok=y>=1000&&p>0&&(el3||c>=600),tot=L.reduce((s,x)=>s+x[1],0);
    out.textContent=ok?R(tot):'—';ut.textContent=ok?(pref?'Утильсбор льготный':'Утильсбор полный: '+R(rec)):'';ut.classList.toggle('bad',ok&&!pref);
    warn.hidden=!ok||pref;if(ok&&!pref)wt.textContent=`Полный утильсбор — ${R(rec)}. Подберём похожую машину ${el3?'до 80 л.с. по 30-минутной мощности':'до 160 л.с.'} с льготным сбором 3 400–5 200 ₽. Напишите нам.`;
    brk.innerHTML=ok?L.map(([k,v])=>`<tr><td>${k}</td><td>${R(v)}</td></tr>`).join('')+`<tr><td><b>Итого под ключ</b></td><td><b>${R(tot)}</b></td></tr>`:''};
  CF.addEventListener('input',run);CF.addEventListener('change',run);run()}

// «Авто в Китае»: витрина — карточки последних машин сменяют друг друга (Юрий 27.10.2026)
const SH=$('[data-show]');
if(SH){const cs=$$('.shc',SH);let k=0,tm;const set=()=>cs.forEach((c,i)=>{const q=(i-k+cs.length)%cs.length;c.dataset.d=q>3?4:q});
  const go=()=>{clearInterval(tm);if(!RM&&cs.length>1)tm=setInterval(()=>{k=(k+1)%cs.length;set()},2500)};
  set();go();SH.addEventListener('mouseenter',()=>clearInterval(tm));SH.addEventListener('mouseleave',go)}

// слова подсвечиваются
const W=$('#words');let ws=[];
if(W){W.innerHTML=W.innerHTML.split(/(\s+)/).map(t=>{if(/^\s+$/.test(t)||!t)return t;const k=t.includes('*');return `<span class="w${k?' k':''}">${t.replace(/\*/g,'')}</span>`}).join('');ws=$$('#words .w')}

// лента машин на главной: при каждом открытии в новом порядке (Юрий 26.10.2026; набор на день выбирает сборка)
$$('[data-shuffle]').forEach(r=>{const a=[...r.children];for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}a.forEach(c=>r.appendChild(c))});

// ленты со стрелками
$$('[data-reel]').forEach(b=>{const r=document.getElementById(b.dataset.reel);b.onclick=()=>r.scrollBy({left:+b.dataset.d*r.clientWidth*.8,behavior:'smooth'})});

// фильтры каталога и машин
const L=$('[data-list]');
if(L){
  const cards=$$('.card',L),cnt=$('#cnt'),emp=$('#empty'),sortSel=$('[data-sort]'),params=new URLSearchParams(location.search);
  const groups=$$('[data-f]');
  groups.forEach(g=>{const k=g.dataset.f,v=params.get(k);if(v==null)return;
    if(g.matches('.chips,.tiles'))v.split(',').forEach(x=>{const c=g.querySelector(`[data-v="${x}"]`);if(c)c.classList.add('on')});else g.value=v});
  if(sortSel&&params.get('sort'))sortSel.value=params.get('sort');
  const st=()=>{const s={};groups.forEach(g=>{const k=g.dataset.f;
      if(g.matches('.chips,.tiles')){const on=$$('.on',g).map(c=>c.dataset.v);if(on.length)s[k]=on}
      else if(g.type=='range'){if(+g.value<+g.max)s[k]=+g.value}
      else if(g.value!=='')s[k]=g.value});return s};
  const lbl=$$('[data-out]');
  const apply=(push=true)=>{const s=st();let n=0;
    lbl.forEach(o=>{const g=$(`[data-f="${o.dataset.out}"]`);o.textContent=+g.value>=+g.max?'любая':`до ${(+g.value/1e6).toFixed(1).replace('.',',')} млн ₽`});
    cards.forEach(c=>{const d=c.dataset;let ok=true;
      for(const k in s){const v=s[k];
        if(Array.isArray(v)){if(k=='feat'){if(!v.every(x=>(d.feat||'').split(' ').includes(x)))ok=false}else if(!v.some(x=>(d[k]||'').split(' ').includes(x)))ok=false}
        else if(k=='q'){if(!d.q.includes(v.trim().toLowerCase()))ok=false}
        else if(k=='price'){if(+d.price>v)ok=false}
        else if(k=='ymin'){if(+d.year<+v)ok=false}
        else if(k=='kmmax'){if(+d.km>+v)ok=false}
        else if((d[k]||'')!=v)ok=false;
        if(!ok)break}
      c.classList.toggle('x',!ok);if(ok){n++;if(!RM){c.style.animation='none';void c.offsetWidth;c.style.animation=''}}});
    if(sortSel){const m=sortSel.value,[f,dir]=m.split('-');const arr=cards.slice().sort((a,b)=>{const x=a.dataset[f],y=b.dataset[f];
        const r=isNaN(+x)?x.localeCompare(y,'ru'):(+x)-(+y);return dir=='desc'?-r:r});arr.forEach(c=>L.appendChild(c))}
    if(cnt)cnt.textContent=n;if(emp)emp.classList.toggle('on',n==0);if(typeof sync=='function')sync();
    if(push){const p=new URLSearchParams();for(const k in s)p.set(k,Array.isArray(s[k])?s[k].join(','):s[k]);if(sortSel&&sortSel.selectedIndex>0)p.set('sort',sortSel.value);
      history.replaceState(null,'',location.pathname+(p.toString()?'?'+p:''))}};
  // плитки каталога (Электро, Гибриды, Бензин, Полный привод): после выбора страница плавно уходит к списку моделей (Юрий 26.10.2026)
  // трогается сразу и плавно тормозит у списка, без медленного разгона — он выглядел как задержка (Юрий 27.10.2026, вечер)
  const toList=()=>{const t=L.closest('.lay')||L,h=$('#hdr'),hh=(h?h.offsetHeight:90)+16,y0=scrollY,y1=t.getBoundingClientRect().top+scrollY-hh;
    if(RM){scrollTo(0,y1);return}const t0=performance.now(),D=Math.min(800,Math.max(450,Math.abs(y1-y0)*.6)),ez=p=>1-Math.pow(1-p,3);
    const de=document.documentElement;de.style.scrollBehavior='auto';   // иначе scroll-behavior:smooth из CSS растягивает каждый шаг
    const st=n=>{const p=clamp((n-t0)/D);scrollTo(0,y0+(y1-y0)*ez(p));if(p<1)requestAnimationFrame(st);else de.style.scrollBehavior=''};requestAnimationFrame(st)};
  // плитки Каталога — быстрый выбор того же, что в панели «Топливо» и «Привод» (Юрий 27.10.2026)
  const tiles=$$('.tiles [data-to]'),chip=b=>$(`[data-f="${b.dataset.to}"] [data-v="${b.dataset.v}"]`),sync=()=>tiles.forEach(b=>{const c=chip(b);b.classList.toggle('on',!!c&&c.classList.contains('on'))});
  const CAT={ev:'fuel:ev',hyb:'fuel:hybrid',fwd:'fuel:petrol',awd:'feat:awd'};
  (params.get('cat')||'').split(',').forEach(x=>{if(!CAT[x])return;const[f,v]=CAT[x].split(':'),c=$(`[data-f="${f}"] [data-v="${v}"]`);if(c)c.classList.add('on')});
  tiles.forEach(b=>b.addEventListener('click',()=>{const c=chip(b);if(!c)return;c.classList.toggle('on');apply();requestAnimationFrame(toList)}));
  groups.forEach(g=>{if(g.matches('.chips,.tiles'))g.addEventListener('click',e=>{const c=e.target.closest('[data-v]');if(!c)return;
      if(g.dataset.one!=null)$$('[data-v]',g).forEach(x=>{if(x!=c)x.classList.remove('on')});c.classList.toggle('on');apply();if(g.matches('.tiles'))setTimeout(toList,60)});
    else g.addEventListener('input',()=>apply())});
  if(sortSel)sortSel.addEventListener('change',()=>apply());
  $$('[data-reset]').forEach(b=>b.onclick=()=>{groups.forEach(g=>{if(g.matches('.chips,.tiles'))$$('.on',g).forEach(c=>c.classList.remove('on'));else if(g.type=='range')g.value=g.max;else g.value=''});apply()});
  $$('[data-fopen]').forEach(b=>b.onclick=()=>document.body.classList.toggle('fopen'));
  apply(false);
}

// галерея машины
const G=$('.gmain');
if(G){const ims=$$('img',G),th=$$('.gth img'),gn=$('.gn',G),lb=$('.lbox'),li=lb&&$('img',lb);let i=0;
  const go=k=>{i=(k+ims.length)%ims.length;ims.forEach((e,j)=>{e.classList.toggle('on',j==i);if(j==i&&e.dataset.src){e.src=e.dataset.src;delete e.dataset.src}});
    th.forEach((e,j)=>e.classList.toggle('on',j==i));if(gn)gn.textContent=`${i+1} / ${ims.length}`;if(li&&lb.classList.contains('on'))li.src=ims[i].dataset.big||ims[i].src;
    const n=ims[(i+1)%ims.length];if(n.dataset.src){n.src=n.dataset.src;delete n.dataset.src}};
  th.forEach((e,j)=>e.onclick=()=>go(j));
  $('.pv',G).onclick=e=>{e.stopPropagation();go(i-1)};$('.nx',G).onclick=e=>{e.stopPropagation();go(i+1)};
  let x0=null;G.addEventListener('touchstart',e=>x0=e.touches[0].clientX,{passive:true});
  G.addEventListener('touchend',e=>{if(x0==null)return;const dx=e.changedTouches[0].clientX-x0;if(Math.abs(dx)>40)go(i+(dx<0?1:-1));x0=null});
  if(lb){G.addEventListener('click',()=>{lb.classList.add('on');li.src=ims[i].dataset.big||ims[i].src});
    $('.x',lb).onclick=()=>lb.classList.remove('on');$('.pv',lb).onclick=()=>go(i-1);$('.nx',lb).onclick=()=>go(i+1);
    lb.addEventListener('click',e=>{if(e.target==lb)lb.classList.remove('on')});
    addEventListener('keydown',e=>{if(!lb.classList.contains('on'))return;if(e.key=='Escape')lb.classList.remove('on');if(e.key=='ArrowLeft')go(i-1);if(e.key=='ArrowRight')go(i+1)})}
  go(0)}

// прокрутка
const hdr=$('#hdr'),top0=$('.hero,.phead,.mhero'),hc=$('#hc'),fr=$('#fr'),grow=$('#grow'),how=$('#how'),track=$('#track'),prog=$('#prog'),pays=$('#pays'),fin=$('#finbg'),tl=$('.tl');
const tt=$('.totop');if(tt)tt.addEventListener('click',e=>{e.preventDefault();scrollTo({top:0,behavior:RM?'auto':'smooth'})});
let ticking=false;
function frame(){
  ticking=false;const y=scrollY,vh=innerHeight,vw=innerWidth;
  const past=y>(top0?top0.offsetHeight-90:0);hdr.classList.toggle('solid',past);hdr.classList.toggle('sc',!past&&y>6);   // над тёмной шапкой — тёмно-синий фон (Юрий 27.10.2026)
  if(tt)tt.classList.toggle('on',y>vh*1.5);
  if(RM)return;
  if(hc&&y<vh*1.2){const p=clamp(y/vh);hc.style.transform=mob()?`translateY(${p*-50}px)`:`translateY(calc(-42% - ${p*80}px))`;hc.style.opacity=mob()?1-p*.9:1-p*1.3}
  if(ws.length){const r=W.getBoundingClientRect(),wp=clamp((vh*.86-r.top)/(r.height+vh*.36)),nOn=Math.round(wp*ws.length*1.08);ws.forEach((w,i)=>w.classList.toggle('on',i<nOn))}
  if(grow&&!mob()){const g=grow.getBoundingClientRect(),gp=clamp(-g.top/(g.height-vh)),e=clamp(gp/.6);
    fr.style.width=`${60+40*e}vw`;fr.style.height=`${62+38*e}vh`;fr.style.borderRadius=`${28*(1-e)}px`;fr.style.setProperty('--o',clamp((gp-.45)/.3))}
  if(how&&track){if(!mob()){const h=how.getBoundingClientRect(),dist=track.scrollWidth-vw;how.style.height=`${dist+vh}px`;
    const hp=clamp(-h.top/(how.offsetHeight-vh));track.style.transform=`translateX(${-hp*dist}px)`;if(prog)prog.style.setProperty('--p',hp)}else how.style.height=''}
  if(pays){const pr=pays.getBoundingClientRect(),pp=clamp((vh*.8-pr.top)/(vh*.55));pays.style.setProperty('--p',pp);const p4=$$('.pay4',pays);p4.forEach((e,i)=>e.classList.toggle('on',pp>=i/(p4.length-1)-.01&&pp>0))}
  if(tl){const r=tl.getBoundingClientRect(),h=clamp(vh*.6-r.top,0,r.height-40);tl.style.setProperty('--h',h+'px');$$('.ts',tl).forEach(s=>s.classList.toggle('on',s.getBoundingClientRect().top+40<vh*.6))}
  $$('.dc').forEach(d=>{const b=d.getBoundingClientRect();if(b.bottom<0||b.top>vh)return;const q=(b.top+b.height/2-vh/2)/vh;$$('img',d).forEach(im=>im.style.transform=`translateY(${q*-6}%)`)});
  if(fin){const fb=fin.getBoundingClientRect();if(fb.top<vh&&fb.bottom>0)fin.style.transform=`translateY(${(fb.top/vh)*-8}%)`}
}
const req=()=>{if(!ticking){ticking=true;requestAnimationFrame(frame)}};
addEventListener('scroll',req,{passive:true});addEventListener('resize',req);addEventListener('load',req);frame();
if(!RM&&$('.dc'))setInterval(()=>$$('.dc').forEach((d,i)=>setTimeout(()=>d.classList.toggle('alt'),i*500)),4200);
})();
