# Releasing

This document describes the release process for Enterprise AI Platform.

## Versioning

We use [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features, backward compatible
- **PATCH** (0.0.X): Bug fixes, security patches

## Release Process

### 1. Prepare the Release

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create a release branch
git checkout -b release/vX.Y.Z
```

### 2. Update Version Numbers

Update version in:
- `pyproject.toml`
- `src/goodai_assess/__init__.py` (if applicable)

### 3. Update CHANGELOG.md

Move items from `[Unreleased]` to the new version section:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

### 4. Run Tests

```bash
make test
make lint
```

### 5. Create Pull Request

```bash
git add -A
git commit -m "release: prepare vX.Y.Z"
git push origin release/vX.Y.Z
```

Create a PR to main and get approval.

### 6. Merge and Tag

After PR is merged:

```bash
git checkout main
git pull origin main
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

### 7. Create GitHub Release

1. Go to GitHub Releases
2. Click "Draft a new release"
3. Select the tag `vX.Y.Z`
4. Title: `vX.Y.Z`
5. Copy release notes from CHANGELOG.md
6. Publish release

## Hotfix Process

For critical fixes to a released version:

```bash
# Branch from the release tag
git checkout -b hotfix/vX.Y.Z+1 vX.Y.Z

# Make fixes, then follow normal release process
```

## Pre-release Versions

For alpha/beta releases:

```bash
git tag -a vX.Y.Z-alpha.1 -m "Pre-release vX.Y.Z-alpha.1"
git tag -a vX.Y.Z-beta.1 -m "Pre-release vX.Y.Z-beta.1"
git tag -a vX.Y.Z-rc.1 -m "Release candidate vX.Y.Z-rc.1"
```

## Checklist

- [ ] All tests pass
- [ ] CHANGELOG.md updated
- [ ] Version numbers updated
- [ ] PR approved and merged
- [ ] Tag created and pushed
- [ ] GitHub Release published
