---
name: "gbox_game"
description: "Provides real-time control and communication with running GBox game instances. Invoke when user needs to control a running GBox game, check game status, or execute game operations."
---

# GBox Game Skill

This skill provides real-time control and communication with running GBox game instances through TCP connection, allowing AI assistants to dynamically discover and call game functions.

## When to Invoke

Invoke this skill when:
- User needs to control a running GBox game instance
- User wants to check game status or perform game operations
- User asks about controlling GBox games through AI
- User needs to execute functions in a GBox game
- User wants to monitor game state changes

## Available Tools

### 1. Real-time Game Control
- **Function**: Control running GBox game instances through TCP connection
- **Features**: Dynamic tool discovery, real-time function invocation, state monitoring, intelligent control
- **Use case**: When user needs to interact with and control a running GBox game

### 2. TCP Communication
- **Function**: Establish and manage TCP connections with GBox game instances
- **Features**: UTF-16 encoding support, automatic reconnection, error handling, logging
- **Use case**: When user needs to communicate with a GBox game over network

### 3. Dynamic Tool Discovery
- **Function**: Automatically discover available tools and functions in the game
- **Features**: Real-time tool registration, MCP integration, tool change notification
- **Use case**: When user wants to explore available functions in a GBox game

## Usage Examples

### Example 1: Listing Available Tools
```
请列出当前游戏中可用的所有工具
```

### Example 2: Controlling Game Objects
```
请移动角色到坐标 (100, 200)
```

### Example 3: Checking Game Status
```
请获取当前关卡的所有敌人列表
```

### Example 4: Executing Game Operations
```
请暂停游戏并保存当前进度
```

## Project Structure

```
gbox_game/
├── SKILL.md              # Skill definition file
├── gbox_tcp.py           # TCP communication core class
├── logger.py             # Logging module
├── gbox_mcp_client.gb    # GBox client script
└── requirements.txt      # Python dependencies
```

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the skill with GBox game connection:
   ```bash
   python gbox_tcp.py --gbox_ip 127.0.0.1:30080
   ```

## Technical Features

- **Self-contained**: All files and resources are included in the directory
- **Relative paths**: All file references use relative paths
- **Standard dependencies**: Only depends on standard Python packages
- **Complete functionality**: Includes all necessary files and modules
- **Ready to use**: Can be directly installed as a trae skill

## TCP Communication Protocol

- **Encoding**: UTF-16LE (Unicode)
- **Message format**: JSON strings ending with \r\n
## Connection Management

- Automatic reconnection when connection is lost
- Heartbeat detection for connection status
- Thread-based asynchronous message handling
- Comprehensive error handling and logging