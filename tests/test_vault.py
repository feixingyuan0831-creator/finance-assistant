"""End-to-end checks use temporary, synthetic vaults only."""
import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from init_vault import init_vault
from sync_obsidian import sync


class VaultTests(unittest.TestCase):
    def test_interest_fees_and_unknown_direction(self):
        with tempfile.TemporaryDirectory() as temp:
            vault = Path(temp) / 'vault'
            init_vault(vault)
            ledger = vault / '脱敏流水.csv'
            with ledger.open(encoding='utf-8') as handle:
                fields = next(csv.reader(handle))
            with ledger.open('a', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                for tid, amount, kind in [('fee', '10.00', '费用'), ('interest', '5.00', '利息')]:
                    record = dict.fromkeys(fields, '')
                    record.update({'日期': '2031-01-01', '交易ID': tid, '金额': amount,
                        '币种': 'CNY', '实际/预计': '实际', '分类': kind, '脱敏备注': '合成测试',
                        '收入/支出/转账/投资本金/债务本金/利息/费用': kind})
                    writer.writerow(record)
            config_path = vault / '.obsidian/finance-assistant.json'
            config = json.loads(config_path.read_text(encoding='utf-8'))
            config.update({'cash_baseline': {'confirmed': True, 'amount': '1000.00',
                'as_of': '2031-01-01', 'included_transaction_ids': []},
                'cash_delta_by_id': {'interest': '5.00'}, 'monthly_reconciled': {'2031-01': True}})
            config_path.write_text(json.dumps(config), encoding='utf-8')
            result = sync(vault, date(2031, 1, 1))
            self.assertEqual(result['cash_balance'], '995.00')
            self.assertEqual(result['month_expenses'], '10.00')
            self.assertEqual(result['monthly_net'], '-5.00')
            config['cash_delta_by_id'] = {}
            config_path.write_text(json.dumps(config), encoding='utf-8')
            result = sync(vault, date(2031, 1, 1))
            self.assertIsNone(result['cash_balance'])
            self.assertIsNone(result['monthly_net'])

    def test_blank_then_cash_and_conflict(self):
        with tempfile.TemporaryDirectory() as temp:
            vault = Path(temp) / 'vault'
            init_vault(vault)
            config_path = vault / '.obsidian/finance-assistant.json'
            config = json.loads(config_path.read_text(encoding='utf-8'))
            self.assertIsNone(config['cash_baseline']['amount'])
            first = sync(vault, date(2031, 1, 1))
            self.assertIsNone(first['cash_balance'])
            self.assertEqual(sync(vault, date(2031, 1, 1))['changed_files'], 0)
            ledger = vault / '脱敏流水.csv'
            with ledger.open(encoding='utf-8') as handle:
                fields = next(csv.reader(handle))
            record = dict.fromkeys(fields, '')
            record.update({'日期': '2031-01-01', '交易ID': 'TEST-expense-1', '金额': '12.34',
                '币种': 'CNY', '实际/预计': '实际', '分类': '餐饮', '脱敏备注': '合成测试午饭',
                '收入/支出/转账/投资本金/债务本金/利息/费用': '支出'})
            with ledger.open('a', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writerow(record)
            config['cash_baseline'] = {'confirmed': True, 'amount': '1000.00',
                'as_of': '2031-01-01', 'included_transaction_ids': []}
            config['cash_label'] = '测试范围余额'
            config_path.write_text(json.dumps(config), encoding='utf-8')
            before = ledger.read_bytes()
            result = sync(vault, date(2031, 1, 1))
            self.assertEqual(result['cash_balance'], '987.66')
            self.assertEqual(result['today_expenses'], '12.34')
            self.assertEqual(ledger.read_bytes(), before)
            home = vault / '财务首页.md'
            self.assertIn('测试范围余额', home.read_text(encoding='utf-8'))
            private = vault / 'private/我的财务档案.md'
            private.write_text('user edits', encoding='utf-8')
            init_vault(vault)
            self.assertEqual(private.read_text(encoding='utf-8'), 'user edits')
            home.write_text(home.read_text(encoding='utf-8') + 'manual edit', encoding='utf-8')
            with self.assertRaises(ValueError):
                sync(vault, date(2031, 1, 2))


if __name__ == '__main__':
    unittest.main()
