# ========================================
# Script Interativo de Gerenciamento do Banco
# ========================================

param(
    [Parameter(Position=0)]
    [ValidateSet('full', 'data', 'help')]
    [string]$Action = 'help'
)

function Show-Help {
    Write-Host @"

🗄️  Gerenciamento do Banco de Dados Coral
==========================================

Uso: .\db.ps1 [opção]

Opções:
  full    - Reconstrução completa (destrói volume e recria do zero)
  data    - Limpa apenas os dados (mantém estrutura das tabelas)
  help    - Mostra esta ajuda

Exemplos:
  .\db.ps1 full    # Recria o banco completamente
  .\db.ps1 data    # Limpa os dados mas mantém tabelas

"@ -ForegroundColor Cyan
}

function Reset-Full {
    Write-Host "`nRECONSTRUÇÃO COMPLETA DO BANCO" -ForegroundColor Yellow
    Write-Host "   Isso vai DESTRUIR todos os dados!" -ForegroundColor Red
    
    $confirm = Read-Host "   Confirma? (S/N)"
    if ($confirm -ne 'S' -and $confirm -ne 's') {
        Write-Host "   ❌ Cancelado" -ForegroundColor Red
        return
    }

    Write-Host "`nParando containers..." -ForegroundColor Yellow
    docker compose --profile backend down

    Write-Host "Removendo volume..." -ForegroundColor Yellow
    docker volume rm backend_postgres_data -f

    Write-Host "Recriando..." -ForegroundColor Green
    docker compose --profile backend up -d

    Write-Host "`nReconstrução completa finalizada!" -ForegroundColor Green
}

function Reset-Data {
    Write-Host "`nLIMPEZA DE DADOS" -ForegroundColor Yellow
    Write-Host "   Isso vai limpar todos os dados mas manter a estrutura" -ForegroundColor Yellow
    
    $confirm = Read-Host "   Confirma? (S/N)"
    if ($confirm -ne 'S' -and $confirm -ne 's') {
        Write-Host "   ❌ Cancelado" -ForegroundColor Red
        return
    }

    Write-Host "`nLimpando dados..." -ForegroundColor Yellow
    $sql = @"
TRUNCATE TABLE
    conversation_states,
    interactions,
    demands,
    demand_supporters,
    legislative_items,
    pl_interactions,
    users
CASCADE;
"@
    docker compose exec postgres psql -U coral_user -d coral_db -c "$sql"

    Write-Host "`nDados limpos!" -ForegroundColor Green
}

# Executar ação
switch ($Action) {
    'full' { Reset-Full }
    'data' { Reset-Data }
    'help' { Show-Help }
    default { Show-Help }
}
