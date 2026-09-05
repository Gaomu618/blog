r"""
generate_anki.py
================
从 Markdown 博客提取 FLASH_CARD 块,生成 Anki 卡片 CSV。

Markdown 里的标记语法:

    <!-- FLASH_CARD
    Q: 问题
    A: 答案
    -->

    <!-- FLASH_CARD
    Q: 第二个问题
    A: 第二个答案
    -->

用法:
    py generate_anki.py <md 文件> [更多...]
    py generate_anki.py src\content\blog\hi-im-tagaki.md
    py generate_anki.py src\content\blog\*.md     # 整批

输出:  项目根目录的 cards.csv (UTF-8 with BOM, Excel/Anki 都能直接读)
"""

import re
import sys
import csv
import pathlib
from typing import List, Tuple

# 匹配 <!-- FLASH_CARD ... Q: ... A: ... -->
CARD_PATTERN = re.compile(
    r'<!--\s*FLASH_CARD\s*\n'
    r'Q:\s*(.+?)\n'
    r'A:\s*(.+?)\n'
    r'-->\s*',
    re.DOTALL,
)


def extract_cards(md_path: pathlib.Path) -> List[Tuple[str, str]]:
    text = md_path.read_text(encoding='utf-8')
    return [(q.strip(), a.strip()) for q, a in CARD_PATTERN.findall(text)]


def write_csv(cards: List[Tuple[str, str]], out_path: pathlib.Path) -> None:
    # utf-8-sig: 加 BOM,Excel/Anki 中文不乱码
    with out_path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['问题', '答案'])
        for q, a in cards:
            w.writerow([q, a])


def main() -> int:
    if len(sys.argv) < 2:
        print('用法:')
        print('  py generate_anki.py <md 文件> [更多...]')
        print('  py generate_anki.py src\\content\\blog\\*.md')
        sys.exit(1)

    # 展开通配符
    targets: List[pathlib.Path] = []
    for arg in sys.argv[1:]:
        if '*' in arg or '?' in arg:
            targets.extend(pathlib.Path('.').glob(arg))
        else:
            targets.append(pathlib.Path(arg))

    if not targets:
        print('没找到任何 Markdown 文件')
        return 1

    all_cards: List[Tuple[str, str]] = []
    print(f'扫描 {len(targets)} 个文件:')
    for md in targets:
        if not md.exists():
            print(f'  [跳过] {md} (不存在)')
            continue
        cards = extract_cards(md)
        print(f'  {md}: {len(cards)} 张')
        all_cards.extend(cards)

    if not all_cards:
        print('\n没找到任何 FLASH_CARD 块。')
        print('提示: 在 .md 里加这种语法标记卡片:')
        print('  <!-- FLASH_CARD')
        print('  Q: 问题')
        print('  A: 答案')
        print('  -->')
        return 0

    out = pathlib.Path('cards.csv')
    write_csv(all_cards, out)
    print(f'\n✅ 已生成 {out} ({len(all_cards)} 张卡片)')
    print()
    print('下一步:')
    print('  1. 打开 Anki')
    print('  2. File → Import')
    print('  3. 选 cards.csv')
    print('  4. Field separator: Comma')
    print('  5. 第一个字段 → Front, 第二个 → Back')
    print('  6. 选 deck (如 "Java 学习"),点 Import')

    return 0


if __name__ == '__main__':
    sys.exit(main())
