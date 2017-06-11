# coding: utf-8
from paradoc import lex_code, pd_simple_eval
from paradoc.num import Char
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

    def test_lex_numbers(self):
        self.assertEqual(list(lex_code('3')), ['3'])
        self.assertEqual(list(lex_code('33X')), ['33', 'X'])
        self.assertEqual(list(lex_code('.3X')), ['.3', 'X'])
        self.assertEqual(list(lex_code('—.3X')), ['—.3', 'X'])
        self.assertEqual(list(lex_code('——3X')), ['——3X']) # comment
        self.assertEqual(list(lex_code('..3X')), ['..3X']) # comment
        self.assertEqual(list(lex_code('3.')), ['3', '.'])
        self.assertEqual(list(lex_code('3.0')), ['3.0'])
        self.assertEqual(list(lex_code('3.4.')), ['3.4', '.'])
        self.assertEqual(list(lex_code('—3')), ['—3'])
        self.assertEqual(list(lex_code('—3e')), ['—3e'])
        self.assertEqual(list(lex_code('—3x')), ['—3x'])
        self.assertEqual(list(lex_code('—3e3')), ['—3e3'])
        self.assertEqual(list(lex_code('—3x3')), ['—3x', '3'])
        self.assertEqual(list(lex_code('—3—4—5')), ['—3', '—4', '—5'])

    def test_numeric_literals(self):
        self.assertEqual(pd_simple_eval('555'), [555])
        self.assertEqual(pd_simple_eval('.5'), [0.5])
        self.assertEqual(pd_simple_eval('0.5'), [0.5])
        self.assertEqual(pd_simple_eval('.3125'), [0.3125])
        self.assertEqual(pd_simple_eval('—5'), [-5])
        self.assertEqual(pd_simple_eval('—.5'), [-0.5])
        self.assertEqual(pd_simple_eval('—0.5'), [-0.5])

    def test_assignment(self):
        self.assertEqual(pd_simple_eval('123.Test;Test Test+'), [246])
        self.assertEqual(pd_simple_eval('123—Test Test Test+'), [246])
        self.assertEqual(pd_simple_eval('129.**+'), [258])
        self.assertEqual(pd_simple_eval('129—***+'), [258])

    def test_arithmetic(self):
        self.assertEqual(pd_simple_eval('2 3+7*'), [35])
        self.assertEqual(pd_simple_eval('2017 95))%(('), [75])
        self.assertEqual(pd_simple_eval('7 3/'), [7/3])
        self.assertEqual(pd_simple_eval('7 3÷'), [7//3])
        self.assertEqual(pd_simple_eval('7.0 2.0/'), [3.5])
        self.assertEqual(pd_simple_eval('0.25 0.25+'), [0.5])
        self.assertEqual(pd_simple_eval('7 3G'), [1])
        self.assertEqual(pd_simple_eval('8 36G'), [4])

    def test_comparison(self):
        self.assertEqual(pd_simple_eval('7 7='), [1])
        self.assertEqual(pd_simple_eval('7 7<'), [0])
        self.assertEqual(pd_simple_eval('7 7>'), [0])
        self.assertEqual(pd_simple_eval('7 7<e'), [1])
        self.assertEqual(pd_simple_eval('7 7>e'), [1])
        self.assertEqual(pd_simple_eval('6 7='),  [0])
        self.assertEqual(pd_simple_eval('6 7<'),  [1])
        self.assertEqual(pd_simple_eval('6 7>'),  [0])
        self.assertEqual(pd_simple_eval('6 7<e'), [1])
        self.assertEqual(pd_simple_eval('6 7>e'), [0])
        self.assertEqual(pd_simple_eval('8 7='),  [0])
        self.assertEqual(pd_simple_eval('8 7<'),  [0])
        self.assertEqual(pd_simple_eval('8 7>'),  [1])
        self.assertEqual(pd_simple_eval('8 7<e'), [0])
        self.assertEqual(pd_simple_eval('8 7>e'), [1])
        self.assertEqual(pd_simple_eval('"abcd" "efgh" <'), [1])
        self.assertEqual(pd_simple_eval('"abcd" "efgh" ='), [0])
        self.assertEqual(pd_simple_eval('"abcd" "efgh" >'), [0])
        self.assertEqual(pd_simple_eval('[0 1 2][0 1] >e'), [1])
        self.assertEqual(pd_simple_eval('[0 0 2][0 1] >e'), [0])

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
        self.assertEqual(pd_simple_eval('[3 7 2 5]1m='), [5])

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
        self.assertEqual(pd_simple_eval('8mL'), [8])
        self.assertEqual(pd_simple_eval('8L'), [8])
        self.assertEqual(pd_simple_eval('0L'), [0])
        self.assertEqual(pd_simple_eval('[7 2 5 9 3 5 8]L'), [7])
        self.assertEqual(pd_simple_eval('[7 2 5 9 3]L'), [5])
        self.assertEqual(pd_simple_eval('[]L'), [0])

    def test_replicate(self):
        self.assertEqual(pd_simple_eval('3 4 Replicate'), [[3,3,3,3]])
        self.assertEqual(pd_simple_eval('4 3 ˆ'), [[4,4,4]])
        self.assertEqual(pd_simple_eval('\'x 3 ˆ'), ["xxx"])
        self.assertEqual(pd_simple_eval('[1 2] 3 ˆ'), [[[1,2],[1,2],[1,2]]])
        self.assertEqual(pd_simple_eval('\'y \'x 3 Sr'), ["xxx"])
        self.assertEqual(pd_simple_eval('\'y \'x 4m Sr'), ["yyyy"])

    def test_zip_trailers(self):
        self.assertEqual(pd_simple_eval('[1 2 3][9 7 5]+z'), [[10,9,8]])
        self.assertEqual(pd_simple_eval('[1 2 3 5 9 11]+ä'), [[3,5,8,14,20]])
        self.assertEqual(pd_simple_eval('[1 2 3 5 9 11]+ë'), [[1,3,5,8,13,16]])

    def test_break(self):
        self.assertEqual(pd_simple_eval('8,{:3>{Q}&:}e'), [0,0,1,1,2,2,3,3,4])

    def test_continue(self):
        self.assertEqual(pd_simple_eval('8,{:3>{K}&:}e'), [0,0,1,1,2,2,3,3,4,5,6,7])

    def test_abs_diff(self):
        self.assertEqual(pd_simple_eval('3 4±'), [1])
        self.assertEqual(pd_simple_eval('4 3±'), [1])
        self.assertEqual(pd_simple_eval('—1 6±'), [7])
        self.assertEqual(pd_simple_eval('—1 —9±'), [8])
        self.assertEqual(pd_simple_eval('7 —9±'), [16])

    def test_mapsum(self):
        self.assertEqual(pd_simple_eval('[3 4 5])š'), [15])
        self.assertEqual(pd_simple_eval('[3 4 5]²š'), [50])

    def test_conversions(self):
        self.assertEqual(pd_simple_eval('253S'), ['253'])
        self.assertEqual(pd_simple_eval('253F'), [253.0])
        self.assertEqual(pd_simple_eval('"253"I'), [253])
        self.assertEqual(pd_simple_eval('"253"F'), [253.0])
        self.assertEqual(pd_simple_eval('\'xI'), [120])
        self.assertEqual(pd_simple_eval('98C'), [Char(98)])

    def test_negate(self):
        self.assertEqual(pd_simple_eval('5M'), [-5])
        self.assertEqual(pd_simple_eval('6MM'), [6])
        self.assertEqual(pd_simple_eval('—7M'), [7])
        self.assertEqual(pd_simple_eval('—8MM'), [-8])

    def test_signum(self):
        self.assertEqual(pd_simple_eval('1U'), [1])
        self.assertEqual(pd_simple_eval('2U'), [1])
        self.assertEqual(pd_simple_eval('1000U'), [1])
        self.assertEqual(pd_simple_eval('—989U'), [-1])
        self.assertEqual(pd_simple_eval('727mU'), [-1])
        self.assertEqual(pd_simple_eval('6986MMU'), [1])
        self.assertEqual(pd_simple_eval('0U'), [0])

    def test_mold(self):
        self.assertEqual(pd_simple_eval('[5 6 7 8][[1 2][3 4]]M'), [[[5,6],[7,8]]])
        self.assertEqual(pd_simple_eval('[[5][6 7][8]][1 2 3 4]M'), [[5,6,7,8]])
        self.assertEqual(pd_simple_eval('[3 1 4 1 5][[0][0 0 0][0]]M'), [[[3],[1,4,1],[5]]])
        self.assertEqual(pd_simple_eval('2[[0][0 0 0][0]]M'), [[[2],[3,4,5],[6]]])

    def test_group(self):
        self.assertEqual(pd_simple_eval('[3 9 9 9 8 8 9]Group'), [[[3],[9,9,9],[8,8],[9]]])
        self.assertEqual(pd_simple_eval('"aaaaargh"G'), [["aaaaa", "r", "g", "h"]])
        self.assertEqual(pd_simple_eval('[3 1 4 1 5 9 2 6]{Odd}G'), [[[3, 1],[4],[1,5,9],[2,6]]])

    def test_uniquify(self):
        self.assertEqual(pd_simple_eval('[1 2 3]U'), [[1,2,3]])
        self.assertEqual(pd_simple_eval('[1 2 3 2 1]U'), [[1,2,3]])
        self.assertEqual(pd_simple_eval('[9 0 0 9 7 0 9 9 0 7]U'), [[9,0,7]])

    def test_number_predicates(self):
        self.assertEqual(pd_simple_eval('1Â'), [1])
        self.assertEqual(pd_simple_eval('0Â'), [0])
        self.assertEqual(pd_simple_eval('1mÂ'), [0])
        self.assertEqual(pd_simple_eval('8Ê'), [1])
        self.assertEqual(pd_simple_eval('—7Ê'), [0])
        self.assertEqual(pd_simple_eval('1Î'), [1])
        self.assertEqual(pd_simple_eval('9Î'), [0])
        self.assertEqual(pd_simple_eval('—7Î'), [0])
        self.assertEqual(pd_simple_eval('—3Ô'), [1])
        self.assertEqual(pd_simple_eval('5Ô'), [1])
        self.assertEqual(pd_simple_eval('—8Ô'), [0])
        self.assertEqual(pd_simple_eval('—3Û'), [1])
        self.assertEqual(pd_simple_eval('5Û'), [0])
        self.assertEqual(pd_simple_eval('0Û'), [0])

    def test_list_predicates(self):
        self.assertEqual(pd_simple_eval('[1 2 3]Â'), [1])
        self.assertEqual(pd_simple_eval('[1 0 3]Â'), [0])
        self.assertEqual(pd_simple_eval('[0 0 0]Â'), [0])
        self.assertEqual(pd_simple_eval('[1 2 3]Ê'), [1])
        self.assertEqual(pd_simple_eval('[0 2 0]Ê'), [1])
        self.assertEqual(pd_simple_eval('[0 0 0]Ê'), [0])
        self.assertEqual(pd_simple_eval('[1 2 3]Î'), [0])
        self.assertEqual(pd_simple_eval('[2 2 2]Î'), [1])
        self.assertEqual(pd_simple_eval('[2 2 0]Î'), [0])
        self.assertEqual(pd_simple_eval('[0 0 0]Î'), [1])
        self.assertEqual(pd_simple_eval('[0 0 0]Ô'), [1])
        self.assertEqual(pd_simple_eval('[0 2 0]Ô'), [0])
        self.assertEqual(pd_simple_eval('[2 2 2]Ô'), [0])
        self.assertEqual(pd_simple_eval('[0 0 0]Û'), [0])
        self.assertEqual(pd_simple_eval('[0 2 0]Û'), [0])
        self.assertEqual(pd_simple_eval('[3 2 0]Û'), [1])
        self.assertEqual(pd_simple_eval('[3 7 1]Û'), [1])

    def test_keep_under(self):
        self.assertEqual(pd_simple_eval('3 4 5 +'),  [3,9])
        self.assertEqual(pd_simple_eval('3 4 5 +k'), [3,4,5,9])
        self.assertEqual(pd_simple_eval('3 4 5 +u'), [7,5])
        self.assertEqual(pd_simple_eval('3 4 5 +q'), [3,9,4,5])

    def test_double(self):
        self.assertEqual(pd_simple_eval('4 5 )d'), [5,6])
        self.assertEqual(pd_simple_eval('2 3 4 5 +d'), [5,9])

    def test_has(self):
        self.assertEqual(pd_simple_eval('4 5 H'), [0])
        self.assertEqual(pd_simple_eval('10 5 H'), [1])
        self.assertEqual(pd_simple_eval('5000 5 H'), [4])
        self.assertEqual(pd_simple_eval('6 4 H'), [0])
        self.assertEqual(pd_simple_eval('28 4 H'), [1])
        self.assertEqual(pd_simple_eval('224 4 H'), [2])
        self.assertEqual(pd_simple_eval('[1 5 1 3] 1 H'), [2])
        self.assertEqual(pd_simple_eval('[1 5 1 3] 2 H'), [0])
        self.assertEqual(pd_simple_eval('[1 5 1 3] 3 H'), [1])
        self.assertEqual(pd_simple_eval('"PARADOC" \'A H'), [2])
        self.assertEqual(pd_simple_eval('"PARADOC" \'a H'), [0])
        self.assertEqual(pd_simple_eval('"PARADOC" 67 H'), [1])

    def test_some_trig(self):
        self.assertEqual(pd_simple_eval('0 Sn'), [0.0])
        self.assertEqual(pd_simple_eval('0 Cs'), [1.0])
        self.assertEqual(pd_simple_eval('0 Tn'), [0.0])
        self.assertEqual(pd_simple_eval('Pi½ Sn'), [1.0])
        self.assertEqual(pd_simple_eval('Pi Cs'), [-1.0])
        self.assertEqual(pd_simple_eval('[[0] Pi] Cs'), [[[1.0], -1.0]])

    def test_base(self):
        self.assertEqual(pd_simple_eval('4 3 B'), [[1,1]])
        self.assertEqual(pd_simple_eval('48762 16 B'), [[11,14,7,10]])
        self.assertEqual(pd_simple_eval('5 D 10 B'), [43210])
        self.assertEqual(pd_simple_eval('"be7a" 16 B'), [48762])
        self.assertEqual(pd_simple_eval('"DeFaCeD" 16 B'), [233811181])

if __name__ == '__main__':
    unittest.main()
