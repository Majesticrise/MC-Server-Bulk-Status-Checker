import re
import unicodedata
from typing import List, Tuple, Dict
import nbtlib
from pathlib import Path

def sanitize_file_path(file_path: str) -> str:
    cleaned = ''.join(ch for ch in file_path if unicodedata.category(ch)[0] != 'C')
    return cleaned.strip()


def parse_servers_file(file_path: str) -> List[Tuple[str, int]]:
    """解析服务器列表文件，每行格式: IP:端口 或 IP 端口，端口默认 25565"""
    file_path = sanitize_file_path(file_path)
    servers = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                parts = line.split(':')
                host = parts[0].strip()
                try:
                    port = int(parts[1].strip())
                except ValueError:
                    continue
            else:
                parts = line.split()
                host = parts[0].strip()
                port = 25565
                if len(parts) > 1:
                    try:
                        port = int(parts[1].strip())
                    except ValueError:
                        pass
            servers.append((host, port))
    return servers

def parse_server_type(version_name: str) -> str:
    if not version_name:
        return "N/A"

    patterns = [
        (r'(?i)(?:\[|^)(paper)(?:\]|$|\s)', 'Paper'),
        (r'(?i)(?:\[|^)(spigot)(?:\]|$|\s)', 'Spigot'),
        (r'(?i)(?:\[|^)(purpur)(?:\]|$|\s)', 'Purpur'),
        (r'(?i)(?:\[|^)(fabric)(?:\]|$|\s)', 'Fabric'),
        (r'(?i)(?:\[|^)(forge)(?:\]|$|\s)', 'Forge'),
        (r'(?i)(?:\[|^)(vanilla)(?:\]|$|\s)', 'Vanilla'),
        (r'(?i)(?:\[|^)(bukkit)(?:\]|$|\s)', 'Bukkit'),
        (r'(?i)(?:\[|^)(cauldron)(?:\]|$|\s)', 'Cauldron'),
        (r'(?i)(?:\[|^)(thermos)(?:\]|$|\s)', 'Thermos'),
        (r'(?i)(?:\[|^)(arclight)(?:\]|$|\s)', 'Arclight'),
        (r'(?i)(?:\[|^)(mohist)(?:\]|$|\s)', 'Mohist'),
        (r'(?i)(?:\[|^)(catserver)(?:\]|$|\s)', 'CatServer'),
        (r'(?i)(?:\[|^)(bungeecord)(?:\]|$|\s)', 'BungeeCord'),
        (r'(?i)(?:\[|^)(velocity)(?:\]|$|\s)', 'Velocity'),
        (r'(?i)(?:\[|^)(waterfall)(?:\]|$|\s)', 'Waterfall'),
        (r'(?i)(?:\[|^)(travertine)(?:\]|$|\s)', 'Travertine'),
        (r'(?i)(?:\[|^)(flamecord)(?:\]|$|\s)', 'FlameCord'),
        (r'(?i)(?:\[|^)(lightfall)(?:\]|$|\s)', 'Lightfall'),
        (r'(?i)(?:\[|^)(leaves)(?:\]|$|\s)', 'Leaves'),
        (r'(?i)(?:\[|^)(pufferfish)(?:\]|$|\s)', 'Pufferfish'),
        (r'(?i)(?:\[|^)(tuinity)(?:\]|$|\s)', 'Tuinity'),
        (r'(?i)(?:\[|^)(yatopia)(?:\]|$|\s)', 'Yatopia'),
        (r'(?i)(?:\[|^)(akarin)(?:\]|$|\s)', 'Akarin'),
        (r'(?i)(?:\[|^)(kcauldron)(?:\]|$|\s)', 'KCauldron'),
        (r'(?i)(?:\[|^)(uranium)(?:\]|$|\s)', 'Uranium'),
        (r'(?i)(?:\[|^)(glowstone)(?:\]|$|\s)', 'Glowstone'),
        (r'(?i)(?:\[|^)(cuberite)(?:\]|$|\s)', 'Cuberite'),
    ]

    for pattern, server_type in patterns:
        if re.search(pattern, version_name):
            return server_type

    lower_name = version_name.lower()
    if 'fml' in lower_name or 'modded' in lower_name or 'forge' in lower_name:
        return 'Forge'
    if 'fabric' in lower_name:
        return 'Fabric'
    return 'Vanilla'

