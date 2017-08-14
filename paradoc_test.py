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

    def test_readme(self):
        self.assertEqual(pd_simple_eval('E²m'), [[0,1,4,9,16,25,36,49,64,81,100]])
        self.assertEqual(pd_simple_eval('E2pm'), [[0,1,4,9,16,25,36,49,64,81,100]])
        self.assertEqual(pd_simple_eval('11 Square_map'), [[0,1,4,9,16,25,36,49,64,81,100]])

        self.assertEqual(pd_simple_eval('0 1T+kx'), [0,1,1,2,3,5,8,13,21,34,55,89])
        self.assertEqual(pd_simple_eval('0 1 10 +_keep_xloop'), [0,1,1,2,3,5,8,13,21,34,55,89])

    def test_numeric_literals(self):
        self.assertEqual(pd_simple_eval('555 .5 0.5 .3125 —5 —.5 —0.5'), [555, 0.5, 0.5, 0.3125, -5, -0.5, -0.5])

    def test_assignment(self):
        self.assertEqual(pd_simple_eval('123.Tst;Tst Tst+ 123—Test Test Test+ 129.**+ 129—///+', use_cache=False), [246,246,258,258])

    def test_arithmetic(self):
        self.assertEqual(pd_simple_eval('2 3+7*  2017 95))%(('), [35,75])
        self.assertEqual(pd_simple_eval('7 3/ 7 3÷ 7.0 2.0/ 0.25 0.25+'), [7/3, 7//3, 3.5, 0.5])
        self.assertEqual(pd_simple_eval('7 3G 8 36G'), [1,4])
        self.assertEqual(pd_simple_eval('16´'), [1/16])

    def test_arithmetic_trailers(self):
        self.assertEqual(pd_simple_eval('2 3á 2 3à'), [5, -1])
        self.assertEqual(pd_simple_eval('8é 42è'), [256,1764])
        self.assertEqual(pd_simple_eval('3í'), [1/3])
        self.assertEqual(pd_simple_eval('3 7ó 3 7ò'), [21,3/7])
        self.assertEqual(pd_simple_eval('2017 13ú'), [2])

    def test_comparison(self):
        self.assertEqual(pd_simple_eval('7 7=q <q >q <eq >e'), [1,0,0,1,1])
        self.assertEqual(pd_simple_eval('6 7=q <q >q <eq >e'), [0,1,0,1,0])
        self.assertEqual(pd_simple_eval('8 7=q <q >q <eq >e'), [0,0,1,0,1])
        self.assertEqual(pd_simple_eval('"abcd" "efgh" <q =q >'), [1,0,0])
        self.assertEqual(pd_simple_eval('[0 1 2][0 1] >e [0 0 2][0 1] >e'), [1,0])

    def test_comparison_approx(self):
        self.assertEqual(pd_simple_eval('9 9<a'), [1])
        self.assertEqual(pd_simple_eval('9 9>a'), [1])
        self.assertEqual(pd_simple_eval('8 3>a'), [1])
        self.assertEqual(pd_simple_eval('8 3<a'), [0])
        self.assertEqual(pd_simple_eval('8 8.0000000001>a'), [1])
        self.assertEqual(pd_simple_eval('8 8.01>a'), [0])
        self.assertEqual(pd_simple_eval('8 8.0000000001=a'), [1])
        self.assertEqual(pd_simple_eval('8 8.01=a'), [0])

    def test_rounding(self):
        self.assertEqual(pd_simple_eval('[1.2 3.5 8.9 3.5m]{Iq <iq >iq =i}e'), [1,1,2,1,3,3,4,4,8,8,9,9,-3,-4,-3,-4])

    def test_multiplication(self):
        self.assertEqual(pd_simple_eval('"foo"3* 3"bar"*'), ["foofoofoo","barbarbar"])
        self.assertEqual(pd_simple_eval('[1 2]3* 3[3 4]*'), [[1,2,1,2,1,2],[3,4,3,4,3,4]])
        self.assertEqual(pd_simple_eval('0{10*)}4*'), [1111])

    def test_constant_fractions(self):
        self.assertEqual(pd_simple_eval('3½7¾9¼11×'), [1.5,5.25,2.25,22])
        self.assertEqual(pd_simple_eval('["""foobar""zfoobar"]½e'), ["","foo","zfo"])
        self.assertEqual(pd_simple_eval('"foobar"×'), ["foobarfoobar"])

    def test_bits(self):
        self.assertEqual(pd_simple_eval('2 4&3 5&2 4|3 5|'), [0,1,6,7])
        self.assertEqual(pd_simple_eval('12347 74321&q|q^'), [8209,78459,70250])

    def test_unary_operators(self):
        self.assertEqual(pd_simple_eval('7('), [6])
        self.assertEqual(pd_simple_eval('7)'), [8])
        self.assertEqual(pd_simple_eval('7½'), [3.5])
        self.assertEqual(pd_simple_eval('7²'), [49])
        self.assertEqual(pd_simple_eval('7³'), [343])

    def test_if(self):
        self.assertEqual(pd_simple_eval('0 2 3? 1 2 3? 2 2 3?'), [3,2,2])
        self.assertEqual(pd_simple_eval('[0 1]{100X{2*}{5+}?}x'), [105,200])

    def test_single_branch_if(self):
        self.assertEqual(pd_simple_eval('0{6}&1{7}&0{8}|1{9}|'), [7,8])
        self.assertEqual(pd_simple_eval('1 2[]{+}&1 2[3 4]{+}&1 2[]{-}|1 2[3 4]{-}|'), [1,2,3,-1,1,2])

    def test_single_branch_word_if(self):
        self.assertEqual(pd_simple_eval('0{6}If 1{7}If 0{8}Unless 1{9}Unless'), [7,8])
        self.assertEqual(pd_simple_eval('0 6 If 1 7 If 0 8 Unless 1 9 Unless'), [7,8])

    def test_indexing(self):
        self.assertEqual(pd_simple_eval('[3 7 2 5]0=q;1=q;3=q;1m='), [3,7,5,5])

    def test_slices(self):
        self.assertEqual(pd_simple_eval('[3 7 2 5]1<q>'), [[3],[7,2,5]])

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
        self.assertEqual(pd_simple_eval('5²m'), [[0,1,4,9,16]])

    def test_strings(self):
        self.assertEqual(pd_simple_eval('"foo"'), ["foo"])
        self.assertEqual(pd_simple_eval(r'"\"what\""'), ['"what"'])

    def test_string_ops(self):
        self.assertEqual(pd_simple_eval('"foo" "bar"+'), ["foobar"])

    def test_min_max(self):
        self.assertEqual(pd_simple_eval('2 3<m4 5>m9 8<m7 6>m'), [2,5,8,7])

    def test_min_max_of_list(self):
        self.assertEqual(pd_simple_eval('[7 2 5 9 3 5 8]>rq<r'), [9,2])

    def test_len(self):
        self.assertEqual(pd_simple_eval('[8m 8 0]Lm'), [[8,8,0]])
        self.assertEqual(pd_simple_eval('[[7 2 5 9 3 5 8][7 2 5 9 3][]]Lm'), [[7,5,0]])

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
        self.assertEqual(pd_simple_eval('[[3 4][4 3][—1 6][—1 —9][7 —9]]{~±}e'), [1,1,7,8,16])

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
        self.assertEqual(pd_simple_eval('5M 6MM —7M —8MM'), [-5,6,7,-8])

    def test_signum(self):
        self.assertEqual(pd_simple_eval('[1 2 1000 —989 727m 6986MM 0]Um'), [[1,1,1,-1,-1,1,0]])

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
        self.assertEqual(pd_simple_eval('1Â0Â1mÂ8Ê—7Ê1Î9Î—7Î—3Ô5Ô—8Ô—3Û5Û0Û'),
                [1,0,0,1,0,1,0,0,1,1,0,1,0,0])

    def test_list_predicates(self):
        self.assertEqual(pd_simple_eval('''
                [1 2 3]Â[1 0 3]Â[0 0 0]Â[1 2 3]Ê[0 2 0]Ê[0 0 0]Ê
                [1 2 3]Î[2 2 2]Î[2 2 0]Î[0 0 0]Î[0 0 0]Ô[0 2 0]Ô[2 2 2]Ô
                [0 0 0]Û[0 2 0]Û[3 2 0]Û[3 7 1]Û'''),
                [1,0,0,1,1,0,0,1,0,1,1,0,0,0,0,1,1])

    def test_mapped_list_predicates(self):
        self.assertEqual(pd_simple_eval('[3 2 0]{1+}Â'), [1])
        self.assertEqual(pd_simple_eval('[3 2 1]{1-}Â'), [0])
        self.assertEqual(pd_simple_eval('[3 2 1]{0*}Ê'), [0])
        self.assertEqual(pd_simple_eval('[0 0 3]{1*}Ê'), [1])
        self.assertEqual(pd_simple_eval('[3 2 1]{0*}Î'), [1])
        self.assertEqual(pd_simple_eval('[3 3 1]{2*}Î'), [0])
        self.assertEqual(pd_simple_eval('[3 2 1]{0*}Ô'), [1])
        self.assertEqual(pd_simple_eval('[1 1 3]{1-}Ô'), [0])
        self.assertEqual(pd_simple_eval('[3 2 3m]{:*}Û'), [0])
        self.assertEqual(pd_simple_eval('[3 2 4m]{:*}Û'), [1])

    def test_keep_under(self):
        self.assertEqual(pd_simple_eval('3 4 5 +'),  [3,9])
        self.assertEqual(pd_simple_eval('3 4 5 +k'), [3,4,5,9])
        self.assertEqual(pd_simple_eval('3 4 5 +u'), [7,5])
        self.assertEqual(pd_simple_eval('3 4 5 +q'), [3,9,4,5])

    def test_double(self):
        self.assertEqual(pd_simple_eval('4 5 )d'), [5,6])
        self.assertEqual(pd_simple_eval('2 3 4 5 +d'), [5,9])

    def test_has(self):
        self.assertEqual(pd_simple_eval('[4 10 5000]5Hv'), [[0,1,4]])
        self.assertEqual(pd_simple_eval('[6 28 224]4Hv'), [[0,1,2]])
        self.assertEqual(pd_simple_eval('[1 2 3][1 5 1 3]Hav'), [[2,0,1]])
        self.assertEqual(pd_simple_eval('[\'A \'a 67]"PARADOC"Hav'), [[2,0,1]])

    def test_ranges(self):
        self.assertEqual(pd_simple_eval('3,[0 1 2]='), [1])
        self.assertEqual(pd_simple_eval('3,[0 1 3]='), [0])
        self.assertEqual(pd_simple_eval('3 5To[3 4 5]='), [1])
        self.assertEqual(pd_simple_eval('5 9Tl[5 6 7 8]='), [1])
        self.assertEqual(pd_simple_eval('2 6¨[2 3 4 5]='), [1])
        self.assertEqual(pd_simple_eval('1 5…[1 2 3 4 5]='), [1])

    def test_flatten(self):
        self.assertEqual(pd_simple_eval('["foo""bar""baz"]¨q…'), ["foobarbaz","foobarbaz"])
        self.assertEqual(pd_simple_eval("['P'a'r'a'd'o'c]¨q…"), ["Paradoc","Paradoc"])
        self.assertEqual(pd_simple_eval('[[2 4]6[0 1]]¨q…'), [[2,4,6,0,1],[2,4,6,0,1]])
        self.assertEqual(pd_simple_eval('[[[2 4]]6[[0 2]]]¨q…'), [[[2,4],6,[0,2]],[2,4,6,0,2]])

    def test_some_trig(self):
        self.assertEqual(pd_simple_eval('0 Snq Csq Tn'), [0.0,1.0,0.0])
        self.assertEqual(pd_simple_eval('Pi½ Sn Pi Cs'), [1.0,-1.0])
        self.assertEqual(pd_simple_eval('[[0] Pi] Cs'), [[[1.0], -1.0]])

    def test_base(self):
        self.assertEqual(pd_simple_eval('4 3 B'), [[1,1]])
        self.assertEqual(pd_simple_eval('48762 16 B'), [[11,14,7,10]])
        self.assertEqual(pd_simple_eval('5 D 10 B'), [43210])
        self.assertEqual(pd_simple_eval('"be7a" 16 B'), [48762])
        self.assertEqual(pd_simple_eval('"DeFaCeD" 16 B'), [233811181])

    def test_base_string(self):
        self.assertEqual(pd_simple_eval('48762 16 LbqUb'), ['be7a','BE7A'])
        self.assertEqual(pd_simple_eval('233811181 16 LbqUb'), ['defaced', 'DEFACED'])

    def test_string_transformations(self):
        self.assertEqual(pd_simple_eval('"hElLo :) 123 xD"Uc'), ["HELLO :) 123 XD"])
        self.assertEqual(pd_simple_eval('"hElLo :) 123 xD"Lc'), ["hello :) 123 xd"])
        self.assertEqual(pd_simple_eval('"hElLo :) 123 xD"Xc'), ["HeLlO :) 123 Xd"])

    def test_string_predicates(self):
        self.assertEqual(pd_simple_eval('"B3 t@"ApqUpqLpqWp'), [[1,0,0,1,0],[1,0,0,0,0],[0,0,0,1,0],[0,0,1,0,0]])

    def test_split(self):
        self.assertEqual(pd_simple_eval('"assdfs""s"/'), [["a","","df",""]])
        self.assertEqual(pd_simple_eval('[1 2 3 4 2 3 5 2 3 2 3 3 3 3 3][2 3]/'), [[[1],[4],[5],[],[3,3,3,3]]])
        self.assertEqual(pd_simple_eval('[2 3 2 3][2 3]/'), [[[],[],[]]])
        self.assertEqual(pd_simple_eval('"assdfs""s"%'), [["a","df"]])
        self.assertEqual(pd_simple_eval('[2 3 2 3][2 3]%'), [[]])
        self.assertEqual(pd_simple_eval('"pair of doc"W'), [["pair","of","doc"]])

    def test_random(self):
        self.assertEqual(pd_simple_eval('0 Random_seed RfRfRf'),
                [0.8444218515250481, 0.7579544029403025, 0.420571580830845])
        self.assertEqual(pd_simple_eval('0 Random_seed RgRgRg'),
                [0.9417154046806644, -1.39657810470115, -0.6797144480784211])
        self.assertEqual(pd_simple_eval('0 Random_seed {5Ri}5*'), [3,3,0,2,4])
        self.assertEqual(pd_simple_eval('0 Random_seed {[2 5 3]Rc}5*'), [5,5,2,5,3])

    def test_arithmetic_literals(self):
        self.assertEqual(pd_simple_eval('[1 27m 7]Uám'), [[31,3,37]])
        self.assertEqual(pd_simple_eval('[15 13]Bàm'), [[4,2]])
        self.assertEqual(pd_simple_eval('AéBèGíHì'), [1024,121,1/16,-17])
        self.assertEqual(pd_simple_eval('[1 3 5]Uóm'), [[30,90,150]])
        self.assertEqual(pd_simple_eval('200Aò200Hú'), [20.0, 13])
        self.assertEqual(pd_simple_eval('Aý'), [10000000000])

    def test_discrete_math(self):
        self.assertEqual(pd_simple_eval('5 2 Bc'), [10])
        self.assertEqual(pd_simple_eval('5 !p'), [120])
        self.assertEqual(pd_simple_eval('12 Pp'), [0])
        self.assertEqual(pd_simple_eval('13 Pp'), [1])
        self.assertEqual(pd_simple_eval('26 (p'), [23])
        self.assertEqual(pd_simple_eval('26 )p'), [29])
        self.assertEqual(pd_simple_eval('60 Fc'), [[[2,2],[3,1],[5,1]]])
        self.assertEqual(pd_simple_eval('60 Ff'), [[2,2,3,5]])
        self.assertEqual(pd_simple_eval('11 Fb'), [89])
        self.assertEqual(pd_simple_eval('12 Et'), [4])
        self.assertEqual(pd_simple_eval('2 21 Js'), [-1])

    def test_stack_functions(self):
        self.assertEqual(pd_simple_eval('6 6 6 Ls'), [3])
        self.assertEqual(pd_simple_eval('6 6 6 Šs'), [18])
        self.assertEqual(pd_simple_eval('6 6 6 Þs'), [216])
        self.assertEqual(pd_simple_eval('2 4 6 0 1 Ds'), [1,0,6,4,2])

    def test_transpose(self):
        self.assertEqual(pd_simple_eval('[[1 2][3 4]]Transpose'), [[[1,3],[2,4]]])

if __name__ == '__main__':
    unittest.main()
