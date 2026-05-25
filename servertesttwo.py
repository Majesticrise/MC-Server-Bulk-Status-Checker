import argparse
import asyncio
import re
import time
import unicodedata
from typing import Dict, List, Optional, Tuple

from mcstatus import JavaServer


def sanitize_file_path(file_path: str) -> str:
    """移除路径中的不可见控制字符，避免 open() 报 Invalid argument。"""
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


def visible_length(s: str) -> int:
    cleaned = re.sub(r'\033\[[0-9;]*m', '', s)
    return len(cleaned)


def print_table(results: List[Dict]):
    headers = ['IP:Port', '联通', '正版', '服务端类型', '版本', 'MOTD', '在线人数']
    col_widths = [len(h) for h in headers]

    for res in results:
        addr = res['address']
        reachable = '是' if res['reachable'] else '否'
        online_mode = '是' if res['online_mode'] is True else ('否' if res['online_mode'] is False else '未知')
        server_type = res['server_type']
        server_version = res.get('server_version', 'N/A')
        motd = res.get('motd', '')
        if not motd:
            motd_display = '-'
        elif visible_length(motd) > 50:
            motd_display = motd[:80] + '\033[0m...'
        else:
            motd_display = motd
        players = f"{res['players_online']}/{res['players_max']}" if res['reachable'] else 'N/A'

        col_widths[0] = max(col_widths[0], len(addr))
        col_widths[1] = max(col_widths[1], len(reachable))
        col_widths[2] = max(col_widths[2], len(online_mode))
        col_widths[3] = max(col_widths[3], len(server_type))
        col_widths[4] = max(col_widths[4], len(server_version))
        col_widths[5] = max(col_widths[5], visible_length(motd_display))
        col_widths[6] = max(col_widths[6], len(players))

    col_widths = [w + 2 for w in col_widths]

    def print_separator():
        print('+' + '+'.join('-' * w for w in col_widths) + '+')

    def print_row(row_data):
        cells = []
        for i, cell in enumerate(row_data):
            if i == 5:
                padding = col_widths[i] - visible_length(cell) - 2
                if padding < 0:
                    padding = 0
                cells.append(f' {cell}{" " * padding} ')
            else:
                cells.append(f' {str(cell):<{col_widths[i]-2}} ')
        print('| ' + '|'.join(cells) + '|')

    print_separator()
    print_row(headers)
    print_separator()

    for res in results:
        addr = res['address']
        reachable = '是' if res['reachable'] else '否'
        online_mode = '是' if res['online_mode'] is True else ('否' if res['online_mode'] is False else '未知')
        server_type = res['server_type']
        server_version = res.get('server_version', 'N/A')
        motd = res.get('motd', '')
        if not motd:
            motd_display = '-'
        elif visible_length(motd) > 50:
            motd_display = motd[:80] + '\033[0m...'
        else:
            motd_display = motd
        players = f"{res['players_online']}/{res['players_max']}" if res['reachable'] else 'N/A'

        print_row([addr, reachable, online_mode, server_type, server_version, motd_display, players])

    print_separator()


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


async def run_scan_async(servers, timeout, debug, inter_check_delay, task_timeout, workers):
    sem = asyncio.Semaphore(workers)

    async def run_one(host, port):
        async with sem:
            try:
                return await asyncio.wait_for(
                    check_server_async(host, port, timeout, debug, inter_check_delay),
                    timeout=task_timeout,
                )
            except asyncio.TimeoutError:
                print(f'[超时] {host}:{port} 超过 {task_timeout} 秒，跳过')
                return make_failure_result(f'{host}:{port}')
            except Exception:
                return make_failure_result(f'{host}:{port}')

    tasks = [asyncio.create_task(run_one(host, port)) for host, port in servers]
    results = []
    for task in asyncio.as_completed(tasks):
        results.append(await task)
    return results


async def retry_failed_async(failed_servers, timeout, debug, inter_check_delay, task_timeout, workers, existing_results):
    if not failed_servers:
        return existing_results

    results = existing_results
    sem = asyncio.Semaphore(workers)

    async def run_retry(addr):
        async with sem:
            host, port = parse_address(addr)
            try:
                new_res = await asyncio.wait_for(
                    check_server_async(host, port, timeout, debug, inter_check_delay),
                    timeout=task_timeout,
                )
                return addr, new_res
            except asyncio.TimeoutError:
                print(f'[超时] {addr} 超过 {task_timeout} 秒，重试跳过')
                return addr, None
            except Exception:
                return addr, None

    # 创建任务，每个任务返回 (address, result)
    tasks = [asyncio.create_task(run_retry(addr)) for addr, _ in failed_servers]

    # 使用 as_completed 处理完成的任务
    for coro in asyncio.as_completed(tasks):
        addr, new_res = await coro
        if new_res is not None:
            # 更新结果列表
            for i, res in enumerate(results):
                if res['address'] == addr:
                    results[i] = new_res
                    break

    return results


async def async_main():
    parser = argparse.ArgumentParser(description='检测 Minecraft 服务器状态')
    parser.add_argument('file', nargs='?', help='包含服务器地址的文本文件 (每行 IP:端口 或 IP 端口)')
    parser.add_argument('--timeout', type=float, default=3.0, help='连接超时时间（秒）')
    parser.add_argument('--task-timeout', type=float, default=10.0, help='单个任务等待超时时间（秒）')
    parser.add_argument('--workers', type=int, default=12, help='并发任务数')
    parser.add_argument('--debug', action='store_true', help='打印调试信息')
    parser.add_argument('--inter-check-delay', type=float, default=0.2, help='每个检测阶段之间的延迟（秒）')
    args = parser.parse_args()

    if not args.file:
        args.file = input('请输入服务器列表 TXT 路径（直接回车退出）：')

    args.file = sanitize_file_path(args.file)
    if not args.file:
        print('未提供服务器列表路径')
        return

    try:
        servers = parse_servers_file(args.file)
    except FileNotFoundError:
        print(f"错误: 文件 '{args.file}' 不存在")
        return

    if not servers:
        print('没有找到有效的服务器地址')
        return

    print(f'正在检测 {len(servers)} 个服务器...\n')

    results = await run_scan_async(
        servers,
        timeout=args.timeout,
        debug=args.debug,
        inter_check_delay=args.inter_check_delay,
        task_timeout=args.task_timeout,
        workers=args.workers,
    )

    order = {f'{h}:{p}': idx for idx, (h, p) in enumerate(servers)}
    results.sort(key=lambda x: order[x['address']])
    print_table(results)

    failed_servers = [(res['address'], res) for res in results if not res['reachable']]
    retry_round = 1
    while failed_servers:
        print(f'\n第 {retry_round} 次重试：还有 {len(failed_servers)} 个服务器连通失败。')
        answer = input('是否重新检测这些失败的服务器？(y/N): ').strip().lower()
        if answer not in ('y', 'yes'):
            break

        print('正在重新检测失败的服务器...')
        results = await retry_failed_async(
            failed_servers,
            timeout=args.timeout,
            debug=args.debug,
            inter_check_delay=args.inter_check_delay,
            task_timeout=args.task_timeout,
            workers=args.workers,
            existing_results=results,
        )

        failed_servers = [(res['address'], res) for res in results if not res['reachable']]
        retry_round += 1

    if retry_round > 1:
        print('\n最终结果：')
        print_table(results)


def main():
    asyncio.run(async_main())


if __name__ == '__main__':
    main()
