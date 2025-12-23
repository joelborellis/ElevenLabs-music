"""
Direct service test - tests the prompt generator service without HTTP.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.prompt import (
    PromptGenerationRequest,
    ProjectBlueprint,
    SoundProfile,
    DeliveryAndControl
)
from services.prompt_generator import get_prompt_generator_service


async def test_service_directly():
    """Test the prompt generator service directly without HTTP."""
    
    print("=" * 80)
    print("Direct Service Test")
    print("=" * 80)
    
    # Create a test request
    request = PromptGenerationRequest(
        project_blueprint=ProjectBlueprint.AD_BRAND_FAST_HOOK,
        sound_profile=SoundProfile.BRIGHT_POP_ELECTRO,
        delivery_and_control=DeliveryAndControl.BALANCED_STUDIO,
        instrumental_only=False
    )
    
    print("\nTest Request:")
    print(f"  Project: {request.project_blueprint.value}")
    print(f"  Sound: {request.sound_profile.value}")
    print(f"  Delivery: {request.delivery_and_control.value}")
    print(f"  Instrumental: {request.instrumental_only}")
    
    print("\n" + "=" * 80)
    print("Generating prompt...")
    print("=" * 80)
    
    try:
        # Get service and generate prompt
        service = get_prompt_generator_service()
        prompt = await service.generate_prompt(request)
        
        print("\n✓ SUCCESS! Generated prompt:")
        print("=" * 80)
        print(prompt)
        print("=" * 80)
        print(f"\nPrompt length: {len(prompt)} characters")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_service_directly())
    sys.exit(0 if result else 1)
