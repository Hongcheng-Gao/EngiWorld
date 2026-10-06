import copy
import os
import unittest
from unittest.mock import Mock, patch

from engiworld.agents.openai_compatible import (
    OpenAICompatibleAPIError,
    call_chat_completions,
    chat_completions_url,
    prepare_payload,
    require_api_key,
)


class OpenAICompatibleTransportTest(unittest.TestCase):
    def test_prepare_payload_strips_private_image_metadata_and_sets_effort(self):
        original = {
            "model": "model-1",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/png;base64,abc"},
                            "_step": 1,
                        }
                    ],
                }
            ],
            "temperature": None,
            "top_p": None,
        }

        prepared = prepare_payload(
            original,
            reasoning_effort="max",
            reasoning_field="reasoning_effort",
        )

        self.assertNotIn("_step", prepared["messages"][0]["content"][0])
        self.assertNotIn("temperature", prepared)
        self.assertNotIn("top_p", prepared)
        self.assertEqual(prepared["reasoning_effort"], "max")
        self.assertEqual(original["messages"][0]["content"][0]["_step"], 1)

    def test_prepare_payload_removes_assistant_reasoning_from_history(self):
        original = {
            "model": "model-1",
            "messages": [
                {
                    "role": "assistant",
                    "reasoning_content": "private chain state",
                    "reasoning": "private alternate state",
                    "content": [
                        {"type": "thinking", "text": "private part"},
                        {"type": "text", "text": "final action"},
                    ],
                }
            ],
        }

        prepared = prepare_payload(
            original,
            reasoning_effort=None,
            reasoning_field="reasoning_effort",
        )

        assistant = prepared["messages"][0]
        self.assertNotIn("reasoning_content", assistant)
        self.assertNotIn("reasoning", assistant)
        self.assertEqual(assistant["content"], [{"type": "text", "text": "final action"}])
        self.assertIn("reasoning_content", original["messages"][0])

    @patch("engiworld.agents.openai_compatible._post_json")
    def test_request_uses_bearer_key_and_v1_chat_completions(self, post: Mock):
        post.return_value = (
            200,
            '{"choices":[{"message":{"content":"API_OK"}}]}',
        )

        content = call_chat_completions(
            {"model": "model-1", "messages": []},
            base_url="http://gateway.example/v1",
            api_key="secret-value",
            provider_name="test model",
            reasoning_effort="high",
            timeout_seconds=5,
        )

        self.assertEqual(content, "API_OK")
        self.assertEqual(post.call_args.args[0], "http://gateway.example/v1/chat/completions")
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer secret-value",
        )

    @patch("engiworld.agents.openai_compatible._post_json")
    def test_gemini_guard_appends_user_turn_after_assistant(self, post: Mock):
        post.return_value = (200, '{"choices":[{"message":{"content":"API_OK"}}]}')
        original = {
            "model": "gemini-3.7-flash",
            "messages": [
                {"role": "system", "content": "rules"},
                {"role": "assistant", "content": "previous action"},
            ],
        }

        with self.assertLogs(
            "engiworld.agents.openai_compatible", level="WARNING"
        ) as logs:
            call_chat_completions(
                original,
                base_url="http://gateway.example/v1",
                api_key="secret-value",
                provider_name="Gemini",
                reasoning_effort="high",
                ensure_final_user_turn=True,
            )

        sent_messages = post.call_args.kwargs["payload"]["messages"]
        self.assertEqual([message["role"] for message in sent_messages], [
            "system", "assistant", "user",
        ])
        self.assertEqual(
            sent_messages[-1]["content"][0]["text"],
            "Continue the task based on the latest available observation.",
        )
        self.assertEqual(original["messages"][-1]["role"], "assistant")
        self.assertIn("roles=['system', 'assistant']", "\n".join(logs.output))

    @patch("engiworld.agents.openai_compatible._post_json")
    def test_gemini_guard_leaves_final_user_turn_unchanged(self, post: Mock):
        post.return_value = (200, '{"choices":[{"message":{"content":"API_OK"}}]}')
        messages = [{"role": "user", "content": "current observation"}]

        call_chat_completions(
            {"model": "gemini-3.7-flash", "messages": messages},
            base_url="https://gateway.example/v1",
            api_key="secret-value",
            provider_name="Gemini",
            reasoning_effort="high",
            ensure_final_user_turn=True,
        )

        self.assertEqual(post.call_args.kwargs["payload"]["messages"], messages)

    @patch("engiworld.agents.openai_compatible._post_json")
    def test_final_user_guard_is_disabled_for_other_specs(self, post: Mock):
        post.return_value = (200, '{"choices":[{"message":{"content":"API_OK"}}]}')

        call_chat_completions(
            {
                "model": "other-model",
                "messages": [{"role": "assistant", "content": "previous action"}],
            },
            base_url="https://gateway.example/v1",
            api_key="secret-value",
            provider_name="Other model",
            reasoning_effort=None,
        )

        self.assertEqual(
            post.call_args.kwargs["payload"]["messages"][-1]["role"],
            "assistant",
        )

    @patch("engiworld.agents.openai_compatible.time.sleep")
    @patch("engiworld.agents.openai_compatible._post_json")
    def test_gemini_retries_reasoning_only_response_for_final_action(
        self, post: Mock, sleep: Mock
    ):
        sent_payloads = []
        responses = iter(
            [
                (
                    200,
                    '{"choices":[{"finish_reason":"stop","message":'
                    '{"role":"assistant","reasoning_content":"Thinking",'
                    '"content":null}}]}',
                ),
                (200, '{"choices":[{"message":{"content":"CLICK(10, 20)"}}]}'),
            ]
        )

        def fake_post(*_args, **kwargs):
            sent_payloads.append(copy.deepcopy(kwargs["payload"]))
            return next(responses)

        post.side_effect = fake_post
        attempts = []
        original = {
            "model": "gemini-3.7-flash",
            "messages": [{"role": "user", "content": "current observation"}],
        }

        content = call_chat_completions(
            original,
            base_url="https://gateway.example/v1",
            api_key="secret-value",
            provider_name="Gemini",
            reasoning_effort="high",
            retry_reasoning_only_response=True,
            retry_empty_response=False,
            retries=3,
            attempt_log=attempts,
        )

        self.assertEqual(content, "CLICK(10, 20)")
        self.assertEqual(post.call_count, 2)
        self.assertEqual(sleep.call_count, 1)
        self.assertEqual(sent_payloads[0]["messages"], original["messages"])
        self.assertEqual(sent_payloads[1]["messages"][-1]["role"], "user")
        self.assertIn(
            "no executable final action",
            sent_payloads[1]["messages"][-1]["content"][0]["text"],
        )
        self.assertEqual([item["status"] for item in attempts], ["reasoning_only", "ok"])
        self.assertEqual(attempts[0]["raw_finish_reason"], "stop")

    @patch("engiworld.agents.openai_compatible._post_json")
    def test_empty_response_retry_can_be_explicitly_disabled(self, post: Mock):
        post.return_value = (
            200,
            '{"choices":[{"message":{"reasoning_content":"Thinking",'
            '"content":""}}]}',
        )

        with self.assertRaisesRegex(
            OpenAICompatibleAPIError, "returned an empty assistant message"
        ):
            call_chat_completions(
                {"model": "claude-opus-5", "messages": []},
                base_url="https://gateway.example/v1",
                api_key="secret-value",
                provider_name="Claude",
                reasoning_effort="max",
                retry_empty_response=False,
                retries=3,
            )

        self.assertEqual(post.call_count, 1)

    @patch("engiworld.agents.openai_compatible.time.sleep")
    @patch("engiworld.agents.openai_compatible._post_json")
    def test_gemini_reasoning_only_response_exhausts_retry_budget(
        self, post: Mock, sleep: Mock
    ):
        post.return_value = (
            200,
            '{"choices":[{"finish_reason":"stop","message":'
            '{"reasoning_content":"Thinking","content":null}}]}',
        )
        attempts = []

        with self.assertRaisesRegex(OpenAICompatibleAPIError, "after 3 attempt\\(s\\)"):
            call_chat_completions(
                {"model": "gemini-3.7-flash", "messages": []},
                base_url="https://gateway.example/v1",
                api_key="secret-value",
                provider_name="Gemini",
                reasoning_effort="high",
                retry_reasoning_only_response=True,
                retry_empty_response=False,
                retries=3,
                attempt_log=attempts,
            )

        self.assertEqual(post.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual([item["status"] for item in attempts], [
            "reasoning_only", "reasoning_only", "reasoning_only",
        ])

    def test_model_keys_are_read_from_the_requested_environment_variable(self):
        with patch.dict(os.environ, {"GEMINI37_FLASH_API_KEY": "gemini-key"}, clear=True):
            self.assertEqual(
                require_api_key("GEMINI37_FLASH_API_KEY", "Gemini"),
                "gemini-key",
            )
            with self.assertRaises(EnvironmentError):
                require_api_key("CLAUDE_OPUS5_API_KEY", "Claude")

    def test_shared_gateway_key_is_an_explicit_fallback(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "shared-key"}, clear=True):
            self.assertEqual(
                require_api_key(
                    "GEMINI37_FLASH_API_KEY",
                    "Gemini",
                    fallback_env="OPENAI_API_KEY",
                ),
                "shared-key",
            )

    def test_base_url_without_v1_is_normalized(self):
        self.assertEqual(
            chat_completions_url("http://gateway.example"),
            "http://gateway.example/v1/chat/completions",
        )


if __name__ == "__main__":
    unittest.main()
