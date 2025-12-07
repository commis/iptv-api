import unittest

from utils.sort_util import mixed_sort_key


class TestMixedSortKey(unittest.TestCase):
    """测试混合排序键函数"""

    def test_pure_alphabet(self):
        """测试纯字母：按小写ASCII排序（不区分原大小写）"""
        lst = ["Banana", "apple", "Cherry", "aBc"]
        sorted_lst = sorted(lst, key=mixed_sort_key)
        self.assertEqual(sorted_lst, ["aBc", "apple", "Banana", "Cherry"])

    def test_pure_number(self):
        """测试纯数字：自然排序（而非字符串字典序）"""
        lst = ["10", "2", "100", "1", "0", "99"]
        sorted_lst = sorted(lst, key=mixed_sort_key)
        self.assertEqual(sorted_lst, ["0", "1", "2", "10", "99", "100"])

    def test_pure_chinese(self):
        """测试纯汉字：按拼音小写排序"""
        # 场景1：城市拼音排序（北京(bei) < 广州(guang) < 上海(shang) < 深圳(shen)）
        city_lst = ["上海", "北京", "广州", "深圳"]
        self.assertEqual(
            sorted(city_lst, key=mixed_sort_key),
            ["北京", "广州", "上海", "深圳"]
        )

        # 场景2：人名拼音排序（李四(li) < 王五(wang) < 张三(zhang)）
        name_lst = ["张三", "李四", "王五", "航拍中国第一季", "航拍中国第三季", "航拍中国第二季"]
        self.assertEqual(sorted(name_lst, key=mixed_sort_key), ["李四", "王五", "张三", "航拍中国第一季", "航拍中国第二季", "航拍中国第三季"])

    def test_mixed_alpha_number(self):
        """测试字母+数字混合：字母按ASCII，数字按自然序"""
        lst = ["a10b", "a2b", "a100c", "b1a", "A99"]
        sorted_lst = sorted(lst, key=mixed_sort_key)
        self.assertEqual(sorted_lst, ["A99", "a2b", "a10b", "a100c", "b1a"])

    def test_mixed_chinese_number(self):
        """测试汉字+数字混合：汉字按拼音，数字按自然序"""
        lst = ["中123国", "中45国", "美67利坚", "美5利坚", "日8本"]
        sorted_lst = sorted(lst, key=mixed_sort_key)
        self.assertEqual(
            sorted_lst, ["中45国", "中123国", "日8本", "美5利坚", "美67利坚"]
        )

    def test_with_symbols(self):
        """测试含符号：符号按ASCII码排序"""
        # #(ASCII 35) < @(64)；+(43) < -(45)；!(33) < #(35)
        lst = ["@123", "#456", "a+b", "a-b", "!789"]
        sorted_lst = sorted(lst, key=mixed_sort_key)
        self.assertEqual(sorted_lst, ["!789", "#456", "@123", "a+b", "a-b"])

    def test_empty_string(self):
        """测试空字符串：空字符串优先排序"""
        lst = ["", "123", "abc", "中文", "@"]
        sorted_lst = sorted(lst, key=mixed_sort_key)
        self.assertEqual(sorted_lst, ["", "@", "123", "abc", "中文"])

    def test_complex_mixed(self):
        """测试复杂混合场景（字母+数字+汉字+符号）"""
        lst = [
            "2025年元旦",
            "2024年春节",
            "B58中文",
            "A69英文",
            "test8测试",
            "test10测试",
            "#999",
        ]
        expected = [
            "#999",
            "A69英文",
            "B58中文",
            "2024年春节",
            "2025年元旦",
            "test8测试",
            "test10测试",
        ]
        self.assertEqual(sorted(lst, key=mixed_sort_key), expected)


if __name__ == "__main__":
    # 运行所有测试，verbosity=2 显示详细测试结果
    unittest.main(verbosity=2)
