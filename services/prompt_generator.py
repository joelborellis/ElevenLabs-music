"""
Service layer for music prompt generation using OpenAI Agents.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

# Ensure environment variables are loaded before importing agents
from dotenv import load_dotenv
load_dotenv()

from agents import Agent, Runner, WebSearchTool, ToolCallItem, ToolCallOutputItem

from models.finetune import FinetuneContext
from models.prompt import (
    PromptGenerationRequest,
    AgentPromptOutput,
)
from services.finetune_service import get_finetune_service


logger = logging.getLogger(__name__)


class PromptGeneratorService:
    """
    Service for generating music prompts using OpenAI Agents.
    
    This service loads the system prompt instructions and uses them to generate
    high-quality music prompts from the user's wizard selections (project blueprint,
    delivery & control) plus the finetune that will render the track.
    """
    
    def __init__(self, instructions_path: Optional[Path] = None):
        """
        Initialize the prompt generator service.
        
        Args:
            instructions_path: Path to the system prompt instructions file.
                             If None, uses the default path.
        """
        if instructions_path is None:
            instructions_path = (
                Path(__file__).parent.parent
                / "prompts"
                / "generate_music_prompt.md"
            )
        
        self.instructions_path = instructions_path
        self._instructions: Optional[str] = None
        self._agent: Optional[Agent] = None
        
        logger.info(f"Initialized PromptGeneratorService with instructions: {instructions_path}")
    
    @property
    def instructions(self) -> str:
        """
        Lazy load and cache the system prompt instructions.
        
        Returns:
            The system prompt instructions as a string.
        
        Raises:
            FileNotFoundError: If the instructions file doesn't exist.
            IOError: If the file cannot be read.
        """
        if self._instructions is None:
            try:
                with open(self.instructions_path, "r", encoding="utf-8") as f:
                    self._instructions = f.read()
                logger.info(f"Loaded instructions from {self.instructions_path}")
            except FileNotFoundError:
                logger.error(f"Instructions file not found: {self.instructions_path}")
                raise
            except Exception as e:
                logger.error(f"Error reading instructions file: {e}")
                raise IOError(f"Failed to read instructions file: {e}") from e
        
        return self._instructions
    
    @property
    def agent(self) -> Agent:
        """
        Lazy load and cache the OpenAI Agent.
        
        Returns:
            The configured Agent instance.
        """
        if self._agent is None:
            self._agent = Agent(
                model="gpt-5.6",
                name="prompt_generator_agent",
                instructions=self.instructions,
                tools=[WebSearchTool()],
                output_type=AgentPromptOutput,  # Agent outputs structured prompt with title and description
            )
            logger.info("Created OpenAI Agent for prompt generation with WebSearchTool")
        
        return self._agent
    
    async def _resolve_finetune_context(
        self,
        finetune_id: str,
    ) -> Optional[FinetuneContext]:
        """
        Resolve a finetune id into the genre metadata the agent derives from.

        Best-effort by design: if the finetune is gone, ElevenLabs is unreachable, or
        no ELEVENLABS_API_KEY is configured, we return None and the agent infers the
        genre from the sound_profile slug alone. /prompt must keep working without an
        ElevenLabs key, as it does today.

        Args:
            finetune_id: The finetune id from the request.

        Returns:
            A FinetuneContext, or None if the finetune could not be resolved.
        """
        try:
            service = get_finetune_service()
            # The SDK call is blocking; keep it off the event loop.
            summary = await asyncio.to_thread(service.get_finetune, finetune_id)
        except Exception as e:
            # Includes the RuntimeError raised when ELEVENLABS_API_KEY is unset.
            logger.warning(f"Finetune context unavailable for {finetune_id}: {e}")
            return None

        if summary is None:
            logger.warning(
                f"No finetune metadata for {finetune_id}; "
                f"agent will infer genre from the slug alone"
            )
            return None

        return FinetuneContext.from_summary(summary)

    async def generate_prompt(
        self,
        request: PromptGenerationRequest,
    ) -> AgentPromptOutput:
        """
        Generate a music prompt based on the wizard selections.

        Args:
            request: The validated prompt generation request containing
                    project_blueprint, sound_profile, finetune_id,
                    delivery_and_control, and instrumental_only settings.

        Returns:
            The generated AgentPromptOutput containing prompt, title, and description.

        Raises:
            RuntimeError: If prompt generation fails.
        """
        try:
            # Resolve the finetune server-side so the agent derives genre from real
            # trained-model metadata rather than from the bare slug.
            finetune_context = await self._resolve_finetune_context(request.finetune_id)

            # Build the JSON payload the agent parses. finetune_context is resolved,
            # not submitted, so it lives here rather than on the request model (which
            # is echoed back to the client as input_parameters).
            payload = request.model_dump()
            if finetune_context is not None:
                payload["finetune_context"] = finetune_context.model_dump()
            user_message = json.dumps(payload, indent=2)

            logger.info(
                f"Generating prompt for: "
                f"blueprint={request.project_blueprint.value}, "
                f"profile={request.sound_profile}, "
                f"finetune_id={request.finetune_id}, "
                f"finetune_context={'resolved' if finetune_context else 'unresolved'}, "
                f"control={request.delivery_and_control.value}, "
                f"instrumental={request.instrumental_only}, "
                f"user_narrative={'provided' if request.user_narrative else 'none'}"
            )

            # Run the agent to generate the prompt
            result = await Runner.run(
                self.agent,
                user_message,
            )

            # Log any tool calls (e.g., WebSearchTool)
            for item in result.new_items:
                if isinstance(item, ToolCallItem):
                    logger.info(f"Tool called: {item.raw_item.type if hasattr(item.raw_item, 'type') else 'unknown'}")
                    logger.info(f"Tool call details: {item.raw_item}")
                elif isinstance(item, ToolCallOutputItem):
                    output_preview = str(item.output)[:500] if item.output else "No output"
                    logger.info(f"Tool output (truncated): {output_preview}")

            generated_output = result.final_output
            
            if not generated_output or not isinstance(generated_output, AgentPromptOutput):
                raise RuntimeError("Agent returned invalid output")
            
            logger.info(f"Successfully generated prompt ({len(generated_output.prompt)} chars)")
            
            return generated_output
            
        except Exception as e:
            logger.error(f"Failed to generate prompt: {e}", exc_info=True)
            raise RuntimeError(f"Prompt generation failed: {str(e)}") from e
    
    def reload_instructions(self) -> None:
        """
        Force reload of the system prompt instructions.
        
        Useful for development when instructions are updated without restarting the app.
        """
        self._instructions = None
        self._agent = None
        logger.info("Instructions and agent cleared, will reload on next use")


# Global service instance (initialized on first use)
_service_instance: Optional[PromptGeneratorService] = None


def get_prompt_generator_service() -> PromptGeneratorService:
    """
    Get the singleton instance of the prompt generator service.
    
    Returns:
        The PromptGeneratorService instance.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = PromptGeneratorService()
    return _service_instance
