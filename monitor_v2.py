"""监控 v2 干跑日志，提取关键指标"""
import os, re, glob, datetime

LOG_DIR = '/tmp'
LOG_PATTERN = 'v2_dryrun_60_*.log'

def find_latest_log():
    logs = sorted(glob.glob(os.path.join(LOG_DIR, LOG_PATTERN)), key=os.path.getmtime, reverse=True)
    return logs[0] if logs else None

def parse_summary(log_file):
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
    except:
        return None

    # 寻找最新 Summary 块
    summary_start = None
    for i in range(len(lines)-1, -1, -1):
        if '--- Summary ---' in lines[i]:
            summary_start = i
            break
    if summary_start is None:
        return None

    summary_lines = lines[summary_start:summary_start+10]
    result = {
        'timestamp': lines[summary_start-1].strip() if summary_start>0 else 'unknown',
        'equity': None,
        'closed': None,
        'new_entries': None,
        'pnls': []
    }
    for line in summary_lines:
        if 'Equity:' in line:
            m = re.search(r'Equity: \$([0-9,]+\.?[0-9]*)', line)
            if m:
                result['equity'] = float(m.group(1).replace(',',''))
        if 'Closed:' in line:
            m = re.search(r'Closed: (\d+)', line)
            if m:
                result['closed'] = int(m.group(1))
        if 'New entries:' in line:
            m = re.search(r'New entries: (\d+)', line)
            if m:
                result['new_entries'] = int(m.group(1))
        if line.strip().startswith('  ') and ':' in line and '$' in line:
            # 例: "  BTC/USDT: $+12.34"
            result['pnls'].append(line.strip())
    return result

if __name__ == '__main__':
    latest = find_latest_log()
    if not latest:
        print("No log found")
        exit(1)
    print(f"Latest log: {os.path.basename(latest)}")
    summary = parse_summary(latest)
    if not summary:
        print("No summary parsed yet")
        exit(0)
    print(f"Time: {summary['timestamp']}")
    print(f"Equity: ${summary['equity']:.2f}" if summary['equity'] else "Equity: N/A")
    print(f"Closed trades: {summary['closed']}")
    print(f"New entries: {summary['new_entries']}")
    if summary['pnls']:
        print("\nRecent PnLs:")
        for p in summary['pnls'][-5:]:
            print(p)
