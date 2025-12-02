"""
Script para executar migrations SQL sem precisar do psql
Executa todas as migrations em ordem
"""
import psycopg2
from dotenv import load_dotenv
import os
from pathlib import Path

# Carregar variáveis de ambiente
load_dotenv()

# Lista de migrations em ordem de execução
MIGRATIONS = [
    'sql/000_reset_schema.sql',
    'sql/002_create_users.sql',
    'sql/003_create_conversation_states.sql',
    'sql/003_create_interactions.sql',
    'sql/004_alter_interactions_add_user_id.sql',
    'sql/004_create_demands.sql',
    'sql/005_add_pgvector.sql',
    'sql/006_create_legislative_items.sql',
    'sql/007_add_auth_fields.sql',
    'sql/008_add_profile_fields.sql',
]

def run_migration(migration_file, conn, cursor):
    """Executa uma migration específica"""
    
    migration_name = Path(migration_file).name
    
    # Verificar se arquivo existe
    if not os.path.exists(migration_file):
        print(f"⚠️  Arquivo {migration_file} não encontrado, pulando...")
        return True
    
    try:
        # Ler arquivo SQL
        print(f"📄 Lendo {migration_name}...")
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # Executar SQL
        print(f"⚙️  Executando {migration_name}...")
        cursor.execute(sql)
        conn.commit()
        
        print(f"✅ {migration_name} executada com sucesso!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Erro ao executar {migration_name}: {e}")
        conn.rollback()  # Fazer rollback para limpar transação abortada
        return False
    except Exception as e:
        print(f"❌ Erro inesperado em {migration_name}: {e}")
        conn.rollback()  # Fazer rollback para limpar transação abortada
        return False

def verify_migrations(cursor):
    """Verifica se as migrations foram aplicadas corretamente"""
    
    print("\n🔍 Verificando estrutura do banco...\n")
    
    # Verificar colunas de autenticação na tabela users
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name IN ('name', 'email', 'cpf', 'password_hash', 'uf', 'city', 'address', 'number', 'is_verified', 'bio', 'avatar_url', 'interests')
        ORDER BY column_name;
    """)
    
    columns = cursor.fetchall()
    print(f"📋 Colunas na tabela 'users': {len(columns)}")
    for col in columns:
        print(f"   ✓ {col[0]}")
    
    # Verificar tabela verification_codes
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'verification_codes'
        );
    """)
    
    if cursor.fetchone()[0]:
        print(f"\n✓ Tabela 'verification_codes' existe")
    
    # Verificar tabela demands
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'demands'
        );
    """)
    
    if cursor.fetchone()[0]:
        print(f"✓ Tabela 'demands' existe")
    
    # Verificar extensão pgvector
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM pg_extension 
            WHERE extname = 'vector'
        );
    """)
    
    if cursor.fetchone()[0]:
        print(f"✓ Extensão 'pgvector' instalada")

def run_all_migrations():
    """Executa todas as migrations"""
    
    # Conectar ao banco
    database_url = os.getenv('DATABASE_URL')
    print(f"🔌 Conectando ao banco: {database_url}\n")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Executar cada migration
        success_count = 0
        for migration_file in MIGRATIONS:
            if run_migration(migration_file, conn, cursor):
                success_count += 1
            print()  # Linha em branco entre migrations
        
        # Verificar estrutura
        verify_migrations(cursor)
        
        cursor.close()
        conn.close()
        
        print(f"\n📊 Resultado: {success_count}/{len(MIGRATIONS)} migrations executadas")
        return success_count == len(MIGRATIONS)
        
    except psycopg2.Error as e:
        print(f"❌ Erro de conexão ao banco: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando execução das migrations...\n")
    print("=" * 60)
    print()
    
    success = run_all_migrations()
    
    print()
    print("=" * 60)
    if success:
        print("✅ Todas as migrations foram concluídas com sucesso!")
    else:
        print("❌ Algumas migrations falharam. Verifique os erros acima.")
        exit(1)