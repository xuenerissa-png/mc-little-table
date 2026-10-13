#!/usr/bin/env python3
"""Coupon discovery and best-price planning for McLittle Table.

Read-only by default: claiming coupons (auto-bind-coupons) requires the explicit
--claim flag and an interactive confirmation, because it changes the user's account.
"""
import argparse
import json
import re
import sys
from mclittle import MCP, unwrap_tool, extract_payload


def parse_claimable(value):
    """Parse the markdown list returned by available-coupons into coupon titles."""
    s = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    out = []
    for line in s.splitlines():
        m = re.match(r'\s*[-*]?\s*优惠券标题[:：]\s*(.+?)\s*\\?\s*$', line)
        if m:
            title = m.group(1).strip().rstrip('\\').strip()
            if title and title not in out:
                out.append(title)
    return out


def parse_store_coupons(value):
    """Normalize query-store-coupons payload into a list of coupon dicts."""
    obj = extract_payload(value)
    rows = obj.get('data') or []
    if isinstance(rows, dict):
        rows = rows.get('list', [])
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        products = r.get('products') or []
        out.append({
            'title': r.get('title') or r.get('couponName') or '',
            'couponId': r.get('couponId'),
            'couponCode': r.get('couponCode'),
            'expire': r.get('tradeDateTime'),
            'productCodes': [str(p.get('productCode')) for p in products if isinstance(p, dict) and p.get('productCode')],
            'productNames': [p.get('productName') for p in products if isinstance(p, dict) and p.get('productName')],
            'moreCodes': r.get('couponCodeCount') or r.get('count'),
        })
    return out


def applicable(coupon, cart_codes):
    """A coupon applies when it targets at least one product in the cart (empty target = store-wide)."""
    if not coupon.get('productCodes'):
        return True
    return any(code in cart_codes for code in coupon['productCodes'])


def build_item_payload(cart, coupon=None):
    """Attach a coupon to matching items; keep the rest untouched."""
    items = []
    for item in cart:
        row = {'productCode': str(item['productCode']), 'quantity': int(item.get('quantity', 1))}
        if coupon and (not coupon.get('productCodes') or row['productCode'] in coupon['productCodes']):
            if coupon.get('couponCode'):
                row['couponCode'] = coupon['couponCode']
            if coupon.get('couponId'):
                row['couponId'] = coupon['couponId']
        items.append(row)
    return items


def price_of(value):
    """Extract the payable amount (in fen) from a calculate-price payload."""
    obj = extract_payload(value)
    data = obj.get('data') or {}
    for key in ('price', 'realTotalAmount', 'productPrice'):
        v = data.get(key)
        if isinstance(v, (int, float)):
            return int(v)
        if isinstance(v, str) and v.replace('.', '', 1).isdigit():
            return int(float(v) * 100) if '.' in v else int(v)
    return None


def api_error(value):
    """Return the API error message when the payload reports failure, else None."""
    obj = extract_payload(value)
    if obj.get('success') is False:
        return str(obj.get('message') or obj.get('code') or '未知错误')
    return None


def price_scenario(client, store_code, order_type, be_type, cart, coupon=None, label='不使用优惠券'):
    """Call calculate-price and return {label, price, error}; survives sell-out/时段 errors."""
    try:
        res = unwrap_tool(client.call('calculate-price', {
            'storeCode': store_code, 'orderType': order_type, 'beType': be_type,
            'items': build_item_payload(cart, coupon)}))
    except Exception as exc:  # network / tool failure
        return {'label': label, 'price': None, 'error': str(exc)}
    err = api_error(res)
    if err:
        return {'label': label, 'price': None, 'error': err,
                'hint': '60006 表示该餐品在当前时段不可售（如早餐时段），需按当前菜单重新选品'}
    out = {'label': label, 'price': price_of(res)}
    if coupon:
        out['couponId'] = coupon.get('couponId')
    return out


def pick_best(baseline, scenarios):
    """Rank {label, price} options and report the best + savings in fen."""
    options = [{'label': '不使用优惠券', 'price': baseline}] + [s for s in scenarios if s.get('price') is not None]
    options = [o for o in options if o.get('price') is not None]
    if not options:
        return {'best': None, 'options': [], 'savings_fen': 0}
    options.sort(key=lambda x: x['price'])
    best = options[0]
    return {'best': best, 'options': options, 'savings_fen': (baseline or 0) - best['price']}


def collect(client, store_code, order_type, be_type, cart=None):
    """Read-only coupon reconnaissance for a store."""
    claimable = parse_claimable(unwrap_tool(client.call('available-coupons')))
    wallet_raw = unwrap_tool(client.call('query-my-coupons'))
    wallet_text = wallet_raw if isinstance(wallet_raw, str) else json.dumps(wallet_raw, ensure_ascii=False)
    wallet = [] if '暂无可用优惠券' in wallet_text else [x for x in (extract_payload(wallet_text).get('data') or []) if isinstance(x, dict)]
    store_coupons = parse_store_coupons(unwrap_tool(client.call('query-store-coupons', {
        'storeCode': store_code, 'orderType': order_type, 'beType': be_type})))
    result = {'claimable': claimable, 'wallet_count': len(wallet), 'store_coupons': store_coupons}
    if cart:
        codes = {str(i['productCode']) for i in cart}
        result['usable_for_cart'] = [c for c in store_coupons if applicable(c, codes)]
    return result


def main():
    p = argparse.ArgumentParser(description='麦麦亲子小饭桌 · 领券与最优价格')
    p.add_argument('--store', required=True, help='门店 storeCode')
    p.add_argument('--order-type', type=int, default=1)
    p.add_argument('--be-type', type=int, default=1)
    p.add_argument('--items', help='购物车，格式 6102:1,1450:1（productCode:数量）')
    p.add_argument('--claim', action='store_true', help='已确认后领取麦麦省可用券（会修改账户，需二次确认）')
    a = p.parse_args()

    cart = None
    if a.items:
        cart = [{'productCode': c.split(':')[0], 'quantity': int(c.split(':')[1]) if ':' in c else 1}
                for c in a.items.split(',') if c.strip()]

    client = MCP(); client.initialize()
    report = collect(client, a.store, a.order_type, a.be_type, cart)

    if a.claim:
        if not sys.stdin.isatty():
            raise SystemExit('--claim 需要交互确认，请在终端中运行')
        answer = input('将自动领取所有可用优惠券并写入你的麦当劳账户，确认？(y/N) ').strip().lower()
        if answer == 'y':
            client.call('auto-bind-coupons')
            report['claimed'] = True
        else:
            report['claimed'] = False

    if cart:
        base = price_scenario(client, a.store, a.order_type, a.be_type, cart)
        scenarios = [price_scenario(client, a.store, a.order_type, a.be_type, cart, c,
                                    c.get('title') or '门店券')
                     for c in report.get('usable_for_cart', [])]
        report['pricing'] = pick_best(base.get('price'), scenarios)
        report['pricing']['baseline'] = base
        report['pricing']['scenarios'] = scenarios
        if base.get('error'):
            report['pricing']['notice'] = base.get('hint') or base['error']

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
