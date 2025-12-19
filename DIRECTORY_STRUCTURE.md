# Phase 4 Secure Medical Chat - Directory Structure

This document describes the organized directory structure of the Phase 4 Secure Medical Chat project.

## 📁 Root Directory (Essential Files Only)

```
phase4-secure-medical-chat/
├── README.md                    # Main project documentation
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment configuration template
├── .env                         # Environment configuration (gitignored)
├── .gitignore                   # Git ignore rules
├── DOCUMENTATION_INDEX.md       # Complete documentation navigation
├── FINAL_CHECKPOINT_SUMMARY.md  # Project completion status
└── DIRECTORY_STRUCTURE.md       # This file
```

## 📁 Core Directories

### `src/` - Source Code
- **Purpose**: Main application source code
- **Contents**: FastAPI application, security pipeline, models, services
- **Key Files**: `main.py`, `chat_service.py`, `security/`, `models/`

### `config/` - Configuration Files
- **Purpose**: Application configuration files
- **Contents**: Guardrails config, environment-specific settings
- **Key Files**: `guardrails/`, environment configs

### `tests/` - Unit Tests
- **Purpose**: Automated test suite
- **Contents**: Unit tests, integration tests, test fixtures
- **Key Files**: `test_*.py`, `conftest.py`

### `docs/` - Documentation
- **Purpose**: Comprehensive project documentation
- **Contents**: API docs, security guides, deployment guides
- **Key Files**: 
  - `API_REFERENCE.md` - Complete API documentation
  - `SECURITY_GUIDE.md` - Security implementation details
  - `DEPLOYMENT_GUIDE.md` - Production deployment guide
  - `TROUBLESHOOTING.md` - Common issues and solutions
  - `RED_TEAM_TESTING_RESULTS.md` - Security validation results

## 📁 User-Facing Directories

### `demos/` - Demonstration Interfaces
- **Purpose**: Interactive demonstrations of system capabilities
- **Structure**:
  ```
  demos/
  ├── web/
  │   └── streaming_demo.html      # Web-based streaming UI
  ├── cli/
  │   ├── demo_cli.py              # Command-line interface
  │   ├── demo_*.py                # Specific feature demos
  │   └── interactive_demo.py      # Interactive demonstrations
  ├── notebook/
  │   ├── demo_notebook.ipynb      # Jupyter notebook demo
  │   └── demo_requirements.txt    # Demo-specific dependencies
  ├── comprehensive_demo.py        # Main demonstration script
  └── demo_streaming.py            # Streaming demo utilities
  ```

### `examples/` - Code Examples
- **Purpose**: Example implementations and usage patterns
- **Contents**: Feature-specific examples, integration patterns
- **Key Files**: `pii_redaction_demo.py`, `guardrails_demo.py`, `rbac_demo.py`

### `scripts/` - Utility Scripts
- **Purpose**: Operational and maintenance scripts
- **Structure**:
  ```
  scripts/
  ├── manage_db.py                 # Database management
  ├── security_check.py            # Security validation
  ├── run_security_tests.py        # Security test runner
  └── validation/
      ├── final_checkpoint_verification.py
      ├── final_checkpoint_simple.py
      └── config_validation.py
  ```

## 📁 Data Directories

### `data/` - Data Files
- **Purpose**: Application data, logs, and generated reports
- **Structure**:
  ```
  data/
  ├── databases/
  │   ├── secure_medical_chat.db   # Main application database
  │   └── demo_database.db         # Demo/testing database
  ├── logs/
  │   └── *.log                    # Application and demo logs
  └── reports/
      ├── final_checkpoint_report.json
      └── config_validation_results.json
  ```

## 📁 Development Directories

### `development/` - Development Artifacts
- **Purpose**: Development tools, debugging, and temporary files
- **Structure**:
  ```
  development/
  ├── debug/
  │   ├── debug_guardrails.py      # Guardrails debugging
  │   ├── debug_test.py            # General debugging
  │   └── quick_test.py            # Quick testing scripts
  ├── testing/
  │   ├── test_*.py                # Ad-hoc test files
  │   └── task_validation/
  │       └── task14_validation.py
  └── task_summaries/
      ├── TASK_9_IMPLEMENTATION_SUMMARY.md
      ├── TASK_11_IMPLEMENTATION_SUMMARY.md
      ├── TASK_12_LATENCY_OPTIMIZATION_SUMMARY.md
      └── TASK_13_SECURITY_TESTING_SUMMARY.md
  ```

### `archive/` - Archived Files
- **Purpose**: Legacy files and deprecated code
- **Contents**: Files that might be needed later but are not actively used

## 🚀 Quick Navigation

### For Users:
- **Get Started**: `README.md`
- **Try the System**: `demos/web/streaming_demo.html`
- **Learn More**: `docs/` directory
- **See Examples**: `examples/` directory

### For Developers:
- **Source Code**: `src/` directory
- **Run Tests**: `tests/` directory
- **Configuration**: `config/` directory
- **Development Tools**: `development/` directory

### For Operators:
- **Deployment**: `docs/DEPLOYMENT_GUIDE.md`
- **Configuration**: `docs/CONFIGURATION_REFERENCE.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`
- **Scripts**: `scripts/` directory

## 📊 Benefits of This Structure

✅ **Clean Root Directory**: Only 7 essential files in root  
✅ **Logical Organization**: Related files grouped together  
✅ **User-Friendly**: Clear separation of user vs developer content  
✅ **Professional**: Industry-standard directory structure  
✅ **Maintainable**: Easy to add new files in appropriate locations  
✅ **Scalable**: Structure supports project growth  

## 🔄 Migration Notes

This structure was reorganized from a cluttered 50+ file root directory to improve:
- **Navigation**: Easier to find relevant files
- **Maintenance**: Clear ownership and purpose for each directory
- **Onboarding**: New users can quickly understand the project layout
- **Professional Appearance**: Clean, organized structure

---

**Last Updated**: December 18, 2024  
**Structure Version**: 2.0.0