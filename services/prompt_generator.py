"""
Service layer for music prompt generation using OpenAI Agents.
"""

import logging
import os
from pathlib import Path
from typing import Optional

# Ensure environment variables are loaded before importing agents
from dotenv import load_dotenv
load_dotenv()

from agents import Agent, Runner
from pydantic import BaseModel

from models.prompt import (
    ProjectBlueprint,
    SoundProfile,
    DeliveryAndControl,
    PromptGenerationRequest,
)


logger = logging.getLogger(__name__)


class PromptGeneratorService:
    """
    Service for generating music prompts using OpenAI Agents.
    
    This service loads the system prompt instructions and uses them to generate
    high-quality music prompts based on the user's three-choice wizard selections.
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
                / "system_prompt_eleven_music_3choice_wizard_prompt_architect_NEW.md"
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
                name="prompt_generator_agent",
                instructions=self.instructions,
                output_type=str,  # Agent outputs a markdown prompt (string)
            )
            logger.info("Created OpenAI Agent for prompt generation")
        
        return self._agent
    
    async def generate_prompt(
        self,
        request: PromptGenerationRequest,
    ) -> str:
        """
        Generate a music prompt based on the wizard selections.
        
        Args:
            request: The validated prompt generation request containing
                    project_blueprint, sound_profile, delivery_and_control,
                    and instrumental_only settings.
        
        Returns:
            The generated music prompt as a markdown string.
        
        Raises:
            RuntimeError: If prompt generation fails.
        """
        try:
            # Convert the request to JSON format that the agent can parse
            user_message = request.model_dump_json(indent=2)
            
            logger.info(
                f"Generating prompt for: "
                f"blueprint={request.project_blueprint.value}, "
                f"profile={request.sound_profile.value}, "
                f"control={request.delivery_and_control.value}, "
                f"instrumental={request.instrumental_only}"
            )
            
            # Run the agent to generate the prompt
            result = await Runner.run(
                self.agent,
                user_message,
            )
            
            generated_prompt = result.final_output
            
            if not generated_prompt or not isinstance(generated_prompt, str):
                raise RuntimeError("Agent returned invalid output")
            
            logger.info(f"Successfully generated prompt ({len(generated_prompt)} chars)")
            
            return generated_prompt
            
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
