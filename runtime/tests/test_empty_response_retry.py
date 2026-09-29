import copy
import ast
import json
import os
import sys
import types
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from engiworld.agents import openai_compatible as transport
from engiworld.scheduler.schemas import AgentConfig

SPEC = transport.OpenAICompatibleAgentSpec(
    display_name="Compatible model", default_model="example-model",
    default_base_url="https://example.invalid/v1", api_key_env="OPENAI_API_KEY",
    env_prefix="ARENA_MODEL",
)


class EmptyResponseRetryTest(unittest.TestCase):
    def request(self, responses, *, stream=False, retries=3, **options):
        sent=[];attempts=[]
        original={'model':'kimi-k3','messages':[{'role':'user','content':[{'type':'text','text':'Original instruction'},{'type':'image_url','image_url':{'url':'data:image/png;base64,eA=='}}]}],'max_tokens':16384}
        before=copy.deepcopy(original);iterator=iter(responses)
        def post(*args,**kwargs):
            sent.append(copy.deepcopy(kwargs));response=next(iterator)
            if isinstance(response,Exception):raise response
            return 200,json.dumps(response)
        method='_post_stream_json' if stream else '_post_json'
        kwargs=dict(base_url='https://example.invalid/v1',api_key='test-only',provider_name='Kimi',reasoning_effort='max',retry_empty_response=True,timeout_seconds=600,retries=retries,attempt_log=attempts,**options)
        if stream:kwargs['stream']=True
        with patch.object(transport,method,side_effect=post),patch.object(transport.time,'sleep'):
            try:result=transport.call_chat_completions(original,**kwargs)
            except transport.OpenAICompatibleAPIError as exc:result=exc
        self.assertEqual(original,before)
        self.assertTrue(all(x['payload']==sent[0]['payload'] for x in sent))
        self.assertTrue(all(x['timeout']==600 for x in sent))
        self.assertEqual(sent[0]['payload']['messages'],original['messages'])
        return result,sent,attempts

    @staticmethod
    def response(content='',reasoning='Thinking',finish='length'):
        return {'choices':[{'finish_reason':finish,'message':{'content':content,'reasoning_content':reasoning}}],'usage':{'completion_tokens':16384}}

    def test_shared_policy_retries_identically_without_corrective_prompts(self):
        self.assertTrue(SPEC.retry_empty_response)
        self.assertFalse(SPEC.retry_reasoning_only_response)
        self.assertTrue(SPEC.retry_stream_errors)
        self.assertEqual(SPEC.retry_backoff_seconds,0.0)

    def test_reasoning_only_then_success_preserves_request(self):
        result,sent,attempts=self.request([self.response(),self.response('ACTION')])
        self.assertEqual(result,'ACTION');self.assertEqual(len(sent),2)
        self.assertEqual([x['status'] for x in attempts],['reasoning_only','ok'])
        self.assertEqual(attempts[0]['raw_finish_reason'],'length')
        self.assertEqual(attempts[0]['usage']['completion_tokens'],16384)
        self.assertEqual(attempts[0]['retry_policy'],'empty-response-identical-request-v1')

    def test_empty_and_whitespace_then_third_attempt_success(self):
        result,sent,attempts=self.request([self.response(None,None,'stop'),self.response('  ','','stop'),self.response('ACTION')])
        self.assertEqual(result,'ACTION');self.assertEqual(len(sent),3)
        self.assertEqual([x['status'] for x in attempts],['empty_response','empty_response','ok'])

    def test_exhaustion_is_exactly_three_attempts(self):
        result,sent,attempts=self.request([self.response()]*3)
        self.assertIsInstance(result,transport.OpenAICompatibleAPIError)
        self.assertIn('after 3 attempt(s)',str(result));self.assertEqual(len(sent),3)
        self.assertEqual(len(attempts),3)

    def test_exception_and_empty_share_one_three_attempt_budget(self):
        result,sent,attempts=self.request([TimeoutError('timeout'),self.response(),self.response('ACTION')])
        self.assertEqual(result,'ACTION');self.assertEqual(len(sent),3)
        self.assertEqual([x['status'] for x in attempts],['exception','reasoning_only','ok'])

    def test_streaming_uses_the_same_policy(self):
        if not hasattr(transport,'_post_stream_json'):self.skipTest('Streaming adapter exists only in newer deployed source')
        result,sent,attempts=self.request([self.response(),self.response('ACTION')],stream=True)
        self.assertEqual(result,'ACTION');self.assertEqual(len(sent),2)

    def test_factory_passes_policy_to_transport(self):
        package=types.ModuleType('mm_agents');package.__path__=[]
        agent=types.ModuleType('mm_agents.agent');errors=types.ModuleType('mm_agents.errors')
        class FakeAgent:
            def __init__(self,**kwargs):pass
        class FakeAPIError(RuntimeError):
            def __init__(self,message,**kwargs):super().__init__(message)
        agent.PromptAgent=FakeAgent;errors.ModelAPIError=FakeAPIError
        env={'OPENAI_API_KEY':'test-only','ARENA_MODEL_API_RETRIES':'3','ARENA_MODEL_TIMEOUT_SECONDS':'600','ARENA_OPENAI_COMPAT_HOTSWAP_ENABLED':'false'}
        with patch.dict(sys.modules,{'mm_agents':package,'mm_agents.agent':agent,'mm_agents.errors':errors}),patch.dict(os.environ,env,clear=True),patch.object(transport,'call_chat_completions',return_value='ACTION') as call:
            a=transport.create_prompt_agent(AgentConfig(name='example-model',eval_mode='gui'),SPEC)
            self.assertEqual(a.call_llm({'model':'kimi-k3','messages':[]}), 'ACTION')
            self.assertTrue(call.call_args.kwargs['retry_empty_response'])
            self.assertFalse(call.call_args.kwargs['retry_reasoning_only_response'])
            self.assertEqual(call.call_args.kwargs['retries'],3)
            self.assertEqual(call.call_args.kwargs['timeout_seconds'],600)

    def test_failed_prediction_preserves_all_attempt_records(self):
        root=Path(transport.__file__).resolve().parents[3]
        tree=ast.parse((root/'engine/lib_run_single.py').read_text(encoding='utf-8'))
        names={'_predict_and_record_llm_attempts','_flush_llm_attempts'}
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        self.assertEqual(len(nodes),2)
        ns={'os':os,'json':json};exec(compile(ast.Module(body=nodes,type_ignores=[]),'attempt-flush','exec'),ns)
        class FailedAgent:
            _llm_attempts=[{'status':'reasoning_only','retry_policy':'empty-response-identical-request-v1'}]*3
            def predict(self,*args):raise RuntimeError('API attempts exhausted')
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError,'API attempts exhausted'):
                ns['_predict_and_record_llm_attempts'](FailedAgent(),'instruction',{},folder,7)
            rows=[json.loads(line) for line in (Path(folder)/'llm_calls.jsonl').read_text().splitlines()]
            self.assertEqual([r['step_num'] for r in rows],[7,7,7])
            self.assertEqual([r['attempt_idx'] for r in rows],[1,2,3])
            self.assertEqual([r['is_final'] for r in rows],[False,False,True])

if __name__=='__main__':unittest.main()
