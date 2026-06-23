# UTF-8 Encoding
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "        Kahoot 互動遊戲 GitHub 上傳助手" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. 檢查是否安裝 Git
$gitCheck = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCheck) {
    Write-Host "[提示] 偵測到系統尚未安裝 Git！" -ForegroundColor Yellow
    Write-Host "正在嘗試透過 Windows 套件管理工具 (winget) 安裝 Git..." -ForegroundColor Yellow
    
    try {
        Start-Process winget -ArgumentList "install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements" -NoNewWindow -Wait
        Write-Host "[成功] Git 安裝完成！請重新開啟本視窗再次執行此指令檔。" -ForegroundColor Green
        Read-Host "按 Enter 鍵結束..."
        exit
    } catch {
        Write-Host "[錯誤] 自動安裝 Git 失敗，請手動至 https://git-scm.com/ 下載安裝。" -ForegroundColor Red
        Read-Host "按 Enter 鍵結束..."
        exit
    }
}

# 2. 初始化 Git 儲存庫
if (-not (Test-Path .git)) {
    Write-Host "正在初始化本機 Git 儲存庫..." -ForegroundColor Green
    git init
    git branch -M main
}

# 3. 提交檔案
Write-Host "正在加入檔案至 Git 暫存區..." -ForegroundColor Green
git add .
Write-Host "正在建立本機提交 (Commit)..." -ForegroundColor Green
git commit -m "Initial commit for deployment"

# 4. 詢問 GitHub 網址
Write-Host ""
Write-Host "---------------------------------------------" -ForegroundColor Yellow
Write-Host "請至 GitHub (github.com) 登入並建立一個新的儲存庫。" -ForegroundColor Yellow
Write-Host "然後複製儲存庫的 HTTPS 網址（例如：https://github.com/您的帳號/專案名稱.git）" -ForegroundColor Yellow
Write-Host "---------------------------------------------" -ForegroundColor Yellow
$repoUrl = Read-Host "請輸入您的 GitHub 儲存庫 HTTPS 網址"
$repoUrl = $repoUrl.Trim()

if (-not $repoUrl) {
    Write-Host "[錯誤] 網址不能為空！" -ForegroundColor Red
    Read-Host "按 Enter 鍵結束..."
    exit
}

# 5. 設定遠端與推送
Write-Host "正在設定 GitHub 遠端連接..." -ForegroundColor Green
git remote remove origin 2>$null
git remote add origin $repoUrl

Write-Host "正在推送檔案至 GitHub (這時可能會跳出 GitHub 登入視窗，請進行授權)..." -ForegroundColor Green
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Green
    Write-Host "🎉 上傳成功！您的專案已成功推送至 GitHub！" -ForegroundColor Green
    Write-Host "現在您可以前往 Render.com 連結此儲存庫進行免費部署了。" -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[錯誤] 上傳失敗！請確認您的儲存庫網址是否正確，且您已成功登入 GitHub。" -ForegroundColor Red
}

Read-Host "按 Enter 鍵結束..."
