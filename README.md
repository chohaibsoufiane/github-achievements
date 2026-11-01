# 🏆 GitHub Achievements Farmer & Badge Recovery

A fast, automated repository designed to help you recover and farm your lost GitHub profile achievements!

Whether you lost an old account or want to rebuild your showcase badges quickly, this repo provides automated scripts and workflows to unlock achievements cleanly and reliably.

---

## 🎖️ Available Achievements Breakdown

| Badge | Achievement Name | Unlock Criteria | Tiers | Automation Status |
| :---: | :--- | :--- | :--- | :---: |
| 🦈 | **Pull Shark** | Merged Pull Requests | 🥉 Bronze (2 PRs)<br>🥈 Silver (16 PRs)<br>🥇 Gold (128 PRs) | **Fully Automated** |
| 🤝 | **Pair Extraordinaire** | Co-authored a merged commit | 🥉 Bronze (1 PR)<br>🥈 Silver (10 PRs)<br>🥇 Gold (24 PRs) | **Fully Automated** |
| ⚡ | **Quickdraw** | Closed an issue or PR within 5 minutes | 🥉 Single Tier | **Fully Automated** (< 5s) |
| 🚀 | **YOLO** | Merged a pull request without code reviews | 🥉 Single Tier | **Fully Automated** |
| 🧠 | **Galaxy Brain** | Had an answer accepted in GitHub Discussions | 🥉 Bronze (2)<br>🥈 Silver (8)<br>🥇 Gold (16)<br>💎 Onyx (32) | **Semi-Automated** (See guide below) |
| ⭐ | **Starstruck** | Repository has stars | 🥉 Bronze (16)<br>🥈 Silver (128)<br>🥇 Gold (512) | Community-driven |
| 💖 | **Public Sponsor** | Sponsoring an open-source contributor | 🥉 Single Tier | Manual ($1 one-time) |

*(Note: Legacy badges like Arctic Code Vault and Mars 2020 Contributor were historic 2020 events and can no longer be acquired on new accounts).*

---

## ⚡ Fast Track: How to Farm All Unlocks

### Step 1: Create a GitHub Personal Access Token (PAT)
GitHub achievements **require human user identity** (automated bot tokens like default GitHub Actions bot don't receive achievements).
1. Go to [GitHub Settings -> Developer Settings -> Personal access tokens (classic)](https://github.com/settings/tokens).
2. Click **Generate new token (classic)**.
3. Note name: `achievements-farmer`.
4. Select scope:
   - ✅ **`repo`** (Full control of private repositories and activity)
5. Click **Generate token** and copy it (starts with `ghp_...`).

---

### Step 2: Run the Farmer

You can run this locally in **Python**, in **PowerShell**, or directly via **GitHub Actions** in the cloud.

#### Option A: Run via Python (Recommended - Works on any OS)
No external dependencies required (uses built-in standard library):

```bash
# Farm all badges (Gold Pull Shark 128x + Gold Pair 24x + Quickdraw + YOLO)
python farm_achievements.py --all
```
*Or run interactive mode:*
```bash
python farm_achievements.py
```
*Or farm specific badges:*
```bash
python farm_achievements.py --quickdraw
python farm_achievements.py --pull-shark 128
python farm_achievements.py --pair-extraordinaire 24
```

---

#### Option B: Run via PowerShell (Windows Native)
Open PowerShell in this directory:

```powershell
# Interactive menu:
.\farm_achievements.ps1

# Or one-liner to farm everything:
.\farm_achievements.ps1 -All
```

---

#### Option C: Cloud Automation via GitHub Actions
If you push this repository to your GitHub account:
1. Go to your repo **Settings** -> **Secrets and variables** -> **Actions**.
2. Add a **New repository secret**:
   - Name: `PAT_TOKEN`
   - Value: *(your `ghp_...` personal access token)*
3. Go to the **Actions** tab in your repository.
4. Select **Farm GitHub Achievements** in the left sidebar.
5. Click **Run workflow** -> Select `all` -> Click **Run workflow**.

---

## 🧠 How to Get the Remaining Achievements

### 1. 🧠 Galaxy Brain (Accepted Discussion Answers)
- **What it is:** Have your answers accepted in GitHub Discussions (2 answers for Bronze, 8 for Silver, 16 for Gold).
- **Anti-spam note:** GitHub's achievement evaluator filters out answers if you answer your own questions in your own repository.
- **Fastest way to get it:**
  1. Visit popular active discussions such as [GitHub Community Discussions](https://github.com/orgs/community/discussions) or active library repositories (e.g. Next.js, Tailwind, etc.).
  2. Filter by the **Q&A** category.
  3. Provide a clear, correct solution to 2 questions.
  4. Once marked as the answer by the author or maintainer, the badge unlocks!

### 2. 💖 Public Sponsor
- Go to any public open-source project or developer offering GitHub Sponsors (e.g. authors of tools you use).
- Sponsor with a **$1 one-time payment**.
- You will immediately receive the **Public Sponsor** badge on your profile.

### 3. ⭐ Starstruck
- Earned when your repository reaches 16 stars (Bronze) / 128 stars (Silver).
- Share your useful open source projects, curated lists, or developer templates on Reddit (`r/github`, `r/opensource`), Twitter/X, or developer Discord servers.

---

## 📌 Important Notes & Troubleshooting

1. **Profile Visibility Setting**:
   - If you farm achievements in a **private** repository, make sure to enable:
     **Profile -> Edit profile -> Settings -> Check "Show private contributions & achievements"**.
   - If your repository is **public**, achievements are tracked automatically!

2. **Achievement Sync Delay**:
   - GitHub does **not** always award badges immediately on the exact second a PR merges.
   - GitHub runs periodic background worker queues for badge evaluations. Badges typically appear on your profile anywhere between **15 minutes to 24 hours** after completion.

3. **Check Your Achievements**:
   - Visit your profile: `https://github.com/<your-username>`
   - Scroll down to the **Achievements** section in the left sidebar.
   - Click on any badge to inspect its tier status and unlock history!

---

## 📜 License
MIT License. Created to help developers restore their achievements and memories!
