-- OpenCode 的 opencode.db 縮小版（只有 ComputAI 會讀的兩張表），內容都是假的。
CREATE TABLE session (id text PRIMARY KEY, project_id text NOT NULL, parent_id text, slug text NOT NULL,
  directory text NOT NULL, title text NOT NULL, version text NOT NULL, time_created integer NOT NULL, time_updated integer NOT NULL);
CREATE TABLE message (id text PRIMARY KEY, session_id text NOT NULL, time_created integer NOT NULL, time_updated integer NOT NULL, data text NOT NULL);
CREATE TABLE part (id text PRIMARY KEY, message_id text NOT NULL, session_id text NOT NULL, time_created integer NOT NULL, time_updated integer NOT NULL, data text NOT NULL);
INSERT INTO session VALUES ('ses_main', 'prj', NULL, 'fake-slug', '/home/demo/delta', 'FAKE TITLE', '1.0', 1789000000000, 1789000000000);
INSERT INTO session VALUES ('ses_sub', 'prj', 'ses_main', 'fake-slug-2', '/home/demo/delta', 'FAKE SUBAGENT TITLE', '1.0', 1789000060000, 1789000060000);
INSERT INTO message VALUES ('msg_u1', 'ses_main', 1789000001000, 1789000001000,
  '{"role":"user","time":{"created":1789000001000},"agent":"build","model":{"providerID":"anthropic","modelID":"claude-sonnet-5"},"summary":{"title":"FAKE PROMPT SUMMARY"}}');
INSERT INTO message VALUES ('msg_a1', 'ses_main', 1789000002000, 1789000005000,
  '{"parentID":"msg_u1","role":"assistant","mode":"build","path":{"cwd":"/home/demo/delta","root":"/"},"cost":0.0123,"tokens":{"input":120,"output":300,"reasoning":40,"cache":{"read":5000,"write":800}},"modelID":"claude-sonnet-5","providerID":"anthropic","time":{"created":1789000002000,"completed":1789000005000}}');
INSERT INTO message VALUES ('msg_a2', 'ses_sub', 1789000070000, 1789000072000,
  '{"role":"assistant","path":{"cwd":"/home/demo/delta"},"cost":0,"tokens":{"input":50,"output":20,"reasoning":0,"cache":{"read":0,"write":0}},"modelID":"gpt-5.5","providerID":"openai","time":{"created":1789000070000}}');
INSERT INTO message VALUES ('msg_err', 'ses_main', 1789000080000, 1789000080000,
  '{"role":"assistant","tokens":{"input":0,"output":0,"reasoning":0,"cache":{"read":0,"write":0}},"modelID":"x","time":{"created":1789000080000},"error":{"message":"FAKE ERROR"}}');
INSERT INTO part VALUES ('prt_1', 'msg_a1', 'ses_main', 1789000002000, 1789000002000, '{"type":"text","text":"FAKE ASSISTANT TEXT"}');
