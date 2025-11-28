#!/bin/bash

# Safe Evidently Drift Report Generator
# This script creates an isolated conda environment and runs Evidently
# It will NOT affect any existing environments or dependencies

echo "============================================================"
echo "SAFE EVIDENTLY DRIFT REPORT GENERATOR"
echo "============================================================"
echo ""
echo "This script will:"
echo "1. Create a temporary conda environment (evidently-env)"
echo "2. Install Evidently in that environment only"
echo "3. Generate the drift report"
echo "4. You can delete the environment later with: conda env remove -n evidently-env"
echo ""
echo "Press ENTER to continue or Ctrl+C to cancel..."
read

# Navigate to project directory
cd "/Users/asligulcur/Library/CloudStorage/OneDrive-Personal/CMU Heinz Foundations of Operationalizing AI October 2025/Crypto Volatility Real Time"

# Check if environment already exists
if conda env list | grep -q "evidently-env"; then
    echo "✅ evidently-env already exists"
else
    echo "📦 Creating evidently-env with Python 3.11..."
    conda create -n evidently-env python=3.11 -y
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create conda environment"
        exit 1
    fi
    
    echo "✅ Environment created"
fi

# Activate environment and install packages
echo "📦 Installing evidently and dependencies..."
conda run -n evidently-env pip install evidently pandas numpy

if [ $? -ne 0 ]; then
    echo "❌ Failed to install packages"
    exit 1
fi

echo "✅ Packages installed"
echo ""

# Run the drift detection script
echo "🚀 Running Evidently drift detection..."
echo ""
# Deactivate any active virtual environment first
if [[ -n "${VIRTUAL_ENV}" ]]; then
    deactivate 2>/dev/null || true
fi

conda run -n evidently-env python scripts/generate_evidently_now.py

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✅ SUCCESS! Drift report generated"
    echo "============================================================"
    echo ""
    echo "Find your report in: reports/drift/"
    echo ""
    echo "To open it:"
    echo "  open reports/drift/evidently_drift_*.html"
    echo ""
    echo "To clean up the temporary environment later:"
    echo "  conda env remove -n evidently-env -y"
    echo ""
else
    echo ""
    echo "❌ Failed to generate report"
    echo "Check the error messages above"
    exit 1
fi
