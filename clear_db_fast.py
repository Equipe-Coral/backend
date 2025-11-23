"""
Script rápido para limpar o banco - SEM confirmação
USO: python clear_db_fast.py
"""

from src.core.database import SessionLocal
from src.models.interaction import Interaction
from src.models.user import User
from src.models.conversation_state import ConversationState

db = SessionLocal()

try:
    # Delete all data
    interactions = db.query(Interaction).delete()
    states = db.query(ConversationState).delete()
    users = db.query(User).delete()
    
    db.commit()
    
    print(f"✅ Banco limpo!")
    print(f"   - {interactions} interações")
    print(f"   - {states} estados")
    print(f"   - {users} usuários")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    db.rollback()
finally:
    db.close()
