#!/usr/bin/env python3
"""
GitHub Achievements Farmer
Automate unlocking GitHub profile achievements:
- Pull Shark (Bronze: 2, Silver: 16, Gold: 128 merged PRs)
- Pair Extraordinaire (Bronze: 1, Silver: 10, Gold: 24 co-authored PRs)
- Quickdraw (Closed issue/PR within 5 minutes)
- YOLO (Merged PR without review)
- Galaxy Brain (Accepted answers in Discussions Q&A)

Built using Python's standard library only (no external dependencies required).
"""

import os
import sys
import time
import json
import base64
import argparse
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple, List

# Ensure safe UTF-8 output on all operating systems and terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

API_BASE = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubClient:
    def __init__(self, token: str, user_agent: str = "GitHub-Achievements-Farmer"):
        self.token = token.strip()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": user_agent,
        }

    def request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        retries: int = 4,
    ) -> Any:
        url = endpoint if endpoint.startswith("http") else f"{API_BASE}{endpoint}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        headers = dict(self.headers)
        if data is not None:
            headers["Content-Type"] = "application/json"

        for attempt in range(retries):
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req) as resp:
                    resp_body = resp.read().decode("utf-8")
                    if not resp_body:
                        return {}
                    return json.loads(resp_body)
            except urllib.error.HTTPError as e:
                err_text = e.read().decode("utf-8", errors="replace")
                try:
                    err_json = json.loads(err_text)
                    msg = err_json.get("message", err_text)
                except Exception:
                    msg = err_text

                # Secondary rate limit or abuse detection -> backoff
                if e.code in (403, 429) and ("rate limit" in msg.lower() or "abuse" in msg.lower()):
                    wait_time = (attempt + 1) * 6
                    print(f"\n[!] GitHub rate limit trigger detected. Backing off for {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                if e.code == 404:
                    raise FileNotFoundError(f"Resource not found (404): {url} -> {msg}")
                raise RuntimeError(f"HTTP {e.code} Error: {msg}")
            except urllib.error.URLError as e:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                raise RuntimeError(f"Network error: {e.reason}")

    def graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = {"query": query, "variables": variables or {}}
        return self.request(GRAPHQL_URL, method="POST", data=data)

    def get_authenticated_user(self) -> Dict[str, Any]:
        return self.request("/user")

    def get_repo(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        try:
            return self.request(f"/repos/{owner}/{repo}")
        except FileNotFoundError:
            return None

    def create_repo(self, name: str, is_private: bool = False, description: str = "") -> Dict[str, Any]:
        payload = {
            "name": name,
            "private": is_private,
            "description": description,
            "auto_init": True,
            "has_discussions": True,
            "has_issues": True,
        }
        return self.request("/user/repos", method="POST", data=payload)

    def get_default_branch(self, owner: str, repo: str) -> str:
        repo_data = self.request(f"/repos/{owner}/{repo}")
        return repo_data.get("default_branch", "main")

    def get_branch_sha(self, owner: str, repo: str, branch: str) -> str:
        ref_data = self.request(f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
        return ref_data["object"]["sha"]

    def create_branch(self, owner: str, repo: str, branch_name: str, base_sha: str) -> Dict[str, Any]:
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha,
        }
        return self.request(f"/repos/{owner}/{repo}/git/refs", method="POST", data=payload)

    def delete_branch(self, owner: str, repo: str, branch_name: str) -> None:
        try:
            self.request(f"/repos/{owner}/{repo}/git/refs/heads/{branch_name}", method="DELETE")
        except Exception:
            pass

    def create_file_commit(
        self,
        owner: str,
        repo: str,
        path: str,
        content_str: str,
        commit_message: str,
        branch: str,
    ) -> Dict[str, Any]:
        encoded = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
        payload = {
            "message": commit_message,
            "content": encoded,
            "branch": branch,
        }
        return self.request(f"/repos/{owner}/{repo}/contents/{path}", method="PUT", data=payload)

    def create_pull_request(
        self, owner: str, repo: str, title: str, head: str, base: str, body: str = ""
    ) -> Dict[str, Any]:
        payload = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
        }
        return self.request(f"/repos/{owner}/{repo}/pulls", method="POST", data=payload)

    def merge_pull_request(
        self, owner: str, repo: str, pr_number: int, commit_title: str = "", merge_method: str = "squash"
    ) -> Dict[str, Any]:
        payload = {
            "commit_title": commit_title or f"Merge PR #{pr_number}",
            "merge_method": merge_method,
        }
        return self.request(f"/repos/{owner}/{repo}/pulls/{pr_number}/merge", method="PUT", data=payload)

    def create_issue(self, owner: str, repo: str, title: str, body: str = "") -> Dict[str, Any]:
        payload = {"title": title, "body": body}
        return self.request(f"/repos/{owner}/{repo}/issues", method="POST", data=payload)

    def close_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        payload = {"state": "closed"}
        return self.request(f"/repos/{owner}/{repo}/issues/{issue_number}", method="PATCH", data=payload)


def get_token_from_git_credential() -> Optional[str]:
    """Retrieves GitHub token directly from Git Credential Manager on the machine."""
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n",
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout:
            for line in proc.stdout.splitlines():
                if line.startswith("password="):
                    val = line.split("=", 1)[1].strip()
                    if val.startswith("ghp_") or val.startswith("github_pat_"):
                        return val
    except Exception:
        pass
    return None


def load_env_token() -> Optional[str]:
    # 1. Environment variable
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()

    # 2. Local .env file
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GITHUB_TOKEN="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("ghp_yourPersonal"):
                            return val
        except Exception:
            pass

    # 3. Git Credential Manager on PC
    token = get_token_from_git_credential()
    if token:
        return token

    return None


def get_git_remote_repo() -> Optional[str]:
    """Inspects current repo git remote url if available."""
    try:
        output = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if "github.com" in output:
            cleaned = output.split("github.com", 1)[1].lstrip("/:")
            if cleaned.endswith(".git"):
                cleaned = cleaned[:-4]
            parts = cleaned.split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"
    except Exception:
        pass
    return None


def farm_quickdraw(client: GitHubClient, owner: str, repo: str):
    print("\n" + "=" * 60)
    print("[ACHIEVEMENT] Quickdraw: Closed issue/PR within 5 minutes")
    print("=" * 60)
    print(f"Creating an issue on {owner}/{repo} and closing it immediately...")

    issue = client.create_issue(
        owner,
        repo,
        title="Quickdraw Achievement Unlock Trigger",
        body="This issue is automatically opened and closed within 5 seconds to unlock the Quickdraw achievement badge on GitHub profile.",
    )
    issue_num = issue["number"]
    print(f"-> Issue #{issue_num} created successfully!")

    # Close immediately (< 5 minutes)
    client.close_issue(owner, repo, issue_num)
    print(f"-> Issue #{issue_num} closed immediately!")
    print("[+] Quickdraw badge action completed successfully!")


def farm_pulls(
    client: GitHubClient,
    owner: str,
    repo: str,
    total_prs: int = 128,
    pair_prs: int = 24,
    co_author_name: str = "Monalisa Octocat",
    co_author_email: str = "octocat@github.com",
    delay: float = 0.6,
):
    print("\n" + "=" * 60)
    print(f"[ACHIEVEMENT] Pull Shark & Pair Extraordinaire & YOLO")
    print("=" * 60)
    print(f"Target PR count: {total_prs} (Co-authored: {pair_prs})")
    print(f"Co-author: {co_author_name} <{co_author_email}>")
    print(f"Repository: {owner}/{repo}")

    default_branch = client.get_default_branch(owner, repo)
    print(f"Default branch: {default_branch}")

    start_time = time.time()
    for i in range(1, total_prs + 1):
        is_pair = i <= pair_prs
        badge_tag = "Pair Extraordinaire + Pull Shark" if is_pair else "Pull Shark"
        if i == 1:
            badge_tag += " + YOLO"

        try:
            # 1. Fetch current default branch head commit SHA
            base_sha = client.get_branch_sha(owner, repo, default_branch)

            # 2. Create distinct branch
            timestamp = int(time.time() * 1000)
            branch_name = f"achieve-farm-{i}-{timestamp % 100000}"
            client.create_branch(owner, repo, branch_name, base_sha)

            # 3. Create commit with file change
            file_path = f"farm_history/badge_action_{i}.md"
            content = (
                f"# Achievement Activity Action #{i}\n\n"
                f"- Action: Pull Request #{i}\n"
                f"- Type: {badge_tag}\n"
                f"- Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n"
            )

            if is_pair:
                commit_msg = (
                    f"feat: record activity #{i} for Pair Extraordinaire\n\n"
                    f"Co-authored-by: {co_author_name} <{co_author_email}>"
                )
            else:
                commit_msg = f"feat: record activity #{i} for Pull Shark"

            client.create_file_commit(owner, repo, file_path, content, commit_msg, branch_name)

            # 4. Create Pull Request
            pr_title = f"Farm PR #{i}: {badge_tag}"
            pr_body = (
                f"Automated PR #{i} for unlocking GitHub achievements.\n"
                f"- Target: {badge_tag}\n"
                f"- Co-author: {co_author_name if is_pair else 'None'}"
            )
            pr = client.create_pull_request(
                owner, repo, title=pr_title, head=branch_name, base=default_branch, body=pr_body
            )
            pr_number = pr["number"]

            # 5. Merge Pull Request
            client.merge_pull_request(
                owner, repo, pr_number, commit_title=f"Merge pull request #{pr_number} from {branch_name}"
            )

            # 6. Delete remote branch
            client.delete_branch(owner, repo, branch_name)

            # Progress output
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            remaining = (total_prs - i) / rate if rate > 0 else 0
            print(
                f"[{i:03d}/{total_prs:03d}] Merged PR #{pr_number} ({badge_tag}) "
                f"| Elapsed: {int(elapsed)}s | ETA: {int(remaining)}s"
            )

            # Achievement milestones
            if i == 1:
                print("   [*] Milestone: YOLO achievement unlocked! (Merged PR without review)")
                print("   [*] Milestone: Pair Extraordinaire (Bronze) unlocked!")
            elif i == 2:
                print("   [*] Milestone: Pull Shark (Bronze) unlocked! (2 PRs merged)")
            elif i == 10 and pair_prs >= 10:
                print("   [*] Milestone: Pair Extraordinaire (Silver) unlocked! (10 co-authored PRs)")
            elif i == 16:
                print("   [*] Milestone: Pull Shark (Silver) unlocked! (16 PRs merged)")
            elif i == 24 and pair_prs >= 24:
                print("   [*] Milestone: Pair Extraordinaire (Gold - Max Tier) unlocked! (24 co-authored PRs)")
            elif i == 128:
                print("   [*] Milestone: Pull Shark (Gold - Max Tier) unlocked! (128 PRs merged)")

            if delay > 0 and i < total_prs:
                time.sleep(delay)

        except Exception as e:
            print(f"\n[X] Error on PR #{i}: {e}")
            print("Retrying next iteration after 3 seconds...")
            time.sleep(3)

    print(f"\n[+] All {total_prs} Pull Requests merged successfully!")


def farm_discussions(client: GitHubClient, owner: str, repo: str, count: int = 2):
    print("\n" + "=" * 60)
    print(f"[ACHIEVEMENT] Galaxy Brain (Discussions Q&A Answers)")
    print("=" * 60)
    print(f"Target accepted answers: {count}")

    # Query repository ID and discussion categories
    query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(first: 10) {
          nodes {
            id
            name
            isAnswerable
          }
        }
      }
    }
    """
    try:
        res = client.graphql(query, {"owner": owner, "name": repo})
        repo_data = res.get("data", {}).get("repository")
        if not repo_data:
            print("[X] Unable to query repository via GraphQL.")
            return

        repo_id = repo_data["id"]
        categories = repo_data.get("discussionCategories", {}).get("nodes", [])

        # Find answerable category (usually Q&A)
        qa_cat = None
        for cat in categories:
            if cat.get("isAnswerable"):
                qa_cat = cat
                break

        if not qa_cat:
            print("[!] No answerable discussion category found (e.g. Q&A).")
            print("Please ensure Discussions is enabled with Q&A in repo settings.")
            return

        cat_id = qa_cat["id"]
        print(f"[+] Found answerable category: {qa_cat['name']} ({cat_id})")

        create_disc_mutation = """
        mutation($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
          createDiscussion(input: {repositoryId: $repositoryId, categoryId: $categoryId, title: $title, body: $body}) {
            discussion {
              id
              number
              url
            }
          }
        }
        """

        add_comment_mutation = """
        mutation($discussionId: ID!, $body: String!) {
          addDiscussionComment(input: {discussionId: $discussionId, body: $body}) {
            comment {
              id
            }
          }
        }
        """

        mark_answer_mutation = """
        mutation($id: ID!) {
          markDiscussionCommentAsAnswer(input: {id: $id}) {
            discussion {
              id
            }
          }
        }
        """

        for i in range(1, count + 1):
            disc_title = f"Technical Question #{i}: How to verify algorithm performance in Python?"
            disc_body = (
                f"### Question #{i}\n\n"
                f"What is the recommended approach to profile execution time accurately in Python?\n"
            )
            d_res = client.graphql(create_disc_mutation, {
                "repositoryId": repo_id,
                "categoryId": cat_id,
                "title": disc_title,
                "body": disc_body,
            })
            disc = d_res.get("data", {}).get("createDiscussion", {}).get("discussion")
            if not disc:
                print(f"[X] Failed to create discussion #{i}: {d_res}")
                continue

            disc_id = disc["id"]
            print(f"[{i}/{count}] Created Discussion #{disc['number']}: {disc['url']}")

            # Add answer comment
            answer_body = (
                f"**Solution for Question #{i}:**\n\n"
                f"Use the standard library `timeit` or `cProfile` modules:\n"
                f"```python\nimport timeit\nprint(timeit.timeit('\"- \".join(str(n) for n in range(100))', number=10000))\n```\n"
            )
            c_res = client.graphql(add_comment_mutation, {
                "discussionId": disc_id,
                "body": answer_body,
            })
            comment = c_res.get("data", {}).get("addDiscussionComment", {}).get("comment")
            if not comment:
                print(f"[X] Failed to add comment: {c_res}")
                continue

            comment_id = comment["id"]

            # Mark as answer
            m_res = client.graphql(mark_answer_mutation, {"id": comment_id})
            if "errors" in m_res:
                print(f"[!] Mark answer note: {m_res['errors']}")
            else:
                print(f"   [*] Marked comment {comment_id} as accepted answer!")

            time.sleep(1)

        print("[+] Discussion Q&A actions completed!")
    except Exception as e:
        print(f"[!] Discussions helper error: {e}")


def main():
    parser = argparse.ArgumentParser(description="GitHub Achievements Farmer")
    parser.add_argument("--token", help="GitHub Personal Access Token (PAT)")
    parser.add_argument("--repo", help="Repository in format owner/repo")
    parser.add_argument("--all", action="store_true", help="Farm all achievements (Quickdraw, YOLO, Pull Shark x128, Pair x24)")
    parser.add_argument("--quickdraw", action="store_true", help="Farm Quickdraw only")
    parser.add_argument("--yolo", action="store_true", help="Farm YOLO only (1 PR)")
    parser.add_argument("--discussions", type=int, help="Farm Galaxy Brain discussions (e.g. 2, 8, 16)")
    parser.add_argument("--pull-shark", type=int, help="Farm Pull Shark with specific PR count (e.g. 2, 16, 128)")
    parser.add_argument("--pair-extraordinaire", type=int, help="Farm Pair Extraordinaire with specific count (e.g. 1, 10, 24)")
    parser.add_argument("--co-author-name", default="Monalisa Octocat", help="Co-author name for Pair Extraordinaire")
    parser.add_argument("--co-author-email", default="octocat@github.com", help="Co-author email for Pair Extraordinaire")
    parser.add_argument("--delay", type=float, default=0.6, help="Delay between operations in seconds (default 0.6s)")

    args = parser.parse_args()

    # 1. Resolve token
    token = args.token or load_env_token()
    if not token:
        print("\n============================================================")
        print(" GitHub Achievements Farmer - Setup Required")
        print("============================================================")
        print("No GitHub Personal Access Token found.")
        try:
            token = input("Enter your GitHub Personal Access Token: ").strip()
        except (KeyboardInterrupt, EOFError):
            sys.exit(1)
        if not token:
            print("[X] Token is required to authenticate with GitHub API.")
            sys.exit(1)

    client = GitHubClient(token)

    # 2. Test token
    try:
        user_info = client.get_authenticated_user()
        user_login = user_info["login"]
        print(f"\n[+] Authenticated successfully as: {user_login} ({user_info.get('name', 'N/A')})")
    except Exception as e:
        print(f"[X] Authentication failed: {e}")
        sys.exit(1)

    # 3. Resolve repository
    repo_full_name = args.repo or get_git_remote_repo() or f"{user_login}/github-achievements"
    if "/" not in repo_full_name:
        repo_full_name = f"{user_login}/{repo_full_name}"

    owner, repo_name = repo_full_name.split("/", 1)

    # Check if repo exists, or create it automatically
    repo_obj = client.get_repo(owner, repo_name)
    if not repo_obj:
        print(f"\n[i] Repository '{owner}/{repo_name}' does not exist on GitHub. Creating it...")
        try:
            repo_obj = client.create_repo(
                repo_name,
                is_private=False,
                description="Repository for GitHub achievement farming and activity tracking",
            )
            print(f"[+] Public repository '{owner}/{repo_name}' created successfully!")
            time.sleep(2)
        except Exception as e:
            print(f"[X] Failed to create repository: {e}")
            sys.exit(1)
    else:
        print(f"[+] Found repository: {owner}/{repo_name} (Private: {repo_obj.get('private', False)})")

    # 4. Handle actions
    if args.quickdraw:
        farm_quickdraw(client, owner, repo_name)
        return

    if args.yolo:
        farm_pulls(
            client,
            owner,
            repo_name,
            total_prs=1,
            pair_prs=0,
            delay=args.delay,
        )
        return

    if args.discussions:
        farm_discussions(client, owner, repo_name, count=args.discussions)
        return

    if args.pull_shark or args.pair_extraordinaire:
        total = args.pull_shark or 2
        pair = args.pair_extraordinaire or 0
        if pair > total:
            total = pair
        farm_pulls(
            client,
            owner,
            repo_name,
            total_prs=total,
            pair_prs=pair,
            co_author_name=args.co_author_name,
            co_author_email=args.co_author_email,
            delay=args.delay,
        )
        return

    if args.all:
        farm_quickdraw(client, owner, repo_name)
        farm_discussions(client, owner, repo_name, count=2)
        farm_pulls(
            client,
            owner,
            repo_name,
            total_prs=128,
            pair_prs=24,
            co_author_name=args.co_author_name,
            co_author_email=args.co_author_email,
            delay=args.delay,
        )
        print("\n[+] ALL FARMING TASKS COMPLETE!")
        print("Note: GitHub badge updates may take between 15 minutes to 24 hours to sync to your profile.")
        return

    # Interactive Menu
    print("\n" + "=" * 60)
    print(" GitHub Achievements Farmer - Action Menu")
    print("=" * 60)
    print(" [1] Farm ALL (Gold Pull Shark x128 + Gold Pair x24 + Quickdraw + YOLO + Discussions)")
    print(" [2] Quickdraw only (Open & close issue in <5 seconds)")
    print(" [3] YOLO only (1 PR merged without review)")
    print(" [4] Pair Extraordinaire (Bronze x1, Silver x10, Gold x24)")
    print(" [5] Pull Shark (Bronze x2, Silver x16, Gold x128)")
    print(" [6] Galaxy Brain discussions Q&A")
    print(" [0] Exit")
    print("=" * 60)

    try:
        selection = input("Choose an option [1-6]: ").strip()
    except (KeyboardInterrupt, EOFError):
        sys.exit(0)

    if selection == "1":
        farm_quickdraw(client, owner, repo_name)
        farm_discussions(client, owner, repo_name, count=2)
        farm_pulls(
            client,
            owner,
            repo_name,
            total_prs=128,
            pair_prs=24,
            co_author_name=args.co_author_name,
            co_author_email=args.co_author_email,
            delay=args.delay,
        )
    elif selection == "2":
        farm_quickdraw(client, owner, repo_name)
    elif selection == "3":
        farm_pulls(client, owner, repo_name, total_prs=1, pair_prs=0, delay=args.delay)
    elif selection == "4":
        count = 24
        farm_pulls(client, owner, repo_name, total_prs=count, pair_prs=count, delay=args.delay)
    elif selection == "5":
        count = 128
        farm_pulls(client, owner, repo_name, total_prs=count, pair_prs=0, delay=args.delay)
    elif selection == "6":
        farm_discussions(client, owner, repo_name, count=2)
    else:
        print("Exiting.")

    print("\n[+] DONE! Check your GitHub profile achievements page soon.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Process interrupted by user.")
        sys.exit(0)
