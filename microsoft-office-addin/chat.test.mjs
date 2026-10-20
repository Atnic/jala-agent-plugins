import test from 'node:test';
import assert from 'node:assert/strict';
import { CodexChat } from './codex-chat.mjs';
import { resolve } from 'node:path';
import { homedir } from 'node:os';
function fixture() {
  const sent = [], writes = [];
  const directory = resolve(homedir(), '.codex', 'office-chats');
  const state = { threads: {} };
  const projects = { directory, read: async () => state, folder: async path => resolve(path), owns: async thread => Object.hasOwn(state.threads, thread.id) || resolve(thread.cwd) === directory, remember: async (cwd, id) => { state.threads[id] = cwd; } };
  const chat = new CodexChat({ send: m => sent.push(m), documentId: 'selected-document', root: '/plugin', port: 3000, certDirectory: '/certs', projects });
  chat.write = m => writes.push(m);
  return { chat, sent, writes };
}
test('streams visible summaries and filters other threads and private reasoning', () => {
  const { chat, sent } = fixture(); chat.threadId = 'office-thread';
  chat.receive({ method:'item/agentMessage/delta', params:{ threadId:'other-thread', delta:'private' } });
  assert.equal(sent.length, 0);
  chat.receive({ method:'item/completed', params:{ threadId:'office-thread', item:{ type:'reasoning', id:'r', summary:['Visible'], content:['Private'] } } });
  assert.deepEqual(sent[0].params.item, { type:'reasoning', id:'r', summary:['Visible'], content:[] });
  chat.receive({ method:'item/reasoning/textDelta', params:{ threadId:'office-thread', delta:'Private' } });
  assert.equal(sent.length, 1);
});
test('approval remains pending until an explicit valid answer', () => {
  const { chat, writes } = fixture();
  chat.receive({ id:4, method:'item/commandExecution/requestApproval', params:{command:'example'} });
  assert.equal(writes.length, 0);
  assert.throws(()=>chat.answer({id:4,decision:'acceptForSession'}));
  chat.answer({id:4,decision:'decline'});
  assert.deepEqual(writes[0], {id:4,result:{decision:'decline'}});
  assert.throws(()=>chat.answer({id:4,decision:'accept'}));
});
test('permission approval grants only the requested permissions for one turn', () => {
  const { chat, writes } = fixture();
  chat.receive({id:2,method:'item/permissions/requestApproval',params:{permissions:{network:{enabled:true},fileSystem:null}}});
  chat.answer({id:2,decision:'accept',permissions:{fileSystem:{write:['/']}}});
  assert.deepEqual(writes[0].result,{permissions:{network:{enabled:true}},scope:'turn'});
});
test('MCP form validates choices and omits unrequested fields', () => {
  const { chat, writes } = fixture();
  chat.receive({id:5,method:'mcpServer/elicitation/request',params:{mode:'form',requestedSchema:{type:'object',properties:{choice:{type:'string',enum:['allow','deny']}},required:['choice']}}});
  assert.throws(()=>chat.answer({id:5,decision:'accept',content:{choice:'anything'}}));
  chat.answer({id:5,decision:'accept',content:{choice:'allow',extra:'ignore'}});
  assert.deepEqual(writes[0].result.content,{choice:'allow'});
});
test('resume rejects a conversation outside the Office chat directory', async () => {
  const { chat } = fixture();
  chat.rpc = async () => ({thread:{cwd:'/unrelated',id:'other'}});
  await assert.rejects(chat.handle({type:'resume',threadId:'other'}),/created in Office/);
  assert.equal(chat.threadId, undefined);
});
test('new thread does not query unmaterialized history and binds the selected document', async () => {
  const { chat, sent } = fixture();
  const calls=[];chat.rpc=async (method,params)=>{calls.push({method,params});return method === 'thread/list' ? {data:[],nextCursor:null} : {thread:{id:'new'}};};
  await chat.handle({type:'new'});
  assert.deepEqual(calls.map(c=>c.method),['thread/start','thread/list']);
  assert.equal(calls[0].params.config['mcp_servers.office_document'].env.OFFICE_CHAT_DOCUMENT_ID,'selected-document');
  assert.equal(calls[0].params.approvalPolicy,'never');
  assert.equal(sent.find(m=>m.type==='history').turns.length,0);
});
test('interrupt routes to the active turn and session close rejects pending requests', async () => {
  const { chat } = fixture(); chat.threadId='t'; chat.turnId='u';
  const rpc=chat.rpc.bind(chat);let call;chat.rpc=async(method,params)=>{call={method,params};};
  await chat.handle({type:'stop'});assert.deepEqual(call,{method:'turn/interrupt',params:{threadId:'t',turnId:'u'}});
  const pending=rpc('thread/list',{});chat.close();await assert.rejects(pending,/disconnected/);assert.equal(chat.pending.size,0);
});
test('a conversation cannot be resumed in two panes at the same time', async () => {
  const { chat }=fixture(); const owner={}; chat.owners.set('busy-thread',owner);
  chat.rpc=async()=>{throw new Error('Must not reach Codex');};
  await assert.rejects(chat.handle({type:'resume',threadId:'busy-thread'}),/another Office pane/);
  assert.equal(chat.owners.get('busy-thread'),owner);
});
