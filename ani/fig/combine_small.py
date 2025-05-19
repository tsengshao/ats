from moviepy.editor import VideoFileClip, ImageSequenceClip, concatenate_videoclips, clips_array
from moviepy.video.fx.all import crop
import sys, os
sys.path.insert(1,'../')
import glob

def get_ImageSeq(fname, fps=2):
    flist=glob.glob(fname)
    flist.sort()
    return ImageSequenceClip(flist, fps=fps)

iexp=0
#iexp = int(sys.argv[1])

#dum0 = get_ImageSeq(f'./fig_olr_rain/{exp}/bla_olrrain_*.png')
dum0 = get_ImageSeq('./taiwanvvm/tpe20120819nor/*.png')
dum1 = get_ImageSeq(f'./nicam/13Jul2020/*.png')
dum2 = get_ImageSeq(f'./icon/11Jun2020/*.png')

vid = [dum0, dum1, dum2]

(w, h) = vid[0].size
x1, x2 = int(w*0.125), int(w*0.875)
y1, y2 = 0, h
w = x2-x1
h = y2-y1
new_w = w if w % 2 == 0 else w - 1
new_h = h if h % 2 == 0 else h - 1
for i in range(len(vid)):
  vid[i] = crop(vid[i], x1=x1, y1=y1, x2=x1+w, y2=y1+w)

# Concat them
#final = concatenate_videoclips(vid)
final_clip = clips_array([vid])

# Write output to the file
final_clip.write_videofile(f"all_example.mp4", codec='libx264', \
                      threads=10, ffmpeg_params=['-pix_fmt','yuv420p'])

