from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: str
    display_name: str
    context_window: int | None = None


class ModelProvider(BaseModel):
    id: str
    display_name: str
    auth_status: str = "unknown"
    models: list[ModelInfo]


class ModelChoice(BaseModel):
    provider: str
    model: str
    reasoning_effort: str | None = None
    temperature: float | None = None


class ModelRegistry:
    def __init__(self, providers: list[ModelProvider]):
        self._providers = {provider.id: provider for provider in providers}

    @classmethod
    def with_defaults(cls) -> "ModelRegistry":
        return cls(
            providers=[
                ModelProvider(
                    id="openai",
                    display_name="OpenAI",
                    models=[
                        ModelInfo(id="gpt-5.4", display_name="GPT-5.4"),
                        ModelInfo(id="gpt-5.4-mini", display_name="GPT-5.4 Mini"),
                    ],
                ),
                ModelProvider(
                    id="anthropic",
                    display_name="Anthropic",
                    models=[ModelInfo(id="claude-sonnet-4.5", display_name="Claude Sonnet 4.5")],
                ),
                ModelProvider(
                    id="local",
                    display_name="Local",
                    models=[ModelInfo(id="custom-local", display_name="Custom Local Model")],
                ),
            ]
        )

    def list_providers(self) -> list[ModelProvider]:
        return list(self._providers.values())

    def list_models(self, provider_id: str) -> list[ModelInfo]:
        if provider_id not in self._providers:
            raise ValueError(f"Unknown provider: {provider_id}")
        return self._providers[provider_id].models

    def validate_choice(self, choice: ModelChoice) -> ModelChoice:
        models = self.list_models(choice.provider)
        if choice.model not in {model.id for model in models}:
            raise ValueError(f"Unknown model for {choice.provider}: {choice.model}")
        return choice

    def resolve_choice(
        self,
        default_choice: ModelChoice,
        session_override: ModelChoice | None = None,
    ) -> ModelChoice:
        choice = session_override or default_choice
        return self.validate_choice(choice)
