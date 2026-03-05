---
name: "gbox_engine"
description: "Provides GBox game engine API documentation query and syntax guidance. Invoke when user needs GBox API information, syntax help, or wants to learn about GBox engine functionality."
---

# GBox Engine Skill

This skill provides comprehensive documentation and guidance for the GBox game engine through the Model Context Protocol (MCP).

## When to Invoke

Invoke this skill when:
- User needs information about GBox API classes, methods, or properties
- User asks for GBox scripting language syntax help
- User wants to learn about GBox engine architecture and functionality
- User is developing with GBox and needs reference documentation
- User has questions about GBox game engine features

## Available Tools

### 1. GBox API Directory Query
- **Function**: Get complete GBox API documentation directory structure
- **Content includes**: All available classes and inheritance trees, namespace hierarchy, functional module classification, quick index and navigation guide
- **Use case**: Understand overall architecture before any GBox development

### 2. API Detailed Documentation Query
- **Function**: Get detailed documentation for specified classes or namespaces
- **Content includes**: Complete method lists and inheritance relationships, detailed descriptions of method parameters and return values, property read/write permissions and data types, actual usage examples and code snippets, notes and best practice recommendations
- **Use case**: Deep learning of specific class usage methods

### 3. Syntax Guide
- **Function**: Get complete syntax rules for GBox scripting language
- **Content includes**: Basic syntax structure and rules, data types and variable declarations, control structures (conditions, loops, etc.), function definition and invocation, object-oriented programming features, error handling and debugging techniques, complete code examples
- **Use case**: Learning GBox script programming or solving syntax problems

## Usage Examples

### Example 1: Exploring GBox Architecture
```
请获取 GBox API 的完整目录结构，我想了解都有哪些功能模块
```

### Example 2: Learning Specific Functions
```
请详细介绍 GObjShape 类的所有方法和属性
```

### Example 3: Solving Syntax Problems
```
我在编写 GBox 脚本时遇到语法错误，请提供语法指导
```

## Project Structure

```
gbox_engine/
├── gbox_help.py          # Document query core class
├── logger.py             # Logging module
├── doc/                  # Document resource directory
│   ├── gbox_api.md       # GBox API complete documentation
│   ├── gbox_syntax.md    # GBox syntax detailed documentation
│   ├── gbox_example.gb   # GBox code example
│   └── ui_sys.md         # UI system special documentation
├── requirements.txt      # Python dependency definition
└── SKILL.md              # Skill definition file
```

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. The skill is now ready to use with trae

## Technical Features

- **Self-contained**: All files and resources are included in the directory
- **Relative paths**: All file references use relative paths
- **Standard dependencies**: Only depends on standard Python packages
- **Complete functionality**: Includes all necessary files and modules
- **Ready to use**: Can be directly installed as a trae skill

## Document Resources

### GBox API Documentation
- **Size**: 256KB, 3300+ lines
- **Content**: Complete API reference, including all classes, methods, properties
- **Structure**: Categorized by functional modules, supports quick navigation

### Syntax Documentation
- **Size**: 33KB, 1300+ lines
- **Content**: Complete syntax rules and programming guidelines
- **Features**: Abundant example code and best practices

### Example Code
- **Size**: 23KB, 650+ lines of actual code
- **Content**: Usage examples covering various functional modules of GBox
- **Value**: Complete examples that can be run directly