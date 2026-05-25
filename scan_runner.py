import asyncio
from checker import check_server_async
from utils import make_failure_result, parse_address


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
