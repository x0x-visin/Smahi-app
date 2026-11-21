import argparse, sys, tempfile, os
from pathlib import Path
from PySide6 import QtWidgets, QtCore, QtGui
from vectorfont.pipeline import Pipeline, PipelineConfig

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('Samahi App')
        self.img = None; self.svg = None; self.ttf = None
        w = QtWidgets.QWidget(); self.setCentralWidget(w)
        g = QtWidgets.QGridLayout(w)
        self.openBtn = QtWidgets.QPushButton('Open image...'); self.openBtn.clicked.connect(self.open_img)
        self.runBtn = QtWidgets.QPushButton('Vectorize'); self.runBtn.clicked.connect(self.run)
        self.ttfBtn = QtWidgets.QPushButton('Export TTF'); self.ttfBtn.clicked.connect(self.export_ttf)
        self.svgBtn = QtWidgets.QPushButton('Export SVG'); self.svgBtn.clicked.connect(self.export_svg)
        self.scale = QtWidgets.QDoubleSpinBox(); self.scale.setRange(1,8); self.scale.setValue(2); self.scale.setSuffix('x upscale')
        self.thr = QtWidgets.QSpinBox(); self.thr.setRange(0,255); self.thr.setValue(180); self.thr.setPrefix('threshold ')
        self.tol = QtWidgets.QDoubleSpinBox(); self.tol.setRange(0.1,10); self.tol.setValue(1.0); self.tol.setPrefix('tolerance ')
        self.chars = QtWidgets.QLineEdit('A'); self.chars.setMaxLength(40)
        self.preview = QtWidgets.QLabel('Preview'); self.preview.setAlignment(QtCore.Qt.AlignCenter); self.preview.setMinimumSize(420,420)
        self.status = QtWidgets.QLabel('Ready')
        for i,x in enumerate([self.openBtn,self.scale,self.thr,self.tol]): g.addWidget(x,0,i)
        g.addWidget(QtWidgets.QLabel('Character(s):'),1,0); g.addWidget(self.chars,1,1,1,3)
        for i,x in enumerate([self.runBtn,self.ttfBtn,self.svgBtn]): g.addWidget(x,2,i)
        g.addWidget(self.preview,3,0,1,4); g.addWidget(self.status,4,0,1,4)
    def open_img(self):
        f,_ = QtWidgets.QFileDialog.getOpenFileName(self,'Open image','','Images (*.png *.jpg *.jpeg *.bmp *.webp)')
        if f: self.img=f; self.preview.setPixmap(QtGui.QPixmap(f).scaled(self.preview.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
    def cfg(self): return PipelineConfig(upscale=self.scale.value(), threshold=self.thr.value(), tolerance=self.tol.value(), chars=self.chars.text() or 'A')
    def run(self):
        if not self.img: return
        self.status.setText('Working...'); QtWidgets.QApplication.processEvents()
        tmp = Path(tempfile.mkdtemp())
        self.ttf, self.svg = Pipeline(self.cfg()).run(self.img, tmp/'out')
        self.preview.setPixmap(QtGui.QPixmap(str(self.svg)).scaled(self.preview.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        self.status.setText(f'Done: {self.ttf}')
    def _save(self, src, filt):
        if not src: return
        d,_ = QtWidgets.QFileDialog.getSaveFileName(self,'Save',str(Path.home()),filt)
        if d:
            Path(d).write_bytes(Path(src).read_bytes()); self.status.setText(f'Saved {d}')
    def export_ttf(self): self._save(self.ttf,'Fonts (*.ttf)')
    def export_svg(self): self._save(self.svg,'SVG (*.svg)')

def cli():
    a = argparse.ArgumentParser(); a.add_argument('--cli',action='store_true'); a.add_argument('--in',dest='inp'); a.add_argument('--out',default='out.ttf'); a.add_argument('--scale',type=float,default=2); a.add_argument('--threshold',type=int,default=180); a.add_argument('--tolerance',type=float,default=1.0); a.add_argument('--chars',default='A')
    nsp = a.parse_args(); cfg = PipelineConfig(upscale=nsp.scale, threshold=nsp.threshold, tolerance=nsp.tolerance, chars=nsp.chars)
    ttf,_ = Pipeline(cfg).run(nsp.inp, Path(nsp.out).with_suffix(''))
    import shutil; shutil.copy(ttf, nsp.out); print(nsp.out)

if __name__ == '__main__':
    if '--cli' in sys.argv: cli()
    else:
        app = QtWidgets.QApplication(sys.argv); m=Main(); m.resize(760,720); m.show(); sys.exit(app.exec())
