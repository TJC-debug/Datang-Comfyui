import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function harness() {
  const app = {configuringGraph: false, registerExtension() {}};
  const context = vm.createContext({app});
  const source = fs.readFileSync(new URL('../web/prompt_switchboard_v16.js', import.meta.url), 'utf8').replace(/^import .*\r?\n/, '');
  vm.runInContext(source + '\nglobalThis.commit = commitSwitchboardValue;', context);
  const events = [], widget = {value: 'before', options: {setValue() {throw new Error('must use tracked value');}}};
  const node = {id: 196, widgets: [widget], setDirtyCanvas() {}};
  const graph = {
    getNodeById(id) {return id === node.id ? node : null;},
    beforeChange() {events.push(['before', widget.value]);},
    change() {events.push(['change', widget.value]);},
    afterChange() {events.push(['after', widget.value]);},
    setDirtyCanvas() {},
  };
  node.graph = graph; app.graph = graph;
  app.extensionManager = {workflow: {activeWorkflow: {changeTracker: {checkState() {events.push(['cache', widget.value]);}}}}};
  return {app, node, widget, graph, events, commit: context.commit};
}

test('槽位数据在当前图事务中同步提交，旧值在前、新值在后，刷新缓存无需失焦', () => {
  const h = harness(); h.commit(h.node, h.widget, 'after\n中文🙂');
  assert.deepEqual(h.events, [['before','before'],['after','after\n中文🙂'],['cache','after\n中文🙂']]);
});
test('未变值不创建额外保存或撤销记录', () => {
  const h = harness(); h.commit(h.node,h.widget,'before'); assert.deepEqual(h.events,[]);
});
test('加载恢复期间不写入旧活动工作流缓存', () => {
  const h=harness(); h.app.configuringGraph=true; h.commit(h.node,h.widget,'other');
  assert.equal(h.widget.value,'before'); assert.deepEqual(h.events,[]);
});
test('已卸载或同ID替换的旧节点不改写新工作流', () => {
  const h=harness(); h.node.graph=null; h.commit(h.node,h.widget,'detached');
  h.node.graph=h.graph; h.graph.getNodeById=()=>({id:196}); h.commit(h.node,h.widget,'replaced');
  assert.equal(h.widget.value,'before'); assert.deepEqual(h.events,[]);
});
test('子图的编辑通知其所属图，不把另一活动图缓存当作保存目标', () => {
  const h=harness(); h.app.graph={}; h.commit(h.node,h.widget,'subgraph');
  assert.deepEqual(h.events,[['before','before'],['after','subgraph']]);
});
test('原生value访问器只触发一次，且保留字符串空白与换行', () => {
  const h=harness(); let count=0, value='before';
  Object.defineProperty(h.widget,'value',{get:()=>value,set:v=>{count++; value=v;}});
  h.commit(h.node,h.widget,'  exact\n\n  '); assert.equal(count,1); assert.equal(value,'  exact\n\n  ');
});
test('异常写值仍结束图事务并保留异常，不伪装保存成功', () => {
  const h=harness(); Object.defineProperty(h.widget,'value',{get:()=> 'before',set(){throw new Error('write failed');}});
  assert.throws(()=>h.commit(h.node,h.widget,'after'),/write failed/);
  assert.deepEqual(h.events,[['before','before'],['after','before']]);
});
test('旧前端缺少change或缓存接口也可通过前后事务保存', () => {
  const h=harness(); delete h.graph.change; delete h.app.extensionManager;
  h.commit(h.node,h.widget,'legacy'); assert.deepEqual(h.events,[['before','before'],['after','legacy']]);
});


test('每次编辑只发出一次真实工作流变更，而不叠加graph.change直接通知', () => {
  const h=harness();let state='before',emits=0;
  const check=()=>{if(state!==h.widget.value){state=h.widget.value;emits++;}};
  h.graph.change=()=>{emits++;};h.graph.afterChange=check;
  h.app.extensionManager.workflow.activeWorkflow.changeTracker.checkState=check;
  h.commit(h.node,h.widget,'after');assert.equal(emits,1);
  h.commit(h.node,h.widget,'after');assert.equal(emits,1);
});
