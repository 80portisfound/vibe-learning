from hermes_vibe_api.models.providers import ModelChoice, ModelRegistry


def test_registry_lists_default_providers_and_models():
    registry = ModelRegistry.with_defaults()

    providers = registry.list_providers()

    assert [provider.id for provider in providers] == ["openai", "kimi-coding", "anthropic", "local"]
    assert registry.list_models("openai")[0].id == "gpt-5.4"
    assert registry.list_models("kimi-coding")[0].id == "kimi-k2.6"


def test_session_override_replaces_agent_default_model():
    registry = ModelRegistry.with_defaults()
    default = ModelChoice(provider="openai", model="gpt-5.4")
    override = ModelChoice(provider="anthropic", model="claude-sonnet-4.5")

    selected = registry.resolve_choice(default_choice=default, session_override=override)

    assert selected == override


def test_unknown_model_is_rejected():
    registry = ModelRegistry.with_defaults()

    try:
        registry.validate_choice(ModelChoice(provider="openai", model="missing-model"))
    except ValueError as exc:
        assert "Unknown model" in str(exc)
    else:
        raise AssertionError("Unknown model should be rejected")
