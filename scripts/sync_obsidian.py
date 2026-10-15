"""Render a local CSV ledger into Obsidian notes; never change the source ledger."""
import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def money(value):
    amount = Decimal(str(value))
    if not amount.is_finite() or amount != amount.quantize(Decimal('.01')):
        raise ValueError('金额须为有限数值，最多两位小数。')
    return amount


def cash_balance(actual, config, as_of):
    baseline = config.get('cash_baseline', {})
    if not baseline.get('confirmed') or baseline.get('amount') is None or not baseline.get('as_of'):
        return None, '现金起点待确认'
    start = date.fromisoformat(baseline['as_of'][:10])
    if start > as_of:
        return None, '现金起点晚于本次报告日期'
    balance = money(baseline['amount'])
    included = set(baseline.get('included_transaction_ids', []))
    deltas = config.get('cash_delta_by_id', {})
    for row, day, amount, kind in actual:
        tid = row['交易ID']
        if tid in included or day < start:
            continue
        if tid in deltas:
            balance += money(deltas[tid])
        elif kind == '收入':
            balance += amount
        elif kind in ('支出', '费用'):
            balance -= amount
        elif kind == '转账':
            continue  # Own-account transfers do not change aggregate cash.
        else:
            return None, f'{tid}的现金变动方向待确认'
    return balance, '按已确认起点和已登记新收支推算，尚需实际对账'


