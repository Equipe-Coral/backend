"""
Test script for Step 2: Onboarding Flow

This script tests the ProfilerAgent and ConversationStateManager
without needing to send actual WhatsApp messages.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import SessionLocal
from src.agents.profiler import ProfilerAgent
from src.core.state_manager import ConversationStateManager
from src.models.user import User
from src.models.conversation_state import ConversationState

async def test_location_extraction():
    """Test location extraction from various text inputs"""
    profiler = ProfilerAgent()
    
    test_cases = [
        "Moro em Pinheiros, São Paulo",
        "Sou de Copacabana, Rio de Janeiro",
        "Bairro Savassi, BH",
        "Estou em casa",  # Should fail
        "São Paulo",
        "Centro de Fortaleza, CE"
    ]
    
    print("=" * 60)
    print("Testing Location Extraction")
    print("=" * 60)
    
    for text in test_cases:
        print(f"\nInput: '{text}'")
        result = await profiler.extract_location_from_text(text)
        print(f"Result: {result}")
        print(f"Valid: {result.get('has_location') and result.get('confidence', 0) >= 0.6}")

async def test_geocoding():
    """Test geocoding of Brazilian locations"""
    profiler = ProfilerAgent()
    
    locations = [
        "Pinheiros, São Paulo, SP",
        "Avenida Paulista, São Paulo",
        "Copacabana, Rio de Janeiro, RJ",
    ]
    
    print("\n" + "=" * 60)
    print("Testing Geocoding")
    print("=" * 60)
    
    for location in locations:
        print(f"\nLocation: '{location}'")
        result = await profiler.geocode_location(location)
        print(f"Coordinates: {result.get('coordinates')}")
        print(f"Address: {result.get('formatted_address')}")

def test_state_manager():
    """Test conversation state manager"""
    db = SessionLocal()
    state_manager = ConversationStateManager()
    
    test_phone = "+5511999999999"
    
    print("\n" + "=" * 60)
    print("Testing State Manager")
    print("=" * 60)
    
    try:
        # Test set state
        print("\n1. Setting state to 'awaiting_location'")
        state = state_manager.set_state(
            test_phone, 
            'awaiting_location',
            {'test': 'data'},
            db
        )
        print(f"   State created: {state.current_stage}")
        
        # Test get state
        print("\n2. Getting state")
        state = state_manager.get_state(test_phone, db)
        print(f"   Current stage: {state.current_stage}")
        print(f"   Context: {state.context_data}")
        
        # Test update context
        print("\n3. Updating context")
        state_manager.update_context(
            test_phone,
            {'new_field': 'new_value'},
            db
        )
        state = state_manager.get_state(test_phone, db)
        print(f"   Updated context: {state.context_data}")
        
        # Test clear state
        print("\n4. Clearing state")
        cleared = state_manager.clear_state(test_phone, db)
        print(f"   Cleared: {cleared}")
        
        state = state_manager.get_state(test_phone, db)
        print(f"   State after clear: {state}")
        
    finally:
        db.close()

async def test_user_creation():
    """Test user creation with location"""
    db = SessionLocal()
    profiler = ProfilerAgent()
    
    test_phone = "+5511988888888"
    
    print("\n" + "=" * 60)
    print("Testing User Creation")
    print("=" * 60)
    
    try:
        # Check if user exists
        print("\n1. Checking if user exists")
        user = await profiler.check_user_exists(test_phone, db)
        print(f"   User exists: {user is not None}")
        
        if user:
            print(f"   User ID: {user.id}")
            print(f"   Status: {user.status}")
            print(f"   Location: {user.location_primary}")
        else:
            # Create user
            print("\n2. Creating user")
            location_data = {
                'neighborhood': 'Pinheiros',
                'city': 'São Paulo',
                'state': 'SP',
                'coordinates': [-23.5613, -46.6917],
                'formatted_address': 'Pinheiros, São Paulo - SP, Brasil'
            }
            
            user = await profiler.create_user(test_phone, location_data, db)
            print(f"   User created: {user.id}")
            print(f"   Status: {user.status}")
            print(f"   Location: {user.location_primary}")
            
            # Generate civic ID
            civic_id = profiler.generate_civic_id_hash(test_phone)
            print(f"   Civic ID: {civic_id[:16]}...")
            
    except Exception as e:
        print(f"   Error: {e}")
    finally:
        db.close()

async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("STEP 2: Onboarding Tests")
    print("=" * 60)
    
    try:
        # Test 1: Location Extraction
        await test_location_extraction()
        
        # Test 2: Geocoding
        await test_geocoding()
        
        # Test 3: State Manager
        test_state_manager()
        
        # Test 4: User Creation
        await test_user_creation()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during tests: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
