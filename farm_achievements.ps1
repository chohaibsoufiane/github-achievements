<#
.SYNOPSIS
    GitHub Achievements Farmer (PowerShell Edition)
    Farms Pull Shark, Pair Extraordinaire, Quickdraw, and YOLO badges directly via GitHub REST API.

.DESCRIPTION
    Automates GitHub achievement unlocks with zero extra dependencies using Invoke-RestMethod.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$false)]
    [string]$Token,

    [Parameter(Mandatory=$false)]
    [string]$Repo,

    [Parameter(Mandatory=$false)]
    [switch]$All,

    [Parameter(Mandatory=$false)]
    [switch]$Quickdraw,

    [Parameter(Mandatory=$false)]
    [switch]$Yolo,

    [Parameter(Mandatory=$false)]
    [int]$PullShark = 0,

    [Parameter(Mandatory=$false)]
    [int]$PairExtraordinaire = 0,

    [Parameter(Mandatory=$false)]
    [string]$CoAuthorName = "Monalisa Octocat",

    [Parameter(Mandatory=$false)]
    [string]$CoAuthorEmail = "octocat@github.com",

    [Parameter(Mandatory=$false)]
    [double]$Delay = 0.6
)

$ApiBase = "https://api.github.com"

# 1. Resolve Token
if (-not $Token) {
    if ($env:GITHUB_TOKEN) {
        $Token = $env:GITHUB_TOKEN
    } elseif (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match "^GITHUB_TOKEN\s*=\s*(.*)$") {
                $Token = $matches[1].Trim(' "''')
            }
        }
    }
}

if (-not $Token) {
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host " GitHub Achievements Farmer - Authentication" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Please enter your GitHub Personal Access Token (classic with 'repo' scope):"
    $Token = Read-Host "Token"
    if (-not $Token) {
        Write-Error "A GitHub token is required."
        exit 1
    }
}

$Headers = @{
    "Authorization" = "Bearer $Token"
    "Accept"        = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent"    = "GitHub-Achievements-Farmer-PS"
}

# 2. Test Token & Get User
try {
    $User = Invoke-RestMethod -Uri "$ApiBase/user" -Headers $Headers -Method Get
    Write-Host "`n[+] Successfully authenticated as: $($User.login) ($($User.name))" -ForegroundColor Green
} catch {
    Write-Error "Failed to authenticate with GitHub API: $_"
    exit 1
}

# 3. Resolve Target Repo
if (-not $Repo) {
    $defaultRepo = "$($User.login)/github-achievements"
    Write-Host "`nTarget repository not provided. Use '$defaultRepo'? [Y/n]: " -NoNewline -ForegroundColor Yellow
    $ans = Read-Host
    if ($ans -eq "" -or $ans -match "^[yY]") {
        $Repo = $defaultRepo
    } else {
        $Repo = Read-Host "Enter repository ($($User.login)/<repo-name>)"
    }
}

if ($Repo -notmatch "/") {
    $Repo = "$($User.login)/$Repo"
}

$parts = $Repo.Split("/")
$owner = $parts[0]
$repoName = $parts[1]

# Check repo existence
try {
    $repoObj = Invoke-RestMethod -Uri "$ApiBase/repos/$owner/$repoName" -Headers $Headers -Method Get
    Write-Host "[+] Target repo found: $owner/$repoName" -ForegroundColor Green
} catch {
    Write-Host "[i] Repo $owner/$repoName not found. Creating public repository..." -ForegroundColor Yellow
    $createBody = @{
        name = $repoName
        private = $false
        auto_init = $true
        description = "Repository for GitHub achievement farming and activity tracking"
    } | ConvertTo-Json
    $repoObj = Invoke-RestMethod -Uri "$ApiBase/user/repos" -Headers $Headers -Method Post -Body $createBody -ContentType "application/json"
    Write-Host "[+] Repository created successfully!" -ForegroundColor Green
    Start-Sleep -Seconds 2
}

$defaultBranch = if ($repoObj.default_branch) { $repoObj.default_branch } else { "main" }