def extract_version(version_name: str) -> str:
    if not version_name:
        return 'N/A'
    match = re.search(r'\b(\d+\.\d+(?:\.\d+)?)\b', version_name)
    if match:
        return match.group(1)
    return '未知'

def extract_motd_text(description) -> str:
    if not description:
        return ''

    if isinstance(description, str):
        text = description
    elif isinstance(description, dict):
        if 'extra' in description:
            parts = []
            for part in description['extra']:
                if isinstance(part, dict):
                    parts.append(part.get('text', ''))
                else:
                    parts.append(str(part))
            if 'text' in description:
                parts.insert(0, description['text'])
            text = ''.join(parts)
        elif 'text' in description:
            text = description['text']
        else:
            text = ''
    else:
        text = str(description)

    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    text = re.sub(r'\s+', ' ', text).strip()

    color_map = {
        '0': '\033[30m', '1': '\033[34m', '2': '\033[32m', '3': '\033[36m',
        '4': '\033[31m', '5': '\033[35m', '6': '\033[33m', '7': '\033[37m',
        '8': '\033[90m', '9': '\033[94m', 'a': '\033[92m', 'b': '\033[96m',
        'c': '\033[91m', 'd': '\033[95m', 'e': '\033[93m', 'f': '\033[97m',
        'l': '\033[1m', 'm': '\033[9m', 'n': '\033[4m', 'o': '\033[3m',
        'r': '\033[0m'
    }

    def replace_color(match):
        code = match.group(1)
        return color_map.get(code, '')

    text = re.sub(r'§([0-9a-fk-or])', replace_color, text, flags=re.IGNORECASE)
    text += '\033[0m'
    return text


def visible_length(s: str) -> int:
    cleaned = re.sub(r'\033\[[0-9;]*m', '', s)
    return len(cleaned)


def make_failure_result(address: str) -> Dict:
    return {
        'address': address,
        'reachable': False,
        'online_mode': None,
        'server_type': 'N/A',
        'server_version': 'N/A',
        'players_online': 'N/A',
        'players_max': 'N/A',
        'motd': 'N/A'
    }

def parse_address(address: str) -> Tuple[str, int]:
    if ':' in address:
        host, port_part = address.rsplit(':', 1)
        return host, int(port_part)
    return address, 25565

def parse_servers_file_dat(file_path: str) -> List[Tuple[str, int]]:
    """
    解析 Minecraft 的 servers.dat 文件（NBT 格式），返回服务器列表。
    每项为 (host, port)，host 可以是域名或 IP。
    """
    servers = []
    dat_path = Path(file_path)
    if not dat_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    try:
        data = nbtlib.load(dat_path)
        servers_nbt = data.get("servers")
        
        # 确保 servers_nbt 是一个可迭代对象（列表或类似）
        if servers_nbt is None:
            return []  # 没有服务器数据，返回空列表
        
        for server in servers_nbt:
            # 获取 IP/地址
            ip = server.get("ip", "")
            # 获取端口（如果单独存储）
            port = server.get("port", 25565)
            
            if not ip:
                continue
            
            # 如果 ip 字段已经包含端口（例如 "mc.hypixel.net:25565"），则解析
            if ":" in ip:
                host, port_str = ip.rsplit(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    port = 25565
                host = host
            else:
                host = ip
            
            servers.append((host, port))
        return servers
    except Exception as e:
        raise RuntimeError(f"解析 servers.dat 失败: {e}")