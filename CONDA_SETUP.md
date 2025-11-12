# Conda Environment Setup Guide

This project uses **Python 3.12** as the standard version. We recommend using Anaconda/Miniconda to manage your Python environment.

## Why Python 3.12?

Python 3.12 is the latest stable version of Python with:
- Improved performance (up to 5% faster than 3.11)
- Better error messages
- Type hinting improvements
- Latest security updates
- Long-term support

## Prerequisites

### Install Anaconda or Miniconda

Choose one of the following:

#### Option 1: Anaconda (Full distribution with GUI)
Download and install from: https://www.anaconda.com/download

#### Option 2: Miniconda (Minimal installation, recommended)
Download and install from: https://docs.conda.io/en/latest/miniconda.html

**For Linux/macOS:**
```bash
# Download Miniconda installer
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
# Or for macOS:
# wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh

# Run installer
bash Miniconda3-latest-Linux-x86_64.sh

# Follow the prompts, accept license, and allow conda init
```

**For Windows:**
Download the installer from the link above and run it.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/rkajaria-1507/BAFL-Backend.git
cd BAFL-Backend
```

### 2. Create Conda Environment

#### Option A: Using environment.yml (Recommended)

```bash
# Create environment from file
conda env create -f environment.yml

# Activate the environment
conda activate bafl-backend
```

#### Option B: Manual Setup

```bash
# Create environment with Python 3.12
conda create -n bafl-backend python=3.12

# Activate the environment
conda activate bafl-backend

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Verify Installation

```bash
# Check Python version (should show 3.12.x)
python --version

# Verify environment is active
conda env list
# You should see an asterisk (*) next to bafl-backend

# Run tests to ensure everything works
pytest tests/
```

## Daily Development Workflow

### Activating the Environment

Every time you work on the project, activate the Conda environment:

```bash
cd BAFL-Backend
conda activate bafl-backend
```

### Deactivating the Environment

When you're done working:

```bash
conda deactivate
```

## Managing Dependencies

### Installing New Packages

Always use pip when inside the activated environment:

```bash
conda activate bafl-backend
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt
```

### Updating the Environment

If someone updates the environment.yml file:

```bash
# Update existing environment
conda env update -f environment.yml --prune
```

## Useful Conda Commands

### List All Environments
```bash
conda env list
# or
conda info --envs
```

### Check Python Version
```bash
python --version
```

### List Installed Packages
```bash
conda list
# or
pip list
```

### Remove Environment (if needed)
```bash
conda deactivate
conda env remove -n bafl-backend
```

### Export Environment (for sharing)
```bash
# Export with all packages
conda env export > environment.yml

# Or update pip requirements only
pip freeze > requirements.txt
```

## IDE Configuration

### VS Code

1. Install Python extension
2. Open Command Palette (Ctrl+Shift+P / Cmd+Shift+P)
3. Select "Python: Select Interpreter"
4. Choose the `bafl-backend` conda environment

The interpreter path will look like:
- **Linux/macOS**: `~/miniconda3/envs/bafl-backend/bin/python`
- **Windows**: `C:\Users\YourName\miniconda3\envs\bafl-backend\python.exe`

### PyCharm

1. Go to File → Settings → Project → Python Interpreter
2. Click gear icon → Add
3. Select "Conda Environment" → "Existing environment"
4. Browse to the conda environment path
5. Click OK

## Troubleshooting

### Issue: conda: command not found

**Solution:** Restart your terminal or run:
```bash
# Add conda to PATH
export PATH="$HOME/miniconda3/bin:$PATH"

# Or permanently add to shell profile
echo 'export PATH="$HOME/miniconda3/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Issue: Environment activation not working

**Solution:** Initialize conda for your shell:
```bash
conda init bash  # or zsh, fish, etc.
# Restart terminal
```

### Issue: Wrong Python version

**Solution:** Make sure you're in the correct environment:
```bash
conda deactivate
conda activate bafl-backend
python --version  # Should show 3.12.x
```

### Issue: Package conflicts

**Solution:** Recreate the environment:
```bash
conda deactivate
conda env remove -n bafl-backend
conda env create -f environment.yml
conda activate bafl-backend
```

### Issue: Permission errors when installing packages

**Solution:** Don't use sudo with conda/pip. Ensure you're in the activated environment:
```bash
conda activate bafl-backend
pip install package-name  # No sudo needed
```

## CI/CD Compatibility

Our GitHub Actions CI/CD pipeline uses Python 3.12 to match the local development environment. This ensures:
- Consistent behavior between local and CI
- No "works on my machine" issues
- Same test results locally and in CI

## Best Practices

1. **Always activate the environment** before working on the project
2. **Use Python 3.12** - Don't use older versions
3. **Don't modify base environment** - Always work in the project environment
4. **Update dependencies properly** - Use pip freeze after adding packages
5. **Test before committing** - Run tests in the conda environment
6. **Keep environment.yml updated** - Regenerate after major dependency changes

## Additional Resources

- [Conda Documentation](https://docs.conda.io/)
- [Conda Cheat Sheet](https://docs.conda.io/projects/conda/en/latest/user-guide/cheatsheet.html)
- [Python 3.12 Release Notes](https://docs.python.org/3.12/whatsnew/3.12.html)
- [Managing Conda Environments](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)

## Getting Help

If you encounter issues:
1. Check this guide's Troubleshooting section
2. Search existing GitHub issues
3. Ask in the team chat
4. Create a new GitHub issue with details

---

**Remember:** Everyone on the team should use Python 3.12 via Conda for consistency!
