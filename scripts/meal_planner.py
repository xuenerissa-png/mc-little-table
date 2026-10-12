#!/usr/bin/env python3
"""Conservative, auditable whole-meal planner. All nutrition figures must be supplied by verified sources."""
import argparse
import itertools
import json
from pathlib import Path
from mclittle import sodium_limit, number

SPICY = ('辣', 'spicy', 'chili', '麻辣', 'hot & spicy')
ROLES = ('main', 'side', 'drink')


def prepare(item, avoid_allergens=(), avoid_spicy=True, age=3):
    """Return normalized item or None. Unknown safety information is excluded."""
    name = str(item.get('name', '')).strip()
    if not name or item.get('available') is not True or item.get('nutrition_verified') is not True:
        return None
    if item.get('role') not in ROLES or item.get('age_min', 99) > age:
        return None
    if item.get('age_max', 99) < age:
        return None
    if item.get('texture_checked') is not True or item.get('allergens_verified') is not True:
        return None
    allergens = item.get('allergens')
    if not isinstance(allergens, list) or any(a.casefold() in {str(x).casefold() for x in allergens} for a in avoid_allergens):
        return None
    if avoid_spicy and (item.get('spicy') is not False or any(x in name.casefold() for x in SPICY)):
        return None
    sodium = number(item.get('sodium_mg'))
    energy = number(item.get('energy_kcal'))
    protein = number(item.get('protein_g'))
    if sodium is None or sodium < 0 or energy is None or energy < 0 or protein is None or protein < 0:
        return None
    return {**item, 'sodium_mg': sodium, 'energy_kcal': energy, 'protein_g': protein}


def plan(items, age, budget=None, avoid_allergens=(), max_results=3, require_drink=True):
    """Compose 1 main + 0/1 side + 1 drink; do not assume official combo availability."""
    daily = sodium_limit(age)
    if budget is not None and budget <= 0:
        raise ValueError('本餐钠预算必须大于 0')
    if not 1 <= max_results <= 3:
        raise ValueError('最多输出 1–3 套方案')
    valid = [v for i in items if (v := prepare(i, avoid_allergens, age=age)) is not None]
    groups = {r: [x for x in valid if x['role'] == r] for r in ROLES}
    if not groups['main'] or (require_drink and not groups['drink']):
        return {'age': age, 'daily_reference_mg': daily, 'meal_budget_mg': budget,
                'plans': [], 'reason': '缺少经过核实且符合限制的主食或饮品，不能可靠搭配整餐。'}
    candidates = []
    drinks = groups['drink'] if require_drink else [None] + groups['drink']
    for main, side, drink in itertools.product(groups['main'], [None] + groups['side'], drinks):
        parts = [x for x in (main, side, drink) if x]
        ids = [str(x.get('id', x['name'])) for x in parts]
        if len(ids) != len(set(ids)):
            continue
        sodium = round(sum(x['sodium_mg'] for x in parts), 2)
        kcal = round(sum(x['energy_kcal'] for x in parts), 2)
        protein = round(sum(x['protein_g'] for x in parts), 2)
        candidates.append({'items': [x['name'] for x in parts], 'item_ids': ids,
                           'sodium_mg': sodium, 'energy_kcal': kcal, 'protein_g': protein,
                           'fraction_of_daily_sodium_reference': round(sodium / daily, 3),
                           'within_meal_budget': None if budget is None else sodium <= budget,
                           'price_total': (round(sum(x['price'] for x in parts), 2)
                                           if all(isinstance(x.get('price'), (int, float)) and x['price'] >= 0 for x in parts) else None),
                           'notice': '仅由核实的单品组成；不代表官方套餐、允许替换或可一键下单。'})
    if budget is not None:
        candidates = [c for c in candidates if c['within_meal_budget']]
    # Offer distinct tradeoffs: lowest sodium, highest protein, lowest energy, avoiding duplicate compositions.
    ranked = [sorted(candidates, key=lambda x: (x['sodium_mg'], -x['protein_g'])),
              sorted(candidates, key=lambda x: (-x['protein_g'], x['sodium_mg'])),
              sorted(candidates, key=lambda x: (x['energy_kcal'], x['sodium_mg']))]
    result = []
    for label, options in zip(('少钠优先', '蛋白质优先', '轻量优先'), ranked):
        choice = next((x for x in options if x['item_ids'] not in [p['item_ids'] for p in result]), None)
        if choice:
            result.append({'label': label, **choice})
        if len(result) >= max_results:
            break
    return {'age': age, 'daily_reference_mg': daily, 'daily_reference': '美国 2025–2030 膳食指南，mg/日，非每餐标准',
            'meal_budget_mg': budget, 'plans': result,
            'reason': None if result else '没有满足已核实安全条件及本餐预算的组合。',
            'safety_note': '仍需家长确认现场供应、实际配料、交叉接触风险及儿童咀嚼能力。'}


def swap(items, selected_ids, old_id, new_id, age, budget=None, avoid_allergens=()):
    """Compare one verified component replacement without claiming store permits it."""
    valid = {str(x.get('id', x['name'])): x for i in items if (x := prepare(i, avoid_allergens, age=age))}
    if old_id not in selected_ids or old_id not in valid or new_id not in valid:
        raise ValueError('替换前后必须是已核实餐品，且原餐品必须在当前组合中')
    if valid[old_id]['role'] != valid[new_id]['role']:
        raise ValueError('只能比较同类型餐品的替换')
    if any(i not in valid for i in selected_ids):
        raise ValueError('原组合中存在未核实餐品')
    updated = [new_id if i == old_id else i for i in selected_ids]
    if len(updated) != len(set(updated)):
        raise ValueError('替换后出现重复餐品')
    def totals(ids):
        return {key: round(sum(valid[i][key] for i in ids), 2) for key in ('sodium_mg', 'energy_kcal', 'protein_g')}
    before, after = totals(selected_ids), totals(updated)
    return {'before': before, 'after': after,
            'delta': {k: round(after[k]-before[k], 2) for k in before},
            'within_meal_budget_after': None if budget is None else after['sodium_mg'] <= budget,
            'notice': '仅营养数值比较，须向门店确认能否实际替换。'}


def main():
    parser = argparse.ArgumentParser(description='麦麦亲子小饭桌 · 整餐搭配')
    parser.add_argument('--catalog', required=True, help='经过菜单及营养双重核实的 JSON 商品目录')
    parser.add_argument('--age', required=True, type=float)
    parser.add_argument('--meal-budget', type=float)
    parser.add_argument('--avoid-allergens', default='', help='逗号分隔')
    parser.add_argument('--swap', nargs=3, metavar=('SELECTED_IDS', 'OLD_ID', 'NEW_ID'),
                        help='SELECTED_IDS 为逗号分隔商品 ID')
    args = parser.parse_args()
    items = json.loads(Path(args.catalog).read_text(encoding='utf-8'))
    if isinstance(items, dict):
        items = items['items']
    allergens = [x.strip() for x in args.avoid_allergens.split(',') if x.strip()]
    if args.swap:
        selected, old, new = args.swap
        result = swap(items, selected.split(','), old, new, args.age, args.meal_budget, allergens)
    else:
        result = plan(items, args.age, args.meal_budget, allergens)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
