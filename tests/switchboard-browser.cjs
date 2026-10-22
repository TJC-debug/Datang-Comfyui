const fs=require('node:fs/promises'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {chromium}=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const root=process.cwd(),out=process.env.SWITCHBOARD_QA_DIR||path.join(require('node:os').tmpdir(),'datang-switchboard-qa');await fs.mkdir(out,{recursive:true});
 const source=await fs.readFile(process.env.SWITCHBOARD_SOURCE||path.join(root,'web/prompt_switchboard_v16.js'),'utf8');
 const setup=`
 const initial={A:[JSON.stringify([{name:'A 第一项',text:'A 原提示词',enabled:true,_selection_mode:'多选'},{name:'A 第二项',text:'A 保留内容',enabled:false}]),', '],B:[JSON.stringify([{name:'B 第一项',text:'B 原提示词',enabled:true,_selection_mode:'多选'},{name:'B 第二项',text:'B 保留内容',enabled:true}]),' / ']};
 const copy=v=>JSON.parse(JSON.stringify(v)); let current=null,extension=null,nodes=[],tabs=copy(initial),changes=0;
 const graph={_nodes:nodes,getNodeById(id){return nodes.find(n=>n.id===id);},setDirtyCanvas(){},beforeChange(){},change(){},afterChange(){cache();}};
 function values(){return nodes[0].widgets.filter(w=>w.serialize!==false).map(w=>w.serializeValue?w.serializeValue():w.value);}
 function cache(){if(!window.__app.configuringGraph&&current&&nodes.length){tabs[current]=copy(values());changes++;}}
 const app=window.__app={graph,configuringGraph:false,registerExtension(e){extension=e;},extensionManager:{workflow:{activeWorkflow:{changeTracker:{checkState:cache}}}}};
 async function mount(key){
  app.configuringGraph=true; for(const node of nodes)node.graph=null;nodes=[];graph._nodes=nodes;
  current=key;document.querySelector('#host').replaceChildren();
  const data={name:'提示词数据',type:'customtext',value:'[]',options:{},onRemove(){}};
  const separator={name:'分隔符',type:'text',value:', ',options:{}};
  const node={id:196,comfyClass:'PromptSwitchboard',graph,size:[420,500],widgets:[data,separator],setSize(size){this.size=size;},setDirtyCanvas(){},
    addDOMWidget(name,type,element,options){const w={name,type,element,options};this.widgets.push(w);document.querySelector('#host').append(element);return w;}};
  nodes.push(node);await extension.nodeCreated(node);
  node.widgets[0].value=tabs[key][0];node.widgets[1].value=tabs[key][1];app.configuringGraph=false;
  await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
  document.querySelector('#tab-label').textContent=key;
 }
 window.qa={mount,values,get state(){return copy(tabs);},get changes(){return changes;},restore(state){tabs=copy(state);return mount(current);},external(value){nodes[0].widgets[0].value=value;},node(){return nodes[0];}};
 document.querySelector('#tab-a').onclick=()=>mount('A');document.querySelector('#tab-b').onclick=()=>mount('B');
 `;
 const html=`<meta charset='utf-8'><style>body{background:#242424;color:white;font:13px sans-serif;margin:12px}#host{width:420px;height:570px;margin-top:20px}button{background:#333;color:#ddd}#tabs{height:30px}</style><div id='tabs'><button id='tab-a'>工作流 A</button><button id='tab-b'>工作流 B</button><span id='tab-label'></span></div><div id='host'></div><script>${setup}</script><script type='module'>import '/extensions/Datang-Comfyui/prompt_switchboard_v16.js';await window.qa.mount('A');</script>`;
 const server=http.createServer((req,res)=>{res.setHeader('Content-Type',req.url.endsWith('.js')?'text/javascript; charset=utf-8':'text/html; charset=utf-8');res.end(req.url==='/scripts/app.js'?'export const app=window.__app;':req.url.includes('/extensions/')?source:html);});
 await new Promise(r=>server.listen(0,'127.0.0.1',r)); const base='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({channel:'chrome',headless:true}),page=await browser.newPage({viewport:{width:600,height:800}}),errors=[],checks=[];
 page.on('pageerror',e=>errors.push(e.message));await page.route('**/*',r=>r.request().url().startsWith(base+'/')?r.continue():r.abort());
 const tab=async key=>{await page.locator('#tab-'+key.toLowerCase()).click();await page.waitForFunction(k=>document.querySelector('#tab-label').textContent===k,key);};
 try{
  await page.goto(base);await page.waitForFunction(()=>document.querySelector('#tab-label').textContent==='A');assert.equal(await page.locator('.prompt-switchboard textarea').count(),2);
  const editor=page.locator('.prompt-switchboard textarea').first();
  const a='  新的 A 提示词\n保留换行、空格 <image1> 🙂\n\n末尾  ';
  await editor.fill(a);
  const immediate=await page.evaluate(()=>({saved:JSON.parse(qa.state.A[0])[0].text,api:JSON.parse(qa.values()[0])[0].text,focused:document.activeElement.tagName}));
  assert.equal(immediate.saved,a,'输入新文字后、尚未失焦时必须已更新工作流缓存');assert.equal(immediate.api,a);assert.equal(immediate.focused,'TEXTAREA');
  checks.push('输入后未失焦即同步保存缓存与API，空格换行及Unicode完整保留');
  await editor.evaluate(el=>window.qaEditor=el);await editor.press('End');await page.keyboard.type('12345');await page.waitForTimeout(100);
  assert.equal(await editor.evaluate(el=>window.qaEditor===el&&document.activeElement===el),true);const latestA=await editor.inputValue();
  assert.equal(JSON.parse((await page.evaluate(()=>qa.state)).A[0])[0].text,latestA);
  checks.push('连续键入不重建编辑区，焦点、光标与当前输入保持');
  await page.evaluate(()=>qa.external(qa.values()[0]));await page.waitForTimeout(60);assert.equal(await editor.evaluate(el=>window.qaEditor===el),true);await page.keyboard.type('6');assert.equal(JSON.parse((await page.evaluate(()=>qa.state)).A[0])[0].text,await editor.inputValue());const finalA=await editor.inputValue();
  checks.push('同值外部回调保留原编辑区，后续键入继续保存当前槽位');
  await page.locator('.prompt-switchboard__name').first().fill('A 修改名称');
  await page.locator('.prompt-switchboard__separator').fill(' | ');
  await page.locator('.prompt-switchboard__mode').selectOption('单选');
  await page.locator('.prompt-switchboard__toggle').nth(1).click();assert.equal(await page.locator('.prompt-switchboard__toggle input').nth(1).isChecked(),true);
  const savedA=await page.evaluate(()=>qa.state.A);assert.equal(JSON.parse(savedA[0])[0].enabled,false);assert.equal(JSON.parse(savedA[0])[1].enabled,true);
  await tab('B');await page.locator('.prompt-switchboard textarea').first().fill('B 独立修改\n不覆盖 A');
  const savedB=await page.evaluate(()=>qa.state.B);
  for(let i=0;i<3;i++){await tab('A');assert.equal(await page.locator('.prompt-switchboard textarea').first().inputValue(),finalA);assert.equal(await page.locator('.prompt-switchboard__name').first().inputValue(),'A 修改名称');assert.equal(await page.locator('.prompt-switchboard__mode').inputValue(),'单选');assert.equal(await page.locator('.prompt-switchboard__separator').inputValue(),' | ');await tab('B');assert.deepEqual(await page.evaluate(()=>qa.values()),savedB);}
  checks.push('同节点ID的A/B工作流反复切换，各自文本、名称、开关、模式、分隔符独立保存');
  await tab('A');await page.locator('.prompt-switchboard__add').click();await page.locator('.prompt-switchboard textarea').nth(2).fill('新增第三项');
  assert.equal(JSON.parse((await page.evaluate(()=>qa.state)).A[0]).length,3);
  await page.locator('.prompt-switchboard__delete').nth(0).click();const afterDelete=await page.evaluate(()=>qa.state.A);
  await tab('B');await tab('A');assert.deepEqual(await page.evaluate(()=>qa.values()),afterDelete);
  checks.push('新增和删除槽位后立即切换，数量与内容保持');
  const beforeOrder=JSON.parse((await page.evaluate(()=>qa.state)).A[0]);
  const handle=await page.locator('.prompt-switchboard__reorder').first().boundingBox(),lastRow=await page.locator('.prompt-switchboard__row').last().boundingBox();
  await page.mouse.move(handle.x+handle.width/2,handle.y+handle.height/2);await page.mouse.down();await page.mouse.move(lastRow.x+20,lastRow.y+lastRow.height-2,{steps:10});await page.mouse.up();
  const ordered=await page.evaluate(()=>qa.state.A);assert.deepEqual(JSON.parse(ordered[0]).map(i=>i.text),beforeOrder.map(i=>i.text).reverse());await tab('B');await tab('A');assert.deepEqual(await page.evaluate(()=>qa.values()),ordered);
  checks.push('实际拖动槽位排序后切换，顺序与文本一起保存');
  await page.getByRole('button',{name:'全关',exact:true}).click();assert.ok(JSON.parse((await page.evaluate(()=>qa.state)).A[0]).every(i=>!i.enabled));
  await page.locator('.prompt-switchboard__mode').selectOption('多选');await page.getByRole('button',{name:'全开',exact:true}).click();assert.ok(JSON.parse((await page.evaluate(()=>qa.state)).A[0]).every(i=>i.enabled));
  checks.push('单选/多选和全开全关继续保存，后端输入结构不变');
  const current=await page.evaluate(()=>qa.state);await page.reload();await page.waitForFunction(()=>document.querySelector('#tab-label').textContent==='A');await page.evaluate(s=>qa.restore(s),current);assert.deepEqual(await page.evaluate(()=>qa.values()),current.A);await tab('B');assert.deepEqual(await page.evaluate(()=>qa.values()),current.B);
  checks.push('保存的控件数据重新载入后继续保留，加载阶段不污染另一工作流');
  const external=JSON.stringify([{name:'外部恢复',text:'外部合法载入值',enabled:true,_selection_mode:'多选'}]);await page.evaluate(v=>qa.external(v),external);await page.waitForFunction(()=>document.querySelector('.prompt-switchboard textarea').value==='外部合法载入值');await page.locator('.prompt-switchboard textarea').first().fill('外部载入后仍可修改');assert.equal(JSON.parse((await page.evaluate(()=>qa.state)).B[0])[0].text,'外部载入后仍可修改');
  checks.push('外部配置恢复会刷新界面，随后仍能正常修改和保存');
  await page.evaluate(()=>qa.external(JSON.stringify([{name:'历史单选一',text:'保留一',enabled:true,_selection_mode:'单选'},{name:'历史单选二',text:'保留二',enabled:true}])));await page.waitForFunction(()=>document.querySelectorAll('.prompt-switchboard__row').length===2);assert.deepEqual(await page.locator('.prompt-switchboard__toggle input').evaluateAll(es=>es.map(e=>e.checked)),[true,false]);
  checks.push('历史单选数据有多个开启项时，仍沿用原有单选约束');
  const idleCount=await page.evaluate(()=>qa.changes);await page.waitForTimeout(900);assert.equal(await page.evaluate(()=>qa.changes),idleCount);
  checks.push('停止操作后无持续工作流保存通知，不使用空闲重试循环');
  await page.screenshot({path:path.join(out,'switchboard-preserved.png')});assert.deepEqual(errors,[]);
  await fs.writeFile(path.join(out,'report.json'),JSON.stringify({checks,errors,isolatedHost:true,realComfyUI:false,realCloud:false},null,2));console.log(JSON.stringify({checks,errors}));
 }catch(e){await page.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});throw e;}
 finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
