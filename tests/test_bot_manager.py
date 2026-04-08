"""Tests for BotManagerAgent."""

from __future__ import annotations

import pytest

from src.autonomous.bot_manager import (
    BotConfig,
    BotManagerAgent,
    BotMessage,
    BotPlatform,
    BotStatus,
)


@pytest.fixture()
def agent() -> BotManagerAgent:
    return BotManagerAgent(api_key="", provider="openai", model="gpt-4o")


class TestBotManagerAgent:
    def test_default_bots_loaded(self, agent: BotManagerAgent) -> None:
        bots = agent.list_bots()
        assert len(bots) == len(BotManagerAgent.DEFAULT_BOTS)

    def test_default_bots_have_correct_ids(self, agent: BotManagerAgent) -> None:
        bot_ids = {b.bot_id for b in agent.list_bots()}
        assert "allbots-main" in bot_ids
        assert "chatlippytm-main" in bot_ids
        assert "tower-control" in bot_ids

    def test_register_bot(self, agent: BotManagerAgent) -> None:
        bot = agent.register_bot(
            bot_id="test-bot",
            name="Test Bot",
            platform=BotPlatform.DISCORD,
            repo_name="TestRepo",
            description="A test bot",
            capabilities=["testing"],
        )
        assert isinstance(bot, BotConfig)
        assert bot.bot_id == "test-bot"
        assert bot.platform == BotPlatform.DISCORD

    def test_activate_bot(self, agent: BotManagerAgent) -> None:
        assert agent.activate_bot("allbots-main")
        assert agent._bots["allbots-main"].status == BotStatus.ACTIVE

    def test_activate_unknown_bot_returns_false(self, agent: BotManagerAgent) -> None:
        assert not agent.activate_bot("does-not-exist")

    def test_stop_bot(self, agent: BotManagerAgent) -> None:
        agent.activate_bot("allbots-main")
        assert agent.stop_bot("allbots-main")
        assert agent._bots["allbots-main"].status == BotStatus.STOPPED

    def test_get_bot_returns_config(self, agent: BotManagerAgent) -> None:
        bot = agent.get_bot("allbots-main")
        assert bot is not None
        assert bot.bot_id == "allbots-main"

    def test_get_bot_unknown_returns_none(self, agent: BotManagerAgent) -> None:
        assert agent.get_bot("unknown") is None

    def test_list_bots_filtered_by_platform(self, agent: BotManagerAgent) -> None:
        manychat_bots = agent.list_bots(platform=BotPlatform.MANYCHAT)
        assert all(b.platform == BotPlatform.MANYCHAT for b in manychat_bots)

    def test_process_message_returns_message(self, agent: BotManagerAgent) -> None:
        msg = agent.process_message("allbots-main", "Hello!")
        assert isinstance(msg, BotMessage)
        assert msg.bot_id == "allbots-main"
        assert msg.user_input == "Hello!"
        assert len(msg.bot_response) > 0

    def test_process_message_unknown_bot_raises(self, agent: BotManagerAgent) -> None:
        with pytest.raises(ValueError, match="not found"):
            agent.process_message("unknown-bot", "Hello!")

    def test_process_message_increments_count(self, agent: BotManagerAgent) -> None:
        initial_count = agent._bots["allbots-main"].message_count
        agent.process_message("allbots-main", "Test")
        assert agent._bots["allbots-main"].message_count == initial_count + 1

    def test_get_fleet_status_structure(self, agent: BotManagerAgent) -> None:
        status = agent.get_fleet_status()
        assert "total_bots" in status
        assert "status_breakdown" in status
        assert "total_messages_processed" in status
        assert "bots" in status
        assert status["total_bots"] == len(BotManagerAgent.DEFAULT_BOTS)

    def test_get_message_log_empty_initially(self, agent: BotManagerAgent) -> None:
        log = agent.get_message_log()
        assert isinstance(log, list)

    def test_get_message_log_after_messages(self, agent: BotManagerAgent) -> None:
        agent.process_message("allbots-main", "Msg 1")
        agent.process_message("tower-control", "Msg 2")
        log = agent.get_message_log()
        assert len(log) == 2

    def test_get_message_log_filtered_by_bot(self, agent: BotManagerAgent) -> None:
        agent.process_message("allbots-main", "Msg 1")
        agent.process_message("tower-control", "Msg 2")
        log = agent.get_message_log(bot_id="allbots-main")
        assert all(m.bot_id == "allbots-main" for m in log)

    def test_placeholder_response_contains_bot_name(self, agent: BotManagerAgent) -> None:
        bot = agent.get_bot("allbots-main")
        assert bot is not None
        response = agent._placeholder_response(bot, "Hello")
        assert "AllBots Central Manager" in response
