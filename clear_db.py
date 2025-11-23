"""
Script para limpar todas as tabelas do banco de dados.
CUIDADO: Isso apaga TODOS os dados!
"""

import sys
from src.core.database import SessionLocal, engine
from src.models.interaction import Interaction
from src.models.user import User
from src.models.conversation_state import ConversationState
from sqlalchemy import text

def clear_database():
    """Limpa todas as tabelas do banco de dados"""
    
    print("⚠️  ATENÇÃO: Isso vai APAGAR TODOS OS DADOS do banco!")
    print("\nTabelas que serão limpas:")
    print("  - interactions")
    print("  - conversation_states")
    print("  - users")
    
    confirm = input("\nTem certeza? Digite 'SIM' para confirmar: ")
    
    if confirm != "SIM":
        print("❌ Operação cancelada.")
        return
    
    db = SessionLocal()
    
    try:
        print("\n🗑️  Limpando banco de dados...")
        
        # Delete in order (respecting foreign keys)
        # 1. Delete interactions first (has FK to users)
        interactions_count = db.query(Interaction).count()
        db.query(Interaction).delete()
        print(f"  ✅ Deletadas {interactions_count} interações")
        
        # 2. Delete conversation states
        states_count = db.query(ConversationState).count()
        db.query(ConversationState).delete()
        print(f"  ✅ Deletados {states_count} estados de conversa")
        
        # 3. Delete users
        users_count = db.query(User).count()
        db.query(User).delete()
        print(f"  ✅ Deletados {users_count} usuários")
        
        # Commit changes
        db.commit()
        
        print("\n✅ Banco de dados limpo com sucesso!")
        print("\n📊 Resumo:")
        print(f"  - {interactions_count} interações removidas")
        print(f"  - {states_count} estados removidos")
        print(f"  - {users_count} usuários removidos")
        
    except Exception as e:
        print(f"\n❌ Erro ao limpar banco: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

def reset_sequences():
    """Reseta as sequences do PostgreSQL (opcional)"""
    db = SessionLocal()
    try:
        print("\n🔄 Resetando sequences...")
        # PostgreSQL auto-increment sequences (se houver)
        # Como usamos UUID, não há sequences para resetar
        print("  ℹ️  Usando UUIDs, não há sequences para resetar")
        db.commit()
    except Exception as e:
        print(f"  ⚠️  Aviso ao resetar sequences: {e}")
    finally:
        db.close()

def show_stats():
    """Mostra estatísticas do banco"""
    db = SessionLocal()
    try:
        print("\n📊 Estatísticas do banco:")
        print(f"  - Usuários: {db.query(User).count()}")
        print(f"  - Interações: {db.query(Interaction).count()}")
        print(f"  - Estados de conversa: {db.query(ConversationState).count()}")
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🧹 CORAL BOT - Limpeza de Banco de Dados")
    print("=" * 60)
    
    # Show current stats
    show_stats()
    
    # Clear database
    clear_database()
    
    # Show stats after clearing
    show_stats()
    
    print("\n" + "=" * 60)
    print("✅ Processo concluído!")
    print("=" * 60)
