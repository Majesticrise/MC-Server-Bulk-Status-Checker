import argparse
import asyncio
import os
from utils import parse_servers_file, parse_servers_file_dat, sanitize_file_path, make_failure_result, parse_address
from scan_runner import run_scan_async, retry_failed_async
from output import print_table


async def async_main():
    parser = argparse.ArgumentParser(description='检测 Minecraft 服务器状态')
    parser.add_argument('file', nargs='?', help='服务器列表文件路径（支持 .txt 或 .dat）')
    parser.add_argument('--type', choices=['txt', 'dat'], help='指定文件类型，不指定时根据扩展名自动判断')
    parser.add_argument('--timeout', type=float, default=3.0, help='连接超时时间（秒）')
    parser.add_argument('--task-timeout', type=float, default=10.0, help='单个任务等待超时时间（秒）')
    parser.add_argument('--workers', type=int, default=12, help='并发任务数')
    parser.add_argument('--debug', action='store_true', help='打印调试信息')
    parser.add_argument('--inter-check-delay', type=float, default=0.2, help='每个检测阶段之间的延迟（秒）')
    args = parser.parse_args()

    # 交互模式：如果没有提供文件路径，则询问文件类型和路径
    if not args.file:
        print("请选择输入文件类型：")
        print("1) 文本文件 (.txt)")
        print("2) Minecraft servers.dat 文件 (.dat)")
        choice = input("请输入 1 或 2: ").strip()
        if choice == '1':
            args.type = 'txt'
            args.file = input("请输入 txt 文件路径: ").strip()
        elif choice == '2':
            args.type = 'dat'
            args.file = input("请输入 dat 文件路径: ").strip()
        else:
            print("无效选择，退出")
            return

    # 清洗文件路径
    args.file = sanitize_file_path(args.file)
    if not args.file:
        print('未提供服务器列表路径')
        return

    # 自动判断文件类型（如果未通过 --type 指定）
    if not args.type:
        if args.file.lower().endswith('.dat'):
            args.type = 'dat'
        else:
            args.type = 'txt'

    # 解析服务器列表
    try:
        if args.type == 'txt':
            servers = parse_servers_file(args.file)
        elif args.type == 'dat':
            # 需要安装 nbtlib 库: pip install nbtlib
            servers = parse_servers_file_dat(args.file)
        else:
            print(f"不支持的文件类型: {args.type}")
            return
    except FileNotFoundError:
        print(f"错误: 文件 '{args.file}' 不存在")
        return
    except ImportError:
        print("错误: 解析 dat 文件需要安装 nbtlib，请运行: pip install nbtlib")
        return
    except Exception as e:
        print(f"解析文件失败: {e}")
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

    # 保持原始顺序排序
    order = {f'{h}:{p}': idx for idx, (h, p) in enumerate(servers)}
    results.sort(key=lambda x: order[x['address']])
    print_table(results)

    # 重试失败的服务器
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