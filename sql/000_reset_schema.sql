-- ========================================
-- Script para recriar todas as tabelas
-- Execute com: docker compose exec postgres psql -U coral_user -d coral_db -f /docker-entrypoint-initdb.d/reset_schema.sql
-- ========================================

-- Drop all tables
DROP TABLE IF EXISTS pl_interactions CASCADE;
DROP TABLE IF EXISTS legislative_items CASCADE;
DROP TABLE IF EXISTS demand_supporters CASCADE;
DROP TABLE IF EXISTS demands CASCADE;
DROP TABLE IF EXISTS interactions CASCADE;
DROP TABLE IF EXISTS conversation_states CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Recriar executando os scripts na ordem
-- (Os scripts serão executados automaticamente se você usar rebuild-db.ps1)
