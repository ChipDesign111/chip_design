import os, sys, glob
import win32com.client as win32
here = os.path.dirname(os.path.abspath(__file__))
pptx = glob.glob(os.path.join(here, "*_v2.pptx"))[0]
out = os.path.join(here, "_preview")
os.makedirs(out, exist_ok=True)
app = win32.Dispatch("PowerPoint.Application")
pres = app.Presentations.Open(pptx, WithWindow=False)
for i, s in enumerate(pres.Slides, 1):
    s.Export(os.path.join(out, "s%02d.png" % i), "PNG", 1600, 900)
pres.Close()
app.Quit()
print("exported", len(glob.glob(os.path.join(out, "*.png"))))