def sync(vault, as_of):
    vault = vault.resolve(strict=True)
    ledger = vault / '脱敏流水.csv'
    before = ledger.read_bytes()
    with ledger.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    config_path = vault / '.obsidian' / 'finance-assistant.json'
    config = json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
    aggregate = config.get('account_tracking') == 'aggregate_cash'
    state_path = vault / '.obsidian' / 'finance-assistant-state.json'
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    outputs = {}
    seen = set()
    actual = []
    for row in rows:
        tid = row['交易ID']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', tid) or tid in seen:
            raise ValueError('交易ID缺失、重复或包含不安全字符；未同步。')
        seen.add(tid)
        day = date.fromisoformat(row['日期'])
        amount = money(row['金额'])
        if amount < 0:
            raise ValueError('金额须为非负有限数值，最多两位小数；未同步。')
        kind = row['收入/支出/转账/投资本金/债务本金/利息/费用']
        metadata = {
            'transaction_id': tid, 'kind': kind, 'category': row['分类'],
            'account': row['账户别名'] or '待确认', 'currency': row['币种'],
            'actual': row['实际/预计'], 'note': row['脱敏备注'],
            'source_ledger': '脱敏流水.csv', 'integration': 'finance-assistant',
        }
        front = ['---', f'date: {day.isoformat()}', f'amount: {amount:.2f}']
        front.extend(f'{key}: {json.dumps(value, ensure_ascii=False)}' for key, value in metadata.items())
        front += ['---', '', f'# {row["脱敏备注"].split("；")[0]}', '',
                  '> 此笔记由正式流水表生成。更正请告诉财务助手，避免与原账本不一致。', '',
                  f'金额：{amount:.2f} {row["币种"]}；类别：{row["分类"]}。' +
                  ('' if aggregate else f'账户：{metadata["account"]}。'), '',
                  '[[财务首页|返回财务首页]]', '']
        outputs[f'交易明细/{tid}.md'] = '\n'.join(front)
        if row['实际/预计'] == '实际' and day <= as_of and row['币种'] == 'CNY':
            actual.append((row, day, amount, kind))
    month = [entry for entry in actual if entry[1].strftime('%Y-%m') == as_of.strftime('%Y-%m')]
    operating = []
    unresolved_interest = False
    for row, day, amount, kind in month:
        if kind == '费用':
            kind = '支出'
        elif kind == '利息':
            delta = config.get('cash_delta_by_id', {}).get(row['交易ID'])
            if delta is None or abs(money(delta)) != amount or (amount and money(delta) == 0):
                unresolved_interest = True
                continue
            kind = '收入' if money(delta) >= 0 else '支出'
        operating.append((row, day, amount, kind))
    expenses = [entry for entry in operating if entry[3] == '支出']
    today = [entry for entry in expenses if entry[1] == as_of]
    incomes = [entry for entry in operating if entry[3] == '收入']
    def total(entries):
        return sum((entry[2] for entry in entries), Decimal('0'))
    cash, cash_status = cash_balance(actual, config, as_of)
    cash_text = f'{cash:,.2f}元（推算）' if cash is not None else '待核对'
    reference = config.get('reference_cash', {})
    if cash is None and reference.get('amount') is not None:
        cash_text += f'；旧快照{money(reference["amount"]):,.2f}元仅作暂算参考'
    complete = config.get('monthly_reconciled', {}).get(as_of.strftime('%Y-%m')) is True
    complete = complete and not unresolved_interest
    net_text = f'{total(incomes)-total(expenses):,.2f}元' if complete else '待核对（本月记录不完整或利息方向未确认）'
    by_category = defaultdict(lambda: Decimal('0'))
    for row, day, amount, kind in expenses:
        by_category[row['分类']] += amount
    home = ['# 财务助手', '', f'更新日期：{as_of.isoformat()}（Asia/Shanghai）', '',
            '> 支出只汇总已登记人民币流水。现金总额与净结余的完整性单独核对，未提供的收支不当作零。', '',
            '| 已登记情况 | 金额／状态 |', '|---|---:|',
            f'| 今日支出（{len(today)}笔） | {format(total(today), ".2f") + "元" if today else "尚无记录，不代表零支出"} |',
            f'| 本月支出（{len(expenses)}笔） | {format(total(expenses), ".2f") + "元" if expenses else "尚无记录，不代表零支出"} |',
            f'| {config.get("cash_label", "现金总额")} | {cash_text} |',
            f'| 本月净结余 | {net_text} |',
            f'| 本月已登记收入 | {format(total(incomes), ".2f") + "元" if incomes else "尚无收入记录，不代表零收入"} |', '',
            '## 常用入口', '',
            '- [[随手记|在 Obsidian 留下待登记事项]]',
            '- [[private/我的财务档案|我的财务档案与余额快照]]',
            '- [[private/储蓄目标|储蓄目标]]',
            '- [[private/独立投资资产|独立投资资产]]',
            '- [[月度复盘入口|月度复盘与历史分析]]',
            '- [[Obsidian使用说明|使用说明]]', '', '## 本月已登记消费结构', '',
            '| 分类 | 金额（元） |', '|---|---:|']
    home.extend(f'| {category.replace("|", "／")} | {amount:.2f} |' for category, amount in sorted(by_category.items()))
    home += ['', '## 现金储蓄目标进度', '',
             '| 目标 | 目标金额 | 期限 | 当前现金 | 缺口 | 完成比例 |',
             '|---|---:|---|---:|---:|---:|']
    for goal in config.get('goals', []):
        target = money(goal['target'])
        if target <= 0:
            raise ValueError('储蓄目标金额必须为正数。')
        if cash is None:
            current, gap, ratio = '待核对', '待核对', '待核对'
        else:
            current, gap, ratio = f'{cash:,.2f}', f'{max(Decimal(0),target-cash):,.2f}', f'{cash/target*100:.2f}%'
        home.append(f'| {goal["name"]} | {target:,.2f}元 | {goal["due"]} | {current} | {gap} | {ratio} |')
    home += ['', '目标统计范围以用户配置为准；当前余额若含尚未支付的专项开支，比例不代表开销后已达标。全部目标使用同一余额范围。', '',
             f'现金状态：{cash_status}。起点未确认前不把既有支出再次从旧快照中扣减。', '',
             '## 流水浏览', '', '![[流水浏览.base]]', '', '## 每日记录', '']
    home.extend(f'- [[{path.relative_to(vault).as_posix()[:-3]}|{path.stem}]]' for path in sorted((vault / 'reports').glob('每日记账_*.md'), reverse=True))
    home += ['', '年费按付款日全额计入；月均金额仅作预算参考，不重复记支出。现金余额仍以档案快照和实际对账为准。', '']
    outputs['财务首页.md'] = '\n'.join(home)
    # All conflicts are checked before writing any generated note.
    for relative, content in outputs.items():
        target = vault / relative
        if target.exists() and target.read_bytes() != content.encode('utf-8'):
            if state.get(relative) != digest(target.read_bytes()):
                raise ValueError(f'{relative}有未同步的手动修改；请核对后同步，不覆盖。')
    changed = {relative: content for relative, content in outputs.items()
               if not (vault / relative).exists() or (vault / relative).read_bytes() != content.encode('utf-8')}
    if changed or not state_path.exists():
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = vault / 'backups' / f'obsidian_sync_{stamp}'
        for relative in list(changed) + ['.obsidian/finance-assistant-state.json']:
            target = vault / relative
            if target.exists():
                copy = backup / relative
                copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, copy)
        for relative, content in changed.items():
            target = vault / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode('utf-8'))
        state.update({relative: digest(content.encode('utf-8')) for relative, content in outputs.items()})
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    assert ledger.read_bytes() == before, '同步不得改变正式流水表'
    return {'transaction_count': len(rows), 'changed_files': len(changed),
            'today_expenses': str(total(today)), 'month_expenses': str(total(expenses)),
            'cash_balance': str(cash) if cash is not None else None,
            'monthly_net': str(total(incomes)-total(expenses)) if complete else None,
            'source_ledger_unchanged': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', type=Path, required=True)
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    args = parser.parse_args()
    print(json.dumps(sync(args.vault, args.as_of), ensure_ascii=False))
