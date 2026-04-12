# GitHub Setup Guide

This file walks through turning this folder into a Git repository and pushing it to GitHub.

## 1. Install Git

If `git` is not installed:

```bash
sudo apt update
sudo apt install git
```

Optional but recommended:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## 2. Create the Git repository

From inside this project folder:

```bash
git init
```

This creates the hidden `.git` folder.

## 3. Make the first commit

```bash
git add .
git commit -m "Initial commit"
```

## 4. Connect the GitHub repository

If the GitHub repo already exists:

```bash
git remote add origin https://github.com/SirMushy/Unofficial-TailScale-GUI.git
git branch -M main
```

If you already added `origin` before, update it instead:

```bash
git remote set-url origin https://github.com/SirMushy/Unofficial-TailScale-GUI.git
```

## 5. Authenticate with GitHub

GitHub does not accept your normal account password for `git push`.

Best option:

```bash
gh auth login
```

Choose:

- `GitHub.com`
- `HTTPS`
- `Login with a web browser`

If `gh` is not installed:

```bash
sudo apt install gh
```

## 6. If the remote already has files

If GitHub already has a README or other starter files, pull them first:

```bash
git pull origin main --allow-unrelated-histories --no-rebase
```

If it opens an editor for the merge message, save and close it.

If there are conflicts:

```bash
git status
```

Fix the files, then finish with:

```bash
git add .
git commit
```

## 7. Push the project

```bash
git push -u origin main
```

## 8. Useful checks

See current status:

```bash
git status
```

See which remote is connected:

```bash
git remote -v
```

See commit history:

```bash
git log --oneline
```

## 9. If you want your local version to replace the GitHub one

Only do this if the GitHub repo does not contain anything important:

```bash
git push -u origin main --force
```

## Recommended full flow

If you are starting from scratch, these are the usual commands:

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/SirMushy/Unofficial-TailScale-GUI.git
git branch -M main
git pull origin main --allow-unrelated-histories --no-rebase
git push -u origin main
```
