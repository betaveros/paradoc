# coding: utf-8
from paradoc import lex_code, pd_simple_eval
import unittest

class TestParadoc(unittest.TestCase):

    def test_lex_code(self):
        self.assertEqual(list(lex_code('3 4+')), ['3',' ','4','+'])
        self.assertEqual(list(lex_code('1 34+')), ['1',' ','34','+'])
        self.assertEqual(list(lex_code('1 3.4+')), ['1',' ','3.4','+'])
        self.assertEqual(list(lex_code(r'''""''"\n"'""\"""\\"''')),
                ['""',"''",r'"\n"',"'\"",r'"\""',r'"\\"'])
        self.assertEqual(list(lex_code('[2 3 5]{7+}_map(m)m+f')),
                ['[','2',' ','3',' ','5',']','{','7','+','}_map','(m',')m','+f'])

    def test_arithmetic(self):
        self.assertEqual(pd_simple_eval('2 3+7*'), [35])
        self.assertEqual(pd_simple_eval('2017 95))%(('), [75])
        self.assertEqual(pd_simple_eval('7 3/'), [7/3])
        self.assertEqual(pd_simple_eval('7 3÷'), [7//3])
        self.assertEqual(pd_simple_eval('7.0 2.0/'), [3.5])
        self.assertEqual(pd_simple_eval('0.25 0.25+'), [0.5])

    def test_multiplication(self):
        self.assertEqual(pd_simple_eval('"foo"3*'), ["foofoofoo"])
        self.assertEqual(pd_simple_eval('3"foo"*'), ["foofoofoo"])
        self.assertEqual(pd_simple_eval('[1 2]3*'), [[1,2,1,2,1,2]])
        self.assertEqual(pd_simple_eval('3[1 2]*'), [[1,2,1,2,1,2]])
        self.assertEqual(pd_simple_eval('0{10*)}4*'), [1111])

    def test_constant_fractions(self):
        self.assertEqual(pd_simple_eval('3½'), [1.5])
        self.assertEqual(pd_simple_eval('7¾'), [5.25])
        self.assertEqual(pd_simple_eval('9¼'), [2.25])
        self.assertEqual(pd_simple_eval('11×'), [22])
        self.assertEqual(pd_simple_eval('""½'), [""])
        self.assertEqual(pd_simple_eval('"foobar"½'), ["foo"])
        self.assertEqual(pd_simple_eval('"zfoobar"½'), ["zfo"])
        self.assertEqual(pd_simple_eval('"foobar"×'), ["foobarfoobar"])

    def test_bits(self):
        self.assertEqual(pd_simple_eval('2 4&'), [0])
        self.assertEqual(pd_simple_eval('3 5&'), [1])
        self.assertEqual(pd_simple_eval('2 4|'), [6])
        self.assertEqual(pd_simple_eval('3 5|'), [7])
        self.assertEqual(pd_simple_eval('12347 74321&'), [8209])
        self.assertEqual(pd_simple_eval('12347 74321|'), [78459])
        self.assertEqual(pd_simple_eval('12347 74321^'), [70250])

    def test_unary_operators(self):
        self.assertEqual(pd_simple_eval('7('), [6])
        self.assertEqual(pd_simple_eval('7)'), [8])
        self.assertEqual(pd_simple_eval('7½'), [3.5])
        self.assertEqual(pd_simple_eval('7Sq'), [49])
        self.assertEqual(pd_simple_eval('7Cb'), [343])

    def test_if(self):
        self.assertEqual(pd_simple_eval('0 2 3?'), [3])
        self.assertEqual(pd_simple_eval('1 2 3?'), [2])
        self.assertEqual(pd_simple_eval('2 2 3?'), [2])
        self.assertEqual(pd_simple_eval('100 0{2*}{5+}?'), [105])
        self.assertEqual(pd_simple_eval('100 1{2*}{5+}?'), [200])

    def test_single_branch_if(self):
        self.assertEqual(pd_simple_eval('0{8}&'), [])
        self.assertEqual(pd_simple_eval('1{8}&'), [8])
        self.assertEqual(pd_simple_eval('0{8}|'), [8])
        self.assertEqual(pd_simple_eval('1{8}|'), [])
        self.assertEqual(pd_simple_eval('1 2[]{+}&'), [1,2])
        self.assertEqual(pd_simple_eval('1 2[3 4]{+}&'), [3])
        self.assertEqual(pd_simple_eval('1 2[]{-}|'), [-1])
        self.assertEqual(pd_simple_eval('1 2[3 4]{-}|'), [1,2])

    def test_indexing(self):
        self.assertEqual(pd_simple_eval('[3 7 2 5]0='), [3])
        self.assertEqual(pd_simple_eval('[3 7 2 5]1='), [7])
        self.assertEqual(pd_simple_eval('[3 7 2 5]3='), [5])
        self.assertEqual(pd_simple_eval('[3 7 2 5]1n='), [5])

    def test_slices(self):
        self.assertEqual(pd_simple_eval('[3 7 2 5]1<'), [[3]])
        self.assertEqual(pd_simple_eval('[3 7 2 5]1>'), [[7,2,5]])

    def test_each(self):
        self.assertEqual(pd_simple_eval('[2 3 5]{7+}/'), [9,10,12])

    def test_map(self):
        self.assertEqual(pd_simple_eval('[2 3 5]{7+}%'), [[9,10,12]])
        self.assertEqual(pd_simple_eval('[2 3 5]{7+}m'), [[9,10,12]])
        self.assertEqual(pd_simple_eval('[2 3 5]{7+}_map'), [[9,10,12]])
        self.assertEqual(pd_simple_eval('[2 3 5](_map'), [[1,2,4]])
        self.assertEqual(pd_simple_eval('[2 3 5])m'), [[3,4,6]])
        self.assertEqual(pd_simple_eval('[2 3 5]{:}%'), [[2,2,3,3,5,5]])
        self.assertEqual(pd_simple_eval('[2 3 5]{:}m'), [[2,2,3,3,5,5]])
        self.assertEqual(pd_simple_eval('[2 3 5]:m'), [[2,2,3,3,5,5]])
        self.assertEqual(pd_simple_eval('[2 3 5]{:}_map'), [[2,2,3,3,5,5]])

    def test_filter(self):
        self.assertEqual(pd_simple_eval('[1 3 7 5 0 9 2]{5<}+'), [[1,3,0,2]])
        self.assertEqual(pd_simple_eval('[1 3 7 5 0 9 2]{5<},'), [[0,1,4,6]])
        self.assertEqual(pd_simple_eval('10,{3%0=}+'), [[0,3,6,9]])
        self.assertEqual(pd_simple_eval('10J{3%0=}+'), [[3,6,9]])
        self.assertEqual(pd_simple_eval('10J{3%0=},'), [[2,5,8]])
        self.assertEqual(pd_simple_eval('10,{3%}+'), [[1,2,4,5,7,8]])
        self.assertEqual(pd_simple_eval('10,{5<}+'), [[0,1,2,3,4]])
        self.assertEqual(pd_simple_eval('10,3%_bind_filter'), [[1,2,4,5,7,8]])
        self.assertEqual(pd_simple_eval('10,3%bf'), [[1,2,4,5,7,8]])

    def test_builtin_reduce(self):
        self.assertEqual(pd_simple_eval('[5 7 8]{+}R'), [20])
        self.assertEqual(pd_simple_eval('10,{+}R'), [45])
        self.assertEqual(pd_simple_eval('[5 7 8]2R'), [[5,2,7,2,8]])
        self.assertEqual(pd_simple_eval('[5 7 8][0 0]R'), [[5,0,0,7,0,0,8]])
        self.assertEqual(pd_simple_eval('[5 7 8]"+"R'), ["5+7+8"])
        self.assertEqual(pd_simple_eval('[9 2 7]\'.R'), ["9.2.7"])
        self.assertEqual(pd_simple_eval('["123" 456 "789"]"//"R'), ["123//456//789"])

    def test_reduce(self):
        self.assertEqual(pd_simple_eval('[5 7 8]+_reduce'), [20])
        self.assertEqual(pd_simple_eval('10,+r'), [45])
        self.assertEqual(pd_simple_eval('10,*r'), [0])
        self.assertEqual(pd_simple_eval('10J*r'), [3628800])

    def test_square_map(self):
        self.assertEqual(pd_simple_eval('5Sqm'), [[0,1,4,9,16]])

    def test_strings(self):
        self.assertEqual(pd_simple_eval('"foo"'), ["foo"])
        self.assertEqual(pd_simple_eval(r'"\"what\""'), ['"what"'])

    def test_string_ops(self):
        self.assertEqual(pd_simple_eval('"foo" "bar"+'), ["foobar"])

    def test_min_max(self):
        self.assertEqual(pd_simple_eval('2 3<m'), [2])
        self.assertEqual(pd_simple_eval('2 3>m'), [3])
        self.assertEqual(pd_simple_eval('5 4<m'), [4])
        self.assertEqual(pd_simple_eval('5 4>m'), [5])

    def test_min_max_of_list(self):
        self.assertEqual(pd_simple_eval('[7 2 5 9 3 5 8]>l'), [9])
        self.assertEqual(pd_simple_eval('[7 2 5 9 3 5 8]<l'), [2])

    def test_len(self):
        self.assertEqual(pd_simple_eval('8nL'), [8])
        self.assertEqual(pd_simple_eval('8L'), [8])
        self.assertEqual(pd_simple_eval('0L'), [0])
        self.assertEqual(pd_simple_eval('[7 2 5 9 3 5 8]L'), [7])
        self.assertEqual(pd_simple_eval('[7 2 5 9 3]L'), [5])
        self.assertEqual(pd_simple_eval('[]L'), [0])


if __name__ == '__main__':
    unittest.main()
