import socket
import json
import threading
import time
import argparse
import logging
import os

class GboxTcp:
    def __init__(self, gbox_ip="127.0.0.1:30080"):
        """初始化 GboxTcp 类
        
        Args:
            gbox_ip: GBox 游戏实例的 IP 和端口，格式为 "ip:port"
        """
        self.gbox_ip = gbox_ip
        self.host, self.port = gbox_ip.split(':')
        self.port = int(self.port)
        self.sock = None
        self.connected = False
        self.reconnect_interval = 5  # 重连间隔（秒）
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.heartbeat_thread = None
        self.receive_thread = None
        self.stop_event = threading.Event()
        self.logger = self._get_logger()
        
    def _get_logger(self):
        """获取 logger 实例"""
        logger = logging.getLogger('gbox_tcp')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    def connect(self):
        """连接到 GBox 游戏实例"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            self.logger.info(f"Connected to GBox game at {self.gbox_ip}")
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # 启动心跳线程
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to GBox game: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        self.stop_event.set()
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                self.logger.error(f"Error closing socket: {e}")
        self.connected = False
        self.logger.info("Disconnected from GBox game")
    
    def send_message(self, obj, name, arguments=None):
        """发送消息到 GBox 游戏
        
        Args:
            obj: 对象地址（如 "&03E3FC48:4E"）
            name: 函数名
            arguments: 参数字典
            
        Returns:
            str: 响应结果
        """
        if not self.connected:
            if not self.connect():
                return f"Error: Not connected to GBox game at {self.gbox_ip}"
        
        try:
            message = {
                "obj": obj,
                "name": name,
                "arguments": arguments or {}
            }
            
            # 编码为 UTF-16LE 并添加换行符
            message_str = json.dumps(message, ensure_ascii=False) + "\r\n"
            encoded_message = message_str.encode('utf-16le')
            
            self.sock.sendall(encoded_message)
            self.logger.info(f"Sent message: {message_str.strip()}")
            
            # 等待响应（简单实现，实际应用可能需要更复杂的异步处理）
            time.sleep(0.1)
            return "Message sent successfully"
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            self.connected = False
            return f"Error sending message: {e}"
    
    def _receive_loop(self):
        """接收消息循环"""
        while not self.stop_event.is_set():
            if not self.connected:
                time.sleep(1)
                continue
            
            try:
                # 设置超时，以便定期检查 stop_event
                self.sock.settimeout(1.0)
                data = self.sock.recv(4096)
                
                if not data:
                    self.logger.warning("Connection closed by GBox game")
                    self.connected = False
                    continue
                
                # 解码 UTF-16LE
                response = data.decode('utf-16le')
                self.logger.info(f"Received response: {response.strip()}")
                
            except socket.timeout:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                self.logger.error(f"Error receiving message: {e}")
                self.connected = False
                time.sleep(1)
    
    def _heartbeat_loop(self):
        """心跳循环"""
        while not self.stop_event.is_set():
            if self.connected:
                try:
                    # 发送心跳消息
                    self.send_message("", "ping", {})
                except Exception as e:
                    self.logger.error(f"Error sending heartbeat: {e}")
                    self.connected = False
            else:
                # 尝试重新连接
                self.logger.info(f"Attempting to reconnect to GBox game at {self.gbox_ip}...")
                self.connect()
            
            # 等待心跳间隔
            time.sleep(self.heartbeat_interval)
    
    def get_tools(self):
        """获取游戏中的工具列表
        
        Returns:
            str: 工具列表
        """
        return self.send_message("", "get_tools", {})

if __name__ == "__main__":
    # 命令行参数解析
    parser = argparse.ArgumentParser(description="GBox Game TCP Client")
    parser.add_argument('--gbox_ip', type=str, default='127.0.0.1:30080',
                      help='GBox game IP and port (default: 127.0.0.1:30080)')
    args = parser.parse_args()
    
    # 创建 GboxTcp 实例
    gbox_tcp = GboxTcp(args.gbox_ip)
    
    try:
        # 连接到游戏
        if gbox_tcp.connect():
            print(f"Connected to GBox game at {args.gbox_ip}")
            
            # 获取工具列表
            print("Getting tools...")
            tools = gbox_tcp.get_tools()
            print(f"Tools: {tools}")
            
            # 保持运行
            while True:
                time.sleep(1)
        else:
            print(f"Failed to connect to GBox game at {args.gbox_ip}")
            
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        # 断开连接
        gbox_tcp.disconnect()