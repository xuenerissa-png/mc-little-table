import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from meal_planner import plan, swap

def item(id, role, sodium, protein=3, energy=100, **kw):
    return dict(id=id, name=id, role=role, sodium_mg=sodium, protein_g=protein,
                energy_kcal=energy, available=True, nutrition_verified=True,
                allergens_verified=True, allergens=[], texture_checked=True,
                spicy=False, age_min=1, age_max=12, **kw)

class TestMealPlanner(unittest.TestCase):
    def setUp(self):
        self.items=[item('mainA','main',180,10),item('mainB','main',240,18),
                    item('sideA','side',30),item('drinkA','drink',0),item('drinkB','drink',25)]
    def test_three_real_combinations(self):
        r=plan(self.items,3,300)
        self.assertEqual(len(r['plans']),3)
        self.assertTrue(all(p['sodium_mg']<=300 for p in r['plans']))
        self.assertEqual(len({tuple(p['item_ids']) for p in r['plans']}),3)
    def test_budget_no_result(self):
        self.assertFalse(plan(self.items,3,100)['plans'])
    def test_unknown_safety_excluded(self):
        self.items[0]['allergens_verified']=False
        self.items[1]['spicy']=None
        self.assertFalse(plan(self.items,3)['plans'])
    def test_allergen(self):
        self.items[0]['allergens']=['milk']
        r=plan(self.items,3,avoid_allergens=['milk'])
        self.assertTrue(all('mainA' not in p['items'] for p in r['plans']))
    def test_swap(self):
        r=swap(self.items,['mainA','drinkA'],'mainA','mainB',3,300)
        self.assertEqual(r['delta']['sodium_mg'],60)
    def test_no_invented_availability(self):
        self.items[0]['available']=None
        self.assertTrue(all('mainA' not in p['items'] for p in plan(self.items,3)['plans']))

if __name__=='__main__': unittest.main()