function Run-Quickdraw {
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host "🎯 Quickdraw Achievement Action" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Cyan
    $body = @{
        title = "Quickdraw Achievement Trigger"
        body  = "This issue is opened and closed immediately to earn Quickdraw."
    } | ConvertTo-Json

    $issue = Invoke-RestMethod -Uri "$ApiBase/repos/$owner/$repoName/issues" -Headers $Headers -Method Post -Body $body -ContentType "application/json"
    Write-Host "-> Opened Issue #$($issue.number)" -ForegroundColor Green

    $patch = @{ state = "closed" } | ConvertTo-Json
    $null = Invoke-RestMethod -Uri "$ApiBase/repos/$owner/$repoName/issues/$($issue.number)" -Headers $Headers -Method Patch -Body $patch -ContentType "application/json"
    Write-Host "-> Closed Issue #$($issue.number) in <5 seconds!" -ForegroundColor Green
    Write-Host "✅ Quickdraw trigger complete!`n" -ForegroundColor Green
}

function Run-Pulls {
    param(
        [int]$TotalPRs,
        [int]$PairPRs
    )
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host "🎯 Farming Pull Shark & Pair Extraordinaire & YOLO" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Total PRs: $TotalPRs (Co-authored: $PairPRs)"

    $startTime = Get-Date

    for ($i = 1; $i -le $TotalPRs; $i++) {
        $isPair = ($i -le $PairPRs)
        $badge = if ($isPair) { "Pair Extraordinaire + Pull Shark" } else { "Pull Shark" }
        if ($i -eq 1) { $badge += " + YOLO" }

        try {
            # 1. Get base sha
            $ref = Invoke-RestMethod -Uri "$ApiBase/repos/$owner/$repoName/git/ref/heads/$defaultBranch" -Headers $Headers -Method Get
            $baseSha = $ref.object.sha

            # 2. Create branch
            $ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() % 100000
            $branch = "achieve-farm-$i-$ts"
            $branchPayload = @{
                ref = "refs/heads/$branch"
                sha = $baseSha
            } | ConvertTo-Json
            $null = Invoke-RestMethod -Uri "$ApiBase/repos/$owner/$repoName/git/refs" -Headers $Headers -Method Post -Body $branchPayload -ContentType "application/json"

            # 3. Create commit
            $fileContent = "# Activity Entry $i`nBadge: $badge`nDate: $(Get-Date)"
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($fileContent)
            $b64 = [System.Convert]::ToBase64String($bytes)

            $commitMsg = if ($isPair) {
                "feat: activity record $i for Pair Extraordinaire`n`nCo-authored-by: $CoAuthorName <$CoAuthorEmail>"
            } else {
                "feat: activity record $i for Pull Shark"
            }

            $putPayload = @{
                message = $commitMsg
                content = $b64
                branch  = $branch
            } | ConvertTo-Json
            $null = Invoke-RestMethod -Uri "$ApiBase/repos/$owner/$repoName/contents/farm_data/entry_$i.md" -Headers $Headers -Method Put -Body $putPayload -ContentType "application/json"

            # 4. Open PR
            $prPayload = @{
                title = "Farm PR #$i: $badge"
                head  = $branch
                base  = $defaultBranch
                body  = "Achievement farm entry #$i"
            } | ConvertTo-Json
            $pr = Invoke-RestMethod -Uri "$ApiBase/repos/$owner/$repoName/pulls" -Headers $Headers -Method Post -Body $prPayload -ContentType "application/json"

            # 5. Merge PR
            $mergePayload = @{
                commit_title = "Merge PR #$($pr.number) from $branch"
                merge_method = "squash"
            } | ConvertTo-Json
            $null = Invoke-RestMethod -Uri "$ApiBase/repos/$owner/$repoName/pulls/$($pr.number)/merge" -Headers $Headers -Method Put -Body $mergePayload -ContentType "application/json"

            # 6. Delete branch
            try {
                $null = Invoke-RestMethod -Uri "$ApiBase/repos/$owner/$repoName/git/refs/heads/$branch" -Headers $Headers -Method Delete
            } catch {}

            $elapsed = ((Get-Date) - $startTime).TotalSeconds
            $rate = if ($elapsed -gt 0) { $i / $elapsed } else { 0 }
            $remaining = if ($rate -gt 0) { [math]::Round(($TotalPRs - $i) / $rate) } else { 0 }
            Write-Host "[$i/$TotalPRs] Merged PR #$($pr.number) ($badge) | Elapsed: $([int]$elapsed)s | ETA: $($remaining)s" -ForegroundColor Green

            if ($i -eq 1) {
                Write-Host "   🌟 Milestone: YOLO unlocked! (Merged PR without review)" -ForegroundColor Magenta
                Write-Host "   🌟 Milestone: Pair Extraordinaire (Bronze) unlocked!" -ForegroundColor Magenta
            } elseif ($i -eq 2) {
                Write-Host "   🌟 Milestone: Pull Shark (Bronze) unlocked!" -ForegroundColor Magenta
            } elseif ($i -eq 10 -and $PairPRs -ge 10) {
                Write-Host "   🌟 Milestone: Pair Extraordinaire (Silver) unlocked!" -ForegroundColor Magenta
            } elseif ($i -eq 16) {
                Write-Host "   🌟 Milestone: Pull Shark (Silver) unlocked!" -ForegroundColor Magenta
            } elseif ($i -eq 24 -and $PairPRs -ge 24) {
                Write-Host "   🌟 Milestone: Pair Extraordinaire (Gold - Max Tier) unlocked!" -ForegroundColor Magenta
            } elseif ($i -eq 128) {
                Write-Host "   🌟 Milestone: Pull Shark (Gold - Max Tier) unlocked!" -ForegroundColor Magenta
            }

            if ($Delay -gt 0 -and $i -lt $TotalPRs) {
                Start-Sleep -Milliseconds ([int]($Delay * 1000))
            }
        } catch {
            Write-Host "[X] Error on PR #$i: $_" -ForegroundColor Red
            Start-Sleep -Seconds 3
        }
    }
}

