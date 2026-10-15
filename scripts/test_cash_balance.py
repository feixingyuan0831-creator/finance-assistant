"""Run the aggregate-cash invariants with synthetic amounts only."""
from datetime import date
from decimal import Decimal

from sync_obsidian import cash_balance


def check():
    day = date(2031, 10, 14)
    def entry(tid, amount, kind):
        return ({'交易ID': tid}, day, Decimal(amount), kind)
    entries = [entry('included', '10', '支出'), entry('expense', '20', '支出'),
               entry('income', '30', '收入'), entry('transfer', '500', '转账'),
               entry('repaid', '40', '债务本金')]
    config = {'cash_baseline': {'confirmed': True, 'amount': '1000.00',
              'as_of': '2031-10-14T12:00:00+08:00', 'included_transaction_ids': ['included']},
              'cash_delta_by_id': {'repaid': '40.00'}}
    result, status = cash_balance(entries, config, day)
    assert result == Decimal('1050.00'), 'Excluded entries, transfers, or repayment were miscounted.'
    assert cash_balance(entries, {}, day)[0] is None, 'Missing baseline must remain unknown.'
    unknown = entries + [entry('investment', '10', '投资本金')]
    assert cash_balance(unknown, config, day)[0] is None, 'Unknown direction must not be silently skipped.'
    before = ({'交易ID': 'late-history'}, date(2031, 10, 13), Decimal('200'), '支出')
    assert cash_balance(entries + [before], config, day)[0] == result, 'Earlier spending must not be deducted twice.'
    card = [entry('card-purchase', '100', '支出'), entry('card-payment', '100', '债务本金')]
    card_config = {'cash_baseline': {'confirmed': True, 'amount': '1000.00',
                   'as_of': '2031-10-14', 'included_transaction_ids': []},
                   'cash_delta_by_id': {'card-purchase': '0.00', 'card-payment': '-100.00'}}
    assert cash_balance(card, card_config, day)[0] == Decimal('900.00'), 'Credit purchase and repayment must not deduct cash twice.'


if __name__ == '__main__':
    check()
    print('Aggregate cash checks passed.')
