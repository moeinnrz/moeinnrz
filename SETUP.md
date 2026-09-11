# @moeinnrz profile setup

This is an update to the existing `moeinnrz` profile repository. Do not create another repository.

## Files to replace/add

Replace:

- `README.md`
- `assets/header.svg`
- `.github/workflows/snake.yml`

Add:

- `.github/scripts/generate_dashboard.py`

## What changed

The README now uses a custom live analytics dashboard instead of relying on multiple separate statistics cards. The dashboard is generated from GitHub's GraphQL API by GitHub Actions and includes:

- contribution total
- current streak
- longest streak
- repository count
- stars
- monthly contribution trend
- repository language distribution
- contribution type breakdown

The same workflow also generates the contribution snake.

## First run

1. Commit the files to the `main` branch.
2. Open **Actions**.
3. Select **Update profile analytics**.
4. Click **Run workflow**.
5. Wait for the workflow to finish successfully.
6. Open `https://github.com/moeinnrz` and refresh the profile.

The workflow publishes generated SVG assets to the `output` branch.

## Important

The repository must remain named `moeinnrz` for GitHub to recognize it as the profile README repository. The repository must be public for the README to appear publicly on the profile. If you are still designing, keeping it private is fine; make it public only for the final reveal.
