import copy
import json
import os
import sys
import types
import unittest
from unittest.mock import patch

from engiworld.agents import openai_compatible as transport
from engiworld.scheduler.schemas import AgentConfig

SPEC = transport.OpenAICompatibleAgentSpec(
    display_name="Compatible model", default_model="example-model",
    default_base_url="https://example.invalid/v1", api_key_env="OPENAI_API_KEY",
    env_prefix="ARENA_MODEL", retry_backoff_seconds=10.0,
)


class StreamErrorRetryTest(unittest.TestCase):
    @staticmethod
    def response(content='',reasoning='partial reasoning',finish=None,error=None):
        row={'choices':[{'finish_reason':finish,'message':{'content':content,'reasoning_content':reasoning}}]}
        if error:row['stream_warnings']=[json.dumps({'error':{'type':'upstream_error','message':error}})]
        return row

    def request(self,responses,**options):
        payload={'model':'gpt-5.6-sol','max_tokens':16384,'messages':[
            {'role':'system','content':'Original protocol'},
            {'role':'user','content':[{'type':'text','text':'Original task'},
             {'type':'image_url','image_url':{'url':'data:image/png;base64,eA=='}}]},
            {'role':'assistant','content':'Previous action'},
            {'role':'user','content':'Original observation'}]}
        original=copy.deepcopy(payload);sent=[];attempts=[];items=iter(responses)
        def post(*args,**kwargs):
            sent.append(copy.deepcopy(kwargs));item=next(items)
            if isinstance(item,Exception):raise item
            if isinstance(item,tuple):return item
            return 200,json.dumps(item)
        params=dict(base_url='https://example.invalid/v1',api_key='test-only',provider_name='Sol',
                    reasoning_effort='xhigh',retry_empty_response=True,retry_stream_errors=True,
                    retry_backoff_seconds=10.0,retries=3,timeout_seconds=600,attempt_log=attempts)
        if hasattr(transport,'_post_stream_json'):params['stream']=True;method='_post_stream_json'
        else:method='_post_json'
        params.update(options)
        with patch.object(transport,method,side_effect=post),patch.object(transport.time,'sleep') as sleep,patch.object(transport.random,'uniform',return_value=0.0):
            try:result=transport.call_chat_completions(payload,**params)
            except transport.OpenAICompatibleAPIError as exc:result=exc
        self.assertEqual(payload,original)
        self.assertTrue(all(s['payload']==sent[0]['payload'] for s in sent))
        self.assertTrue(all(s['timeout']==600 for s in sent))
        self.assertEqual(sent[0]['payload']['messages'],original['messages'])
        self.assertEqual(sent[0]['payload']['max_tokens'],16384)
        self.assertEqual(sent[0]['payload']['reasoning_effort'],'xhigh')
        return result,attempts,sent,[c.args[0] for c in sleep.call_args_list]

    def test_shared_spec_enables_both_retry_paths(self):
        self.assertTrue(SPEC.retry_empty_response)
        self.assertTrue(SPEC.retry_stream_errors)
        self.assertFalse(SPEC.retry_reasoning_only_response)
        self.assertEqual(SPEC.retry_backoff_seconds,10.0)

    def test_reasoning_only_then_success_identical_payload(self):
        result,logs,sent,waits=self.request([self.response(),self.response('ACTION',finish='stop')])
        self.assertEqual(result,'ACTION');self.assertEqual(len(sent),2)
        self.assertEqual([r['status'] for r in logs],['reasoning_only','ok'])
        self.assertEqual(waits,[10.0])

    def test_whitespace_empty_and_success_share_budget(self):
        result,logs,sent,waits=self.request([self.response('  ',''),self.response(None,''),self.response('ACTION',finish='stop')])
        self.assertEqual(result,'ACTION');self.assertEqual([r['status'] for r in logs],['empty_response','empty_response','ok'])
        self.assertEqual(waits,[10.0,20.0])

    def test_explicit_stream_error_discards_partial_action(self):
        result,logs,sent,waits=self.request([self.response('PARTIAL ACTION',error='overloaded'),self.response('COMPLETE ACTION',finish='stop')])
        self.assertEqual(result,'COMPLETE ACTION');self.assertEqual(logs[0]['status'],'upstream_error')
        self.assertEqual(logs[0]['retry_policy'],'upstream-error-identical-request-v1')
        self.assertIn('overloaded',logs[0]['error']);self.assertEqual(len(sent),2)

    def test_network_error_upstream_error_empty_share_three_attempts(self):
        result,logs,sent,waits=self.request([TimeoutError('timeout'),self.response(error='overloaded'),self.response()])
        self.assertIsInstance(result,transport.OpenAICompatibleAPIError)
        self.assertIn('after 3 attempt(s)',str(result))
        self.assertEqual([r['status'] for r in logs],['exception','upstream_error','reasoning_only'])
        self.assertEqual(len(sent),3);self.assertEqual(waits,[10.0,20.0])

    def test_three_stream_errors_are_logged_and_exhausted(self):
        result,logs,sent,waits=self.request([self.response(error='not ready')]*3)
        self.assertIsInstance(result,transport.OpenAICompatibleAPIError)
        self.assertIn('not ready',str(result));self.assertEqual(len(logs),3);self.assertEqual(len(sent),3)
        self.assertEqual(waits,[10.0,20.0])

    def test_harmless_stream_warnings_do_not_trigger_retry(self):
        response=self.response('ACTION',finish='stop')
        response['stream_warnings']=['keepalive',json.dumps({'notice':'diagnostic'}),'not json']
        result,logs,sent,waits=self.request([response])
        self.assertEqual(result,'ACTION');self.assertEqual(len(sent),1);self.assertEqual(waits,[])

    def test_top_level_error_and_data_prefixed_warning(self):
        self.assertIn('broken',transport._response_upstream_error({'error':{'message':'broken'}}))
        self.assertIn('broken',transport._response_upstream_error({'stream_warnings':['data: {"error":"broken"}']}))

    def test_unsupported_image_http_400_does_not_retry(self):
        result,logs,sent,waits=self.request([(400,'Unsupported image format')])
        self.assertIsInstance(result,transport.OpenAICompatibleAPIError)
        self.assertEqual(len(sent),1);self.assertEqual(waits,[])

    def test_503_shares_same_backoff_and_budget(self):
        result,logs,sent,waits=self.request([(503,'temporarily unavailable'),self.response(),self.response('ACTION',finish='stop')])
        self.assertEqual(result,'ACTION');self.assertEqual(len(sent),3)
        self.assertEqual(waits,[10.0,20.0])

    def test_default_backoff_stays_legacy(self):
        with patch.object(transport.time,'sleep') as sleep:
            transport._sleep_before_retry(1,0.0,[])
            transport._sleep_before_retry(2,0.0,[])
            transport._sleep_before_retry(20,0.0,[])
        self.assertEqual([c.args[0] for c in sleep.call_args_list],[1.5,3.0,15.0])

    def test_jitter_is_bounded_and_recorded(self):
        records=[{}]
        with patch.object(transport.time,'sleep') as sleep,patch.object(transport.random,'uniform',return_value=4.0) as jitter:
            transport._sleep_before_retry(2,10.0,records)
        jitter.assert_called_once_with(0.0,5.0);sleep.assert_called_once_with(24.0)
        self.assertEqual(records[0]['retry_wait_seconds'],24.0)

    def test_sse_decoder_preserves_actual_error_for_retry(self):
        if not hasattr(transport,'_decode_sse_response'):self.skipTest('Streaming decoder is in newer deployed source')
        stream=[b'data: {"choices":[{"delta":{"reasoning_content":"thinking"}}]}\n',
                b'data: {"error":{"type":"upstream_error","message":"overloaded"}}\n',b'data: [DONE]\n']
        response=json.loads(transport._decode_sse_response(stream))
        self.assertIn('overloaded',transport._response_upstream_error(response))
        result,logs,sent,waits=self.request([response,self.response('ACTION',finish='stop')])
        self.assertEqual(result,'ACTION');self.assertEqual(logs[0]['status'],'upstream_error')

    def test_factory_passes_configured_policy_without_changing_parameters(self):
        package=types.ModuleType('mm_agents');package.__path__=[]
        agent=types.ModuleType('mm_agents.agent');errors=types.ModuleType('mm_agents.errors')
        class FakeAgent:
            def __init__(self,**kwargs):self.settings=kwargs
        class FakeAPIError(RuntimeError):
            def __init__(self,message,**kwargs):super().__init__(message)
        agent.PromptAgent=FakeAgent;errors.ModelAPIError=FakeAPIError
        env={'OPENAI_API_KEY':'test-only','ARENA_MODEL_API_RETRIES':'3','ARENA_MODEL_TIMEOUT_SECONDS':'600',
             'ARENA_MODEL_MAX_TOKENS':'16384','ARENA_MODEL_HISTORY_N':'15','ARENA_OPENAI_COMPAT_HOTSWAP_ENABLED':'false'}
        with patch.dict(sys.modules,{'mm_agents':package,'mm_agents.agent':agent,'mm_agents.errors':errors}),patch.dict(os.environ,env,clear=True),patch.object(transport,'call_chat_completions',return_value='ACTION') as call:
            a=transport.create_prompt_agent(AgentConfig(name='gpt-5.6-sol',eval_mode='gui',history_turns=15),SPEC)
            self.assertEqual(a.call_llm({'model':'gpt-5.6-sol','messages':[]}), 'ACTION')
            self.assertTrue(call.call_args.kwargs['retry_empty_response']);self.assertTrue(call.call_args.kwargs['retry_stream_errors'])
            self.assertEqual(call.call_args.kwargs['retry_backoff_seconds'],10.0)
            self.assertEqual(call.call_args.kwargs['retries'],3);self.assertEqual(call.call_args.kwargs['timeout_seconds'],600)
            self.assertEqual(a.settings['max_tokens'],16384);self.assertEqual(a.settings['max_trajectory_length'],15)

if __name__=='__main__':unittest.main()
