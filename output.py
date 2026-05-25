from typing import List, Dict
from utils import visible_length



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

