import argparse
import asyncio
from utils import parse_servers_file, sanitize_file_path
from scan_runner import run_scan_async, retry_failed_async
from output import print_table


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
