#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
易經卜卦 — 三錢法
使用 8x8 二維查表 確保 64 卦完整無重複無歧義
"""

import random

# ─────────────────────────────────────────
# 常數定義
# ─────────────────────────────────────────

# 八卦二進位值（第一爻在最低位，陽=1 陰=0）
#   乾=7(111)  兌=6(110)  離=5(101)  震=4(100)
#   巽=3(011)  坎=2(010)  艮=1(001)  坤=0(000)

TRIGRAM_NAMES = ["坤", "艮", "坎", "巽", "震", "離", "兌", "乾"]
TRIGRAM_SYMBOLS = ["☷", "☶", "☵", "☴", "☳", "☲", "☱", "☰"]
TRIGRAM_NATURE = ["地", "山", "水", "風", "雷", "火", "澤", "天"]

# 六十四卦名稱（索引 0 = 佔位，索引 1–64 = 第1–64卦）
HEXAGRAM_NAMES = [
    "",          # 佔位
    "乾為天",    # 1
    "坤為地",    # 2
    "水雷屯",    # 3
    "山水蒙",    # 4
    "水天需",    # 5
    "天水訟",    # 6
    "地水師",    # 7
    "水地比",    # 8
    "風天小畜",  # 9
    "天澤履",    # 10
    "地天泰",    # 11
    "天地否",    # 12
    "天火同人",  # 13
    "火天大有",  # 14
    "地山謙",    # 15
    "雷地豫",    # 16
    "澤雷隨",    # 17
    "山風蠱",    # 18
    "地澤臨",    # 19
    "風地觀",    # 20
    "火雷噬嗑",  # 21
    "山火賁",    # 22
    "山地剝",    # 23
    "地雷復",    # 24
    "天雷無妄",  # 25
    "山天大畜",  # 26
    "山雷頤",    # 27
    "澤風大過",  # 28
    "坎為水",    # 29
    "離為火",    # 30
    "澤山咸",    # 31
    "雷風恆",    # 32
    "天山遯",    # 33
    "雷天大壯",  # 34
    "火地晉",    # 35
    "地火明夷",  # 36
    "風火家人",  # 37
    "火澤睽",    # 38
    "水山蹇",    # 39
    "雷水解",    # 40
    "山澤損",    # 41
    "風雷益",    # 42
    "澤天夬",    # 43
    "天風姤",    # 44
    "澤地萃",    # 45
    "地風升",    # 46
    "澤水困",    # 47
    "水風井",    # 48
    "澤火革",    # 49
    "火風鼎",    # 50
    "震為雷",    # 51
    "艮為山",    # 52
    "風山漸",    # 53
    "雷澤歸妹",  # 54
    "雷火豐",    # 55
    "火山旅",    # 56
    "巽為風",    # 57
    "兌為澤",    # 58
    "風水渙",    # 59
    "水澤節",    # 60
    "風澤中孚",  # 61
    "雷山小過",  # 62
    "水火既濟",  # 63
    "火水未濟",  # 64
]

# 8x8 查表 TABLE[下卦二進位][上卦二進位] = 卦號
# 下卦 row index = 坤0 艮1 坎2 巽3 震4 離5 兌6 乾7
# 上卦 col index = 坤0 艮1 坎2 巽3 震4 離5 兌6 乾7
TABLE = [
    #  坤   艮   坎   巽   震   離   兌   乾    ← 上卦
    [   2,  23,   8,  20,  16,  35,  45,  12],  # 下卦=坤
    [  15,  52,  39,  53,  62,  56,  31,  33],  # 下卦=艮
    [   7,   4,  29,  59,  40,  64,  47,   6],  # 下卦=坎
    [  46,  18,  48,  57,  32,  50,  28,  44],  # 下卦=巽
    [  24,  27,   3,  42,  51,  21,  17,  25],  # 下卦=震
    [  36,  22,  63,  37,  55,  30,  49,  13],  # 下卦=離
    [  19,  41,  60,  61,  54,  38,  58,  10],  # 下卦=兌
    [  11,  26,   5,   9,  34,  14,  43,   1],  # 下卦=乾
]


# ─────────────────────────────────────────
# 驗證（開發期保留 上線後可移除）
# ─────────────────────────────────────────

def _validate_table() -> None:
    all_nums = [TABLE[r][c] for r in range(8) for c in range(8)]
    assert sorted(all_nums) == list(range(1, 65)), \
        "TABLE 有錯誤：64卦不完整或有重複"

_validate_table()


# ─────────────────────────────────────────
# 起卦邏輯
# ─────────────────────────────────────────

def toss_coins() -> int:
    """
    擲三枚銅錢：正面=3 反面=2
    合計 6=老陰(變) 7=少陽 8=少陰 9=老陽(變)
    """
    return sum(random.choice([2, 3]) for _ in range(3))


def line_info(value: int) -> dict:
    """將爻值轉換為完整爻資訊"""
    if value == 6:
        return {"yang": False, "changing": True,  "symbol": "-- ×", "label": "老陰（變）"}
    elif value == 7:
        return {"yang": True,  "changing": False, "symbol": "———", "label": "少陽"}
    elif value == 8:
        return {"yang": False, "changing": False, "symbol": "-- -", "label": "少陰"}
    elif value == 9:
        return {"yang": True,  "changing": True,  "symbol": "——×", "label": "老陽（變）"}
    raise ValueError(f"非法爻值: {value}")


def lines_to_trigram(three_lines: list[dict]) -> int:
    """
    三爻轉八卦二進位值
    第一爻在最低位（bit 0）
    陽=1 陰=0
    """
    result = 0
    for i, line in enumerate(three_lines):
        if line["yang"]:
            result |= (1 << i)
    return result


def cast_hexagram() -> dict:
    """起卦主函數 回傳完整卦象資訊"""
    values = [toss_coins() for _ in range(6)]
    lines = [line_info(v) for v in values]

    lower_bits = lines_to_trigram(lines[0:3])
    upper_bits = lines_to_trigram(lines[3:6])
    hexagram_num = TABLE[lower_bits][upper_bits]

    # 計算之卦（變爻取反）
    changed_lines = []
    for line in lines:
        if line["changing"]:
            # 老陰→少陽 老陽→少陰
            changed_lines.append(line_info(7 if not line["yang"] else 8))
        else:
            changed_lines.append(line)

    new_lower_bits = lines_to_trigram(changed_lines[0:3])
    new_upper_bits = lines_to_trigram(changed_lines[3:6])
    zhi_num = TABLE[new_lower_bits][new_upper_bits]

    changing_positions = [i + 1 for i, line in enumerate(lines) if line["changing"]]

    return {
        "values": values,
        "lines": lines,
        "lower_bits": lower_bits,
        "upper_bits": upper_bits,
        "hexagram_num": hexagram_num,
        "hexagram_name": HEXAGRAM_NAMES[hexagram_num],
        "lower_name": TRIGRAM_NAMES[lower_bits],
        "lower_nature": TRIGRAM_NATURE[lower_bits],
        "upper_name": TRIGRAM_NAMES[upper_bits],
        "upper_nature": TRIGRAM_NATURE[upper_bits],
        "changing_positions": changing_positions,
        "zhi_num": zhi_num,
        "zhi_name": HEXAGRAM_NAMES[zhi_num],
        "zhi_lower_name": TRIGRAM_NAMES[new_lower_bits],
        "zhi_upper_name": TRIGRAM_NAMES[new_upper_bits],
    }


# ─────────────────────────────────────────
# 顯示
# ─────────────────────────────────────────

def display(result: dict) -> None:
    print("\n" + "═" * 44)
    print("  易經卜卦 — 三錢法")
    print("═" * 44)

    print("\n【起卦過程】（第一爻→第六爻，由下往上）\n")
    for i, (v, line) in enumerate(zip(result["values"], result["lines"])):
        mark = " ★" if line["changing"] else ""
        print(f"  第{i+1}爻  合計={v}  {line['symbol']}  {line['label']}{mark}")

    print("\n" + "─" * 44)
    print("【本卦爻象】（由上往下顯示）\n")
    print(f"  上卦  {result['upper_name']}（{result['upper_nature']}）")
    for line in reversed(result["lines"][3:6]):
        print(f"    {line['symbol']}")
    print(f"  下卦  {result['lower_name']}（{result['lower_nature']}）")
    for line in reversed(result["lines"][0:3]):
        print(f"    {line['symbol']}")

    print("\n" + "─" * 44)
    n = result["hexagram_num"]
    print(f"【本卦】  第 {n:02d} 卦  《{result['hexagram_name']}》")

    if result["changing_positions"]:
        pos_str = " ".join(f"第{p}爻" for p in result["changing_positions"])
        print(f"\n【變爻】  {pos_str}")
        print(f"\n【之卦】  第 {result['zhi_num']:02d} 卦  《{result['zhi_name']}》")
        print(f"          {result['zhi_upper_name']}上  {result['zhi_lower_name']}下")
    else:
        print("\n【變爻】  無（六爻皆靜 以本卦卦辭為主）")

    print("\n" + "═" * 44 + "\n")


# ─────────────────────────────────────────
# 入口
# ─────────────────────────────────────────

if __name__ == "__main__":
    result = cast_hexagram()
    display(result)
