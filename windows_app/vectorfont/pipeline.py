from dataclasses import dataclass
from pathlib import Path
import math, re, tempfile
import numpy as np
from PIL import Image, ImageOps, ImageFilter
import cv2
from svgpathtools import parse_path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
import xml.etree.ElementTree as ET

try:
    import vtracer
except Exception:
    vtracer = None

UPM = 2048

@dataclass
class PipelineConfig:
    upscale: float = 2.0
    threshold: int = 180
    tolerance: float = 1.0     # curve flattening tolerance (px, post-upscale)
    chars: str = 'A'           # glyph(s) mapped to Private Use Area sequentially
    filter_speckle: int = 4

class Pipeline:
    def __init__(self, cfg: PipelineConfig): self.cfg = cfg

    def run(self, image_path, out_base: Path):
        out_base = Path(out_base); out_base.parent.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix='vf_'))
        up = work/'up.png'; binp = work/'bin.png'; svg = out_base.with_suffix('.svg'); ttf = out_base.with_suffix('.ttf')
        self.upscale(image_path, up)
        self.binarize(up, binp)
        self.trace(binp, svg)
        self.svg_to_font(svg, ttf)
        return ttf, svg

    def upscale(self, src, dst):
        img = Image.open(src).convert('RGBA')
        bg = Image.new('RGBA', img.size, (255,255,255,255)); bg.alpha_composite(img); img = bg.convert('RGB')
        w,h = img.size; nw,nh = max(1,int(w*self.cfg.upscale)), max(1,int(h*self.cfg.upscale))
        # Fast default: Lanczos. Swap in Real-ESRGAN here if you add torch/realesrgan deps.
        img = img.resize((nw,nh), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=2))
        img.save(dst)

    def binarize(self, src, dst):
        im = np.array(Image.open(src).convert('L'))
        im = cv2.GaussianBlur(im,(3,3),0)
        # adaptive fallback for noisy scans
        th = cv2.threshold(im, self.cfg.threshold, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1] if self.cfg.threshold==0 else cv2.threshold(im, self.cfg.threshold, 255, cv2.THRESH_BINARY_INV)[1]
        th = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((2,2),np.uint8))
        cv2.imwrite(dst, th)

    def trace(self, src, dst):
        if vtracer is not None:
            vtracer.convert_image_to_svg_py(str(src), str(dst), colormode='binary', mode='spline',
                filter_speckle=self.cfg.filter_speckle, color_precision=6, layer_difference=16,
                corner_threshold=60, length_threshold=4.0, splice_threshold=45, path_precision=3)
            return
        im = cv2.imread(str(src), 0)
        cs,_ = cv2.findContours(im, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        h,w = im.shape
        def path(c):
            pts = cv2.approxPolyDP(c, self.cfg.tolerance, True).reshape(-1,2)
            d = 'M' + ' L'.join(f'{x} {y}' for x,y in pts) + ' Z'
            return d
        body = ''.join(f'<path d="{path(c)}" fill="#000"/>' for c in cs if cv2.contourArea(c) > self.cfg.filter_speckle)
        Path(dst).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>', encoding='utf-8')

    def svg_size(self, svg):
        r = ET.parse(svg).getroot()
        w = r.get('width'); h = r.get('height')
        def num(x):
            m = re.match(r'([0-9.]+)', x or ''); return float(m.group(1)) if m else None
        w,h = num(w), num(h)
        if not (w and h):
            vb = r.get('viewBox'); w,h = (float(vb.split()[2]), float(vb.split()[3])) if vb else (1000.0,1000.0)
        return w,h

    def flatten(self, path):
        pts=[]
        for seg in path:
            n = max(2, int(seg.length()/self.cfg.tolerance)+1)
            for i in range(n): pts.append(seg.point(i/(n-1)))
        if pts and abs(pts[0]-pts[-1])>1e-6: pts.append(pts[0])
        return pts

    def svg_to_font(self, svg, ttf):
        w,h = self.svg_size(svg)
        scale = UPM / max(w,h,1.0)
        root = ET.parse(svg).getroot(); ns={'s':'http://www.w3.org/2000/svg'}
        paths = [el.get('d') for el in root.findall('.//s:path', ns) if el.get('d')]
        fb = FontBuilder(UPM, isTTF=True)
        glyphs={'.notdef': None}; order=['.notdef']
        cmap={}
        base = 0xE000
        for i,d in enumerate(paths):
            name = f'glyph{i:04d}'; order.append(name)
            pen = TTGlyphPen(None)
            try:
                for sp in parse_path(d):
                    pts = self.flatten(sp)
                    if len(pts)<3: continue
                    pen.moveTo((pts[0].real*scale, (h-pts[0].imag)*scale))
                    for p in pts[1:-1]: pen.lineTo((p.real*scale,(h-p.imag)*scale))
                    pen.closePath()
            except Exception:
                continue
            glyphs[name]=pen.glyph()
            if i < len(self.cfg.chars): cmap[ord(self.cfg.chars[i])] = name
        if not cmap: cmap[ord('A')] = order[1] if len(order)>1 else '.notdef'
        fb.setupGlyphOrder(order); fb.setupCharacterMap(cmap)
        fb.setupGlyf(glyphs); fb.setupHorizontalMetrics({n:(int(w*scale),0) for n in order})
        fb.setupHorizontalHeader(ascent=UPM, descent=0); fb.setupOS2(); fb.setupPost(); fb.setupNameTable({'familyName':'Samahi App','styleName':'Regular','uniqueFontIdentifier':'SamahiApp-1','fullName':'Samahi App Regular','psName':'SamahiApp-Regular'}); fb.setupMaxp()
        fb.save(str(ttf))
