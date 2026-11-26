"""Regression tests for waiting on registry parser replies."""

import unittest
from unittest.mock import AsyncMock, Mock

from app import consumer as consumer_module
from app.consumer import AIConsumer


class RegistryTimeoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_wait_timeout_exceeds_parser_ttl_and_keeps_reply_queue_alive(self) -> None:
        consumer = AIConsumer()
        consumer.channel = Mock()
        reply_queue = Mock()
        reply_queue.consume = AsyncMock()
        consumer.channel.declare_queue = AsyncMock(return_value=reply_queue)
        consumer.channel.default_exchange.publish = AsyncMock()
        consumer.redis = Mock()
        consumer.redis.setex = AsyncMock()
        consumer.redis.get = AsyncMock(return_value=None)

        event = {"correlation_id": "registry-timeout-test", "data_for_analytics": {}}
        await consumer._suspend(event)

        parser_ttl = 300
        grace_seconds = consumer_module.settings.registry_wait_timeout_seconds - parser_ttl
        self.assertGreaterEqual(grace_seconds, 120)

        reply_queue_name = consumer.channel.declare_queue.await_args_list[0].args[0]
        reply_queue_options = consumer.channel.declare_queue.await_args_list[0].kwargs
        self.assertEqual(reply_queue_name, "ai.reply.registry-timeout-test")
        self.assertEqual(
            reply_queue_options["arguments"]["x-expires"],
            (consumer_module.settings.registry_wait_timeout_seconds + 300) * 1000,
        )
        self.assertEqual(
            consumer.redis.setex.await_args.args[1],
            consumer_module.settings.registry_wait_timeout_seconds + 300,
        )
        self.assertEqual(
            consumer.channel.declare_queue.await_args_list[1].kwargs["arguments"]["x-message-ttl"],
            consumer_module.settings.registry_wait_timeout_seconds * 1000,
        )


if __name__ == "__main__":
    unittest.main()