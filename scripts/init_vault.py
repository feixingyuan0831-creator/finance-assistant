"""Create a blank, user-selected local vault without overwriting existing files."""
import argparse
import json
from pathlib import Path


def init_vault(vault):
    vault = Path(vault).expanduser().resolve()
    skill = Path(__file__).resolve().parents[1]
    if vault == skill or skill in vault.parents:
        raise ValueError('私人财务库必须位于Skill目录之外。')
    vault.mkdir(parents=True, exist_ok=True)
    config = json.loads((skill / 'assets/finance-assistant.config.json').read_text(encoding='utf-8'))
    config['vault_path'] = str(vault)
    contents = {
        'AGENTS.md': (skill / 'references/graduate-policy.md').read_text(encoding='utf-8') +
            '\n本库以脱敏流水.csv为唯一流水。未知不当零，付款账户可省略；金额、目标和统计范围由用户确认。记账前备份，之后运行Skill同步器。不得发布此库。\n',
        'private/我的财务档案.md': (skill / 'assets/财务信息模板.md').read_text(encoding='utf-8'),
        'private/储蓄目标.md': '# 储蓄目标\n\n目标、截止日、已隔离余额、用途和排除项待用户确认；不填写虚构金额。\n',
        'private/独立投资资产.md': '# 独立投资资产\n\n账户别名、资产、估值日及目标排除范围待用户确认。\n',
        '脱敏流水.csv': (skill / 'assets/脱敏流水模板.csv').read_text(encoding='utf-8-sig'),
        '流水浏览.base': (skill / 'assets/流水浏览.base').read_text(encoding='utf-8'),
        '.obsidian/finance-assistant.json': json.dumps(config, ensure_ascii=False, indent=2) + '\n',
        '随手记.md': '# 随手记\n\n填写真实日期、事项和金额，之后请Agent读取并入账；已登记条目标注交易ID。此文件不是正式流水。\n',
        '月度复盘入口.md': '# 月度复盘\n\n请Agent读取完整账本，按指定月份核对收入、消费、余额、目标和下一月安排。\n',
        'Obsidian使用说明.md': '# 使用方式\n\n将本目录作为Obsidian库打开。正式流水为CSV，交易明细是镜像；在Agent中自然语言记账后同步首页。没有后台连接或默认提醒。\n'
    }
    created, skipped = [], []
    for relative, text in contents.items():
        path = vault / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open('x', encoding='utf-8', newline='') as handle:
                handle.write(text)
            created.append(relative)
        except FileExistsError:
            skipped.append(relative)
    return {'created': created, 'skipped': skipped}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(init_vault(args.vault), ensure_ascii=False))
