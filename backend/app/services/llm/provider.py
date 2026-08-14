"""
LLM provider abstraction.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """
    Interface implemented by concrete LLM providers.
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Generate an LLM response.
        """
        raise NotImplementedError

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ):
        """
        Streaming interface.

        Concrete providers can override this.
        """

        response = await self.generate(
            system_prompt,
            user_prompt,
        )

        yield response


class LocalLLMProvider(LLMProvider):
    """
    Very small deterministic fallback for local environment tests when no
    remote LLM is configured. It synthesizes a grounded answer from the
    provided context instead of failing the endpoint.
    """

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        prompt = user_prompt.strip()
        if not prompt:
            return "No question was provided."

        if "Repository context:" in prompt:
            context = prompt.split("Repository context:", 1)[1].strip()
            if context:
                lines = [line.strip() for line in context.splitlines() if line.strip()]
                preview = "\n".join(lines[:12])
                return (
                    "Based on the available repository context, the most relevant evidence "
                    f"appears to be in the following snippets:\n\n{preview}\n\n"
                    "This is a local fallback response generated from indexed code context. "
                    "For production answers, connect a real LLM provider."
                )

        return (
            "I could not find enough repository context to answer with confidence. "
            "Please verify the repository has been ingested and search results are available."
        )