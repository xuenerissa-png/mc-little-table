import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from mclittle import sodium_limit,parse_toon,analyze,compare

class TestSkill(unittest.TestCase):
    def test_ages(self):
        self.assertEqual([sodium_limit(x) for x in (1,3,4,8,9,12)],[1200,1200,1500,1500,1800,1800])
        with self.assertRaises(ValueError): sodium_limit(13)
    def test_toon(self):
        s='[2]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:\n  A,null,100,20,3,2,4,110,5\n  B,null,200,40,4,3,5,320,6'
        rows=parse_toon({'data':s})
        self.assertEqual(len(rows),2)
        ranked=analyze(rows,3,200)
        self.assertEqual(ranked[0]['name'],'A')
        self.assertTrue(ranked[0]['within_user_meal_budget'])
        self.assertFalse(ranked[1]['within_user_meal_budget'])
        self.assertEqual(compare(ranked,'B','A')['sodium_change_mg'],-210)
    def test_markdown_wrapped_response(self):
        s='# API Response Information\n\n## Original Response\n\n{"success":true,"code":200,"data":"[1]{productName,energyKcal,protein,sodium}:\\n  猪柳麦满分,308,16,781"}'
        rows=parse_toon(s)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['productName'],'猪柳麦满分')
        self.assertEqual(rows[0]['sodium'],'781')
    def test_exclusion(self):
        rows=[{'productName':'香辣鸡','sodium':'20'},{'productName':'普通餐品','sodium':'null'},{'productName':'A','sodium':'50'}]
        self.assertEqual([x['name'] for x in analyze(rows,4)],['A'])

if __name__=='__main__': unittest.main()
