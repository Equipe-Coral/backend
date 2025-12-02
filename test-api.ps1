# Test Authentication API - Coral Backend
# PowerShell script to test authentication endpoints

$baseUrl = "http://localhost:8000"

Write-Host "=== Testing Coral Authentication API ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check
Write-Host "1. Testing Health Check..." -ForegroundColor Yellow
$response = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
Write-Host "Response: $($response | ConvertTo-Json)" -ForegroundColor Green
Write-Host ""

# Test 2: Register
Write-Host "2. Testing Registration..." -ForegroundColor Yellow
$registerData = @{
    name = "Teste Usuario"
    email = "teste@example.com"
    phone = "11999999999"
    cpf = "12345678900"
    password = "senha123"
    uf = "SP"
    city = "São Paulo"
    address = "Rua Teste, 123"
    number = "123"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/auth/register" -Method Post -Body $registerData -ContentType "application/json"
    Write-Host "Response: $($response | ConvertTo-Json)" -ForegroundColor Green
    $email = $response.email
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 3: Verify Code (will fail without real code)
Write-Host "3. Testing Code Verification (will fail without real code)..." -ForegroundColor Yellow
Write-Host "Enter the 6-digit code sent to WhatsApp (or press Enter to skip):" -ForegroundColor Cyan
$code = Read-Host

if ($code) {
    $verifyData = @{
        email = "teste@example.com"
        code = $code
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/api/auth/verify" -Method Post -Body $verifyData -ContentType "application/json"
        Write-Host "Response: $($response | ConvertTo-Json)" -ForegroundColor Green
        $token = $response.token
        
        # Test 4: Get Profile
        Write-Host ""
        Write-Host "4. Testing Get Profile..." -ForegroundColor Yellow
        $headers = @{
            Authorization = "Bearer $token"
        }
        $response = Invoke-RestMethod -Uri "$baseUrl/api/user/profile" -Method Get -Headers $headers
        Write-Host "Response: $($response | ConvertTo-Json)" -ForegroundColor Green
        
        # Test 5: Update Profile
        Write-Host ""
        Write-Host "5. Testing Update Profile..." -ForegroundColor Yellow
        $updateData = @{
            name = "Teste Usuario Atualizado"
            address = "Rua Nova, 456"
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$baseUrl/api/user/profile" -Method Put -Body $updateData -Headers $headers -ContentType "application/json"
        Write-Host "Response: $($response | ConvertTo-Json)" -ForegroundColor Green
        
    } catch {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "Skipping verification tests..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Testing WhatsApp Bot API ===" -ForegroundColor Cyan
Write-Host ""

# Test WhatsApp Bot Status
Write-Host "6. Testing WhatsApp Bot Status..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:3000/status" -Method Get
    Write-Host "Response: $($response | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Error: WhatsApp Bot is not running or not accessible" -ForegroundColor Red
    Write-Host "Make sure to start the bot with: cd whatsapp-bot; npm start" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Tests Complete ===" -ForegroundColor Cyan