# Execution
if ($Quickdraw) {
    Run-Quickdraw
    exit 0
}

if ($Yolo) {
    Run-Pulls -TotalPRs 1 -PairPRs 0
    exit 0
}

if ($PullShark -gt 0 -or $PairExtraordinaire -gt 0) {
    $total = if ($PullShark -gt 0) { $PullShark } else { 2 }
    $pair = if ($PairExtraordinaire -gt 0) { $PairExtraordinaire } else { 0 }
    if ($pair -gt $total) { $total = $pair }
    Run-Pulls -TotalPRs $total -PairPRs $pair
    exit 0
}

if ($All) {
    Run-Quickdraw
    Run-Pulls -TotalPRs 128 -PairPRs 24
    Write-Host "`n🎉 All farming complete! Badges will reflect on GitHub profile within hours." -ForegroundColor Green
    exit 0
}

# Menu
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " 🚀 GitHub Achievements Farmer (PowerShell)" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [1] 🏆 Farm ALL (Gold Pull Shark x128 + Gold Pair x24 + Quickdraw + YOLO)"
Write-Host " [2] ⚡ Quickdraw only (Issue closed in <5 seconds)"
Write-Host " [3] 🚀 YOLO only (1 PR merged without review)"
Write-Host " [4] 🤝 Pair Extraordinaire (Bronze x1, Silver x10, Gold x24)"
Write-Host " [5] 🦈 Pull Shark (Bronze x2, Silver x16, Gold x128)"
Write-Host " [0] Exit"
Write-Host "============================================================" -ForegroundColor Cyan
$choice = Read-Host "Select option [1-5]"

switch ($choice) {
    "1" {
        Run-Quickdraw
        Run-Pulls -TotalPRs 128 -PairPRs 24
    }
    "2" { Run-Quickdraw }
    "3" { Run-Pulls -TotalPRs 1 -PairPRs 0 }
    "4" {
        $t = Read-Host "Select Tier: [1] Bronze (1), [2] Silver (10), [3] Gold (24)"
        $cnt = if ($t -eq "3") { 24 } elseif ($t -eq "2") { 10 } else { 1 }
        Run-Pulls -TotalPRs $cnt -PairPRs $cnt
    }
    "5" {
        $t = Read-Host "Select Tier: [1] Bronze (2), [2] Silver (16), [3] Gold (128)"
        $cnt = if ($t -eq "3") { 128 } elseif ($t -eq "2") { 16 } else { 2 }
        Run-Pulls -TotalPRs $cnt -PairPRs 0
    }
    default { Write-Host "Exiting." }
}
