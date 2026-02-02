import unittest

from utils.sort_util import StringSorter


class TestMixedSortKey(unittest.TestCase):
    """测试混合排序键函数"""

    def test_pure_alphabet(self):
        """测试纯字母：按小写ASCII排序（不区分原大小写）"""
        lst = ["Banana", "apple", "Cherry", "aBc"]
        sorted_lst = StringSorter.mixed_sort(lst)
        self.assertEqual(["aBc", "apple", "Banana", "Cherry"], sorted_lst)

    def test_pure_number(self):
        """测试纯数字：自然排序（而非字符串字典序）"""
        lst = ["10", "2", "100", "1", "0", "99"]
        sorted_lst = StringSorter.mixed_sort(lst)
        self.assertEqual(["0", "1", "2", "10", "99", "100"], sorted_lst)

    def test_pure_chinese(self):
        """测试纯汉字：按拼音小写排序"""
        # 场景1：城市拼音排序（北京(bei) < 广州(guang) < 上海(shang) < 深圳(shen)）
        city_lst = ["上海", "北京", "广州", "深圳"]
        self.assertEqual(['上海', '北京', '广州', '深圳'], StringSorter.mixed_sort(city_lst))

        # 场景2：人名拼音排序（李四(li) < 王五(wang) < 张三(zhang)）
        name_lst = ["张三", "李四", "王五", "航拍中国第一季", "航拍中国第三季", "航拍中国第二季"]
        self.assertEqual(['张三', '李四', '王五', '航拍中国第一季', '航拍中国第二季', '航拍中国第三季'],
                         StringSorter.mixed_sort(name_lst))

        # 场景3：穿靴子的猫<穿靴子的猫2
        movie_lst = ["穿靴子的猫2", "穿靴子的猫"]
        self.assertEqual(["穿靴子的猫", "穿靴子的猫2"], StringSorter.mixed_sort(movie_lst))

    def test_mixed_alpha_number(self):
        """测试字母+数字混合：字母按ASCII，数字按自然序"""
        lst = ["a10b", "a2b", "a100c", "b1a", "A99"]
        sorted_lst = StringSorter.mixed_sort(lst)
        self.assertEqual(["A99", "a2b", "a10b", "a100c", "b1a"], sorted_lst)

    def test_mixed_chinese_number(self):
        """测试汉字+数字混合：汉字按拼音，数字按自然序"""
        lst = ["中123国", "中45国", "美67利坚", "美5利坚", "日8本"]
        sorted_lst = StringSorter.mixed_sort(lst)
        self.assertEqual(['中45国', '中123国', '日8本', '美5利坚', '美67利坚'], sorted_lst)

    def test_with_symbols(self):
        """测试含符号：符号按ASCII码排序"""
        # #(ASCII 35) < @(64)；+(43) < -(45)；!(33) < #(35)
        lst = ["@123", "#456", "a+b", "a-b", "!789"]
        sorted_lst = StringSorter.mixed_sort(lst)
        self.assertEqual(["a+b", "a-b", "!789", "#456", "@123"], sorted_lst)

    def test_empty_string(self):
        """测试空字符串：空字符串优先排序"""
        lst = ["", "123", "abc", "中文", "@"]
        sorted_lst = StringSorter.mixed_sort(lst)
        self.assertEqual(['abc', '中文', '@', '123', ''], sorted_lst)

    def test_complex_mixed(self):
        """测试复杂混合场景（字母+数字+汉字+符号）"""
        lst = [
            "2025年元旦", "2024年春节", "B58中文", "A69英文", "test8测试", "test10测试", "#999", "央视新影-中学生",
            "CCTV-1 综合", "CGTN1"
        ]
        expected = [
            "A69英文", "B58中文", "CCTV-1 综合", "CGTN1", "test8测试", "test10测试",
            "央视新影-中学生", "#999", "2024年春节", "2025年元旦"
        ]
        self.assertEqual(expected, StringSorter.mixed_sort(lst))

    def test_cate_name(self):
        """测试数字和汉字组合：自然排序（而非字符串字典序）"""
        lst = ["010北京", "020广东", "001央广", "000境外"]
        sorted_lst = StringSorter.mixed_sort(lst)
        self.assertEqual(["000境外", "001央广", "010北京", "020广东"], sorted_lst)


if __name__ == "__main__":
    # 运行所有测试，verbosity=2 显示详细测试结果
    unittest.main(verbosity=2)
