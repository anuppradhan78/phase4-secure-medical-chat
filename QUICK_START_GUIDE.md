# 🚀 Quick Start Guide - Phase 4 Secure Medical Chat

## 📋 What You Need to Know

The project has been **reorganized for better navigation**. Here's where to find everything:

## 🎯 **I Want to Try the System**

### Option 1: Web Interface (Recommended)
```bash
# 1. Start the server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 2. Open in browser
open demos/web/streaming_demo.html
```

### Option 2: Command Line
```bash
# Interactive CLI demo
python demos/cli/demo_cli.py --interactive --role patient
```

### Option 3: Jupyter Notebook
```bash
# Install Jupyter and run notebook
pip install jupyter
jupyter notebook demos/notebook/demo_notebook.ipynb
```

## 📚 **I Want to Learn About the System**

- **📖 Main Documentation**: `README.md`
- **🏗️ Project Structure**: `DIRECTORY_STRUCTURE.md`
- **🔒 Security Details**: `docs/SECURITY_GUIDE.md`
- **🚀 Deployment**: `docs/DEPLOYMENT_GUIDE.md`
- **🔧 API Reference**: `docs/API_REFERENCE.md`

## 👨‍💻 **I Want to Develop/Modify**

- **📁 Source Code**: `src/` directory
- **🧪 Run Tests**: `python -m pytest tests/`
- **🔧 Configuration**: `config/` directory
- **📊 Examples**: `examples/` directory

## 🛠️ **I Want to Validate/Debug**

- **✅ Run Security Tests**: `python scripts/run_security_tests.py`
- **🔍 Validation Scripts**: `scripts/validation/`
- **🐛 Debug Tools**: `development/debug/`
- **📊 Test Results**: `data/reports/`

## 📁 **Quick Directory Reference**

| What You Want | Where to Look |
|---------------|---------------|
| **Try the system** | `demos/` |
| **Learn about it** | `docs/` |
| **See examples** | `examples/` |
| **Modify code** | `src/` |
| **Run tests** | `tests/` |
| **Use scripts** | `scripts/` |
| **Check data** | `data/` |
| **Debug issues** | `development/` |

## 🎯 **Common Tasks**

### Start the System
```bash
cd phase4-secure-medical-chat
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Security Validation
```bash
python scripts/run_security_tests.py
```

### Try Different Demos
```bash
# Web UI
open demos/web/streaming_demo.html

# CLI
python demos/cli/demo_cli.py --interactive

# Comprehensive demo
python demos/comprehensive_demo.py
```

### Check System Health
```bash
curl http://localhost:8000/health
```

## 🆘 **Need Help?**

- **🔧 Common Issues**: `docs/TROUBLESHOOTING.md`
- **📋 Full Documentation**: `DOCUMENTATION_INDEX.md`
- **🏗️ Project Structure**: `DIRECTORY_STRUCTURE.md`

---

**The system is now organized and ready to use! 🎉**