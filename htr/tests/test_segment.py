import sys,unittest
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from service.segment import find_lines

def page(rows,size=(800,600)):
    """White page with a black 'text' strip from y0 to y1 for each row."""
    im=Image.new('L',size,255);d=ImageDraw.Draw(im)
    for y0,y1 in rows:
        for x in range(60,720,12):d.rectangle([x,y0,x+7,y1],fill=0)
    return im

class Segment(unittest.TestCase):
    def test_separate_lines_in_reading_order(self):
        boxes=find_lines(page([(100,130),(200,230),(300,330)]))
        self.assertEqual(len(boxes),3)
        for (left,top,right,bottom),(y0,y1) in zip(boxes,[(100,130),(200,230),(300,330)]):
            self.assertLessEqual(top,y0);self.assertGreaterEqual(bottom,y1);self.assertLess(left,60);self.assertGreater(right,720)
    def test_touching_lines_are_split(self):
        boxes=find_lines(page([(100,130),(200,230),(300,360)]))
        self.assertEqual(len(boxes),4)
    def test_blank_page_has_no_lines(self):
        self.assertEqual(find_lines(Image.new('RGB',(400,300),'white')),[])
    def test_single_line_image_is_kept_whole(self):
        im=Image.open(ROOT/'examples/611_01_r1l31.png')
        self.assertEqual(find_lines(im),[(0,0,*im.size)])
    def test_dark_scan_border_ignored(self):
        im=page([(100,130),(200,230)]);ImageDraw.Draw(im).rectangle([0,0,15,599],fill=0)
        self.assertEqual(len(find_lines(im)),2)
if __name__=='__main__':unittest.main()
