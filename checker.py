import asyncio
from typing import Dict, Optional
from mcstatus import JavaServer
from utils import parse_server_type, extract_version, extract_motd_text

async def get_server_status_async(host: str, port: int, timeout: float = 3.0, debug: bool = False) -> Optional[Dict]:
    try:
        if debug:
            print(f"[DEBUG] {host}:{port} 正在解析地址...")
        server = await JavaServer.async_lookup(f"{host}:{port}", timeout=timeout)
        if debug:
            print(f"[DEBUG] {host}:{port} 连接成功，请求状态...")
        status_response = await server.async_status()
        raw = getattr(status_response, 'raw', None)
        if raw is None:
            raw = status_response
        if not isinstance(raw, dict):
            if debug:
                print(f"[DEBUG] {host}:{port} raw 不是 dict: {type(raw)}")
            return None
        version = raw.get('version') or {}
        players = raw.get('players') or {}
        if debug:
            print(f"[DEBUG] {host}:{port} version.name = {version.get('name')}, protocol = {version.get('protocol')}")
            print(f"[DEBUG] {host}:{port} enforcesSecureChat = {raw.get('enforcesSecureChat')}")
        return {
            'version': {
                'name': version.get('name', 'Unknown') if isinstance(version, dict) else 'Unknown',
                'protocol': version.get('protocol') if isinstance(version, dict) else None,
            },
            'players': {
                'online': players.get('online', '?') if isinstance(players, dict) else '?',
                'max': players.get('max', '?') if isinstance(players, dict) else '?',
            },
            'description': raw.get('description'),
            'enforcesSecureChat': raw.get('enforcesSecureChat'),
            'raw': raw,   # 新增：保存原始数据用于服务端类型识别
        }
    except Exception as e:
        if debug:
            print(f"[DEBUG] {host}:{port} 异常: {type(e).__name__}: {e}")
        else:
            # 非 debug 模式下也打印简洁错误（可选）
            print(f"[连接失败] {host}:{port} - {type(e).__name__}: {e}")
        return None
    
def parse_server_type_from_raw(version_name: str, raw: dict) -> str:
    """
    根据原始 status raw 数据更准确地判断服务端类型
    """
    if not raw:
        return parse_server_type(version_name)

    # 1. 检测模组加载器
    if raw.get('modinfo') or raw.get('forgeData'):
        return 'Forge'
    if raw.get('fabricMetadata'):
        return 'Fabric'

    # 2. 检测代理端（常见特征：没有玩家样例，且 enforceSecureChat 存在）
    if raw.get('enforcesSecureChat') is not None and raw.get('players', {}).get('sample') is None:
        # 可进一步判断品牌
        raw_str = str(raw).lower()
        if 'bungeecord' in raw_str:
            return 'BungeeCord'
        if 'velocity' in raw_str:
            return 'Velocity'
        if 'waterfall' in raw_str:
            return 'Waterfall'

    # 3. 回退到原有基于 version.name 的匹配
    return parse_server_type(version_name)

async def check_server_async(
    host: str,
    port: int,
    timeout: float = 4.0,
    debug: bool = False,
    inter_check_delay: float = 0.2,
) -> Dict:
    result = {
        'address': f'{host}:{port}',
        'reachable': False,
        'online_mode': None,
        'server_type': 'N/A',
        'server_version': 'N/A',
        'players_online': 'N/A',
        'players_max': 'N/A',
        'motd': 'N/A'
    }

    status = await get_server_status_async(host, port, timeout, debug=debug)
    if status is None:
        if debug:
            print(f"[DEBUG] {host}:{port} 状态获取失败，标记为不可达")
        return result

    result['reachable'] = True
    version_name = status['version'].get('name', 'Unknown')
    raw_data = status.get('raw', {})
    result['server_type'] = parse_server_type_from_raw(version_name, raw_data)
    result['server_version'] = extract_version(version_name)

    if debug:
        print(f"[DEBUG] {host}:{port} 服务端类型: {result['server_type']}, 版本: {result['server_version']}")

    await asyncio.sleep(inter_check_delay)

    players = status.get('players', {})
    result['players_online'] = str(players.get('online', '?'))
    result['players_max'] = str(players.get('max', '?'))
    result['motd'] = extract_motd_text(status.get('description'))

    await asyncio.sleep(inter_check_delay)
    result['online_mode'] = status.get('enforcesSecureChat')
    if debug:
        print(f"[DEBUG] {host}:{port} 正版验证: {result['online_mode']}")
    return result


