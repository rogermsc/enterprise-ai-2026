# Branch Protection Configuration

## Recommended Settings

Configure branch protection rules in GitHub Settings → Branches → Branch protection rules.

### Main Branch Protection

**Branch name pattern:** `main`

#### Protection Rules

- [x] **Require a pull request before merging**
  - [x] Require approvals: **1** (increase to 2 for larger teams)
  - [x] Dismiss stale pull request approvals when new commits are pushed
  - [x] Require review from Code Owners
  - [x] Require approval of the most recent reviewable push

- [x] **Require status checks to pass before merging**
  - [x] Require branches to be up to date before merging
  - Required status checks:
    - `Lint`
    - `Test`
    - `Security Scan`
    - `Build`
    - `Terraform Validate`
    - `Helm Validate`
    - `Analyze (python)` (CodeQL)

- [x] **Require conversation resolution before merging**

- [x] **Require signed commits** (recommended for enterprise)

- [x] **Require linear history**

- [x] **Do not allow bypassing the above settings**

- [ ] Allow force pushes: **DISABLED**
- [ ] Allow deletions: **DISABLED**

### Develop Branch Protection

**Branch name pattern:** `develop`

#### Protection Rules

- [x] **Require a pull request before merging**
  - [x] Require approvals: **1**
  - [x] Dismiss stale pull request approvals when new commits are pushed

- [x] **Require status checks to pass before merging**
  - Required status checks:
    - `Lint`
    - `Test`

### Feature Branch Pattern

**Branch name pattern:** `feature/*`

- [x] Allow force pushes (for rebasing)
- [x] Allow deletions (cleanup after merge)

## Rulesets (GitHub Enterprise)

For GitHub Enterprise, use rulesets for more granular control:

```json
{
  "name": "Production Protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 2,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "required_status_checks": [
          {"context": "Lint"},
          {"context": "Test"},
          {"context": "Security Scan"},
          {"context": "Build"}
        ],
        "strict_required_status_checks_policy": true
      }
    },
    {
      "type": "required_signatures"
    },
    {
      "type": "required_linear_history"
    }
  ]
}
```

## Environment Protection

For deployment workflows, configure environment protection:

### Production Environment

- [x] Required reviewers: Platform team
- [x] Wait timer: 10 minutes
- [x] Deployment branches: `main` only
- [x] Secrets accessible

### Staging Environment

- [x] Deployment branches: `main`, `develop`
- [x] Secrets accessible

## Commit Signing

Require signed commits for accountability:

```bash
# Configure Git to sign commits
git config --global commit.gpgsign true
git config --global user.signingkey YOUR_GPG_KEY_ID

# Verify commits
git log --show-signature
```

## CODEOWNERS Integration

Branch protection works with CODEOWNERS to require reviews from specific teams:

- Platform changes → @rogermsc
- Infrastructure changes → @rogermsc
- Security changes → @rogermsc

See [CODEOWNERS](../.github/CODEOWNERS) for full configuration.
