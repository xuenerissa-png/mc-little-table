import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from deals import (parse_claimable, parse_store_coupons, parse_wallet, applicable, build_item_payload,
                   pick_best, price_of, api_error, price_scenario)

WALLET_MD = '''# 您的优惠券列表

共 6 张可用优惠券 | 第 1/1 页 | 每页 200 条

## 9.9元中杯冰美式
- **优惠**: ¥9.9 (用券价格)
- **有效期**: 2026-10-13 00:00-2026-10-19 23:59
- **领取时间**: 今日收到
- **标签**: 到店专用、外送专用

<img src="https://img.mcd.cn/x.jpg" alt="9.9元中杯冰美式" width="300">

## 中薯条买一送一
- **优惠**: ¥13.5 (用券价格)
- **有效期**: 2026-10-12 10:30-2026-10-16 23:59
- **标签**: 到店专用
'''

CLAIMABLE_MD = '''### 麦麦省优惠券列表：
- 优惠券标题：中薯条买一送一 \\
  状态：可领取 \\
- 优惠券标题：王牌小食拼 \\
  状态：可领取 \\
- 优惠券标题：中薯条买一送一 \\
  状态：可领取 \\
'''

STORE_MD = '''## Response Structure
| 券名 | `data[].title` | 强制展示 |
{"success":true,"code":200,"data":[{"title":"麦香鸡5折券","couponId":"CID1","couponCode":"CODE1",
"tradeDateTime":"2026-10-20 23:59","products":[{"productCode":"1450","productName":"麦香鸡"}]}]}'''


class TestDeals(unittest.TestCase):
    def test_parse_claimable_dedup(self):
        titles = parse_claimable(CLAIMABLE_MD)
        self.assertEqual(titles, ['中薯条买一送一', '王牌小食拼'])

    def test_parse_store_coupons(self):
        rows = parse_store_coupons(STORE_MD)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['couponId'], 'CID1')
        self.assertEqual(rows[0]['productCodes'], ['1450'])

    def test_parse_wallet_markdown(self):
        wallet = parse_wallet(WALLET_MD)
        self.assertEqual([w['title'] for w in wallet], ['9.9元中杯冰美式', '中薯条买一送一'])
        self.assertEqual(wallet[0]['price_text'], '¥9.9 (用券价格)')
        self.assertIn('到店专用', wallet[0]['tags'])
        self.assertEqual(wallet[1]['tags'], ['到店专用'])
        self.assertEqual(parse_wallet('# 您的优惠券列表\n\n暂无可用优惠券'), [])

    def test_applicable(self):
        coupon = {'productCodes': ['1450']}
        self.assertTrue(applicable(coupon, {'1450', '6102'}))
        self.assertFalse(applicable(coupon, {'6102'}))
        self.assertTrue(applicable({'productCodes': []}, {'6102'}))

    def test_build_item_payload_attaches_coupon_only_to_matching(self):
        cart = [{'productCode': '1450', 'quantity': 1}, {'productCode': '6102', 'quantity': 2}]
        coupon = {'couponId': 'CID1', 'couponCode': 'CODE1', 'productCodes': ['1450']}
        items = build_item_payload(cart, coupon)
        self.assertEqual(items[0]['couponId'], 'CID1')
        self.assertNotIn('couponId', items[1])
        self.assertEqual(items[1]['quantity'], 2)

    def test_price_of_variants(self):
        self.assertEqual(price_of('{"data":{"price":2900}}'), 2900)
        self.assertEqual(price_of('## Original Response\n{"data":{"price":"2900"}}'), 2900)
        self.assertEqual(price_of('{"data":{"price":29.5}}'), 29)

    def test_pick_best(self):
        r = pick_best(3150, [{'label': '券A', 'price': 2900}, {'label': '券B', 'price': None}])
        self.assertEqual(r['best']['label'], '券A')
        self.assertEqual(r['savings_fen'], 250)
        self.assertEqual(len(r['options']), 2)

    def test_api_error_detects_sellout(self):
        sold_out = '## Original Response\n{"success":false,"code":60006,"message":"商品已售罄或不可售"}'
        self.assertEqual(api_error(sold_out), '商品已售罄或不可售')
        ok = '## Original Response\n{"success":true,"code":200,"data":{"price":3150}}'
        self.assertIsNone(api_error(ok))

    def test_price_scenario_survives_api_error(self):
        class FakeClient:
            def call(self, *a, **kw):
                return {'content': [{'type': 'text', 'text': '## Original Response\n{"success":false,"code":60006,"message":"商品已售罄或不可售"}'}]}
        out = price_scenario(FakeClient(), '1400116', 1, 1, [{'productCode': '6102', 'quantity': 1}])
        self.assertIsNone(out['price'])
        self.assertIn('60006', out['hint'])


if __name__ == '__main__':
    unittest.main()
