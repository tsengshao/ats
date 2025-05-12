*grads -a 0.5

'reinit'
'set background 1'
'c'
'open /data2/VVM/taiwanvvm_lc/lc_20220624/gs_ctl_files/topo.ctl'

'set lon 119.9 122.2'
'set lat 21.85 25.5'

'set parea 0.9 5.3 1.31043 9.68957'
'set lwid 75 8'
'set xlopts 1 75 0.2'
'set ylopts 1 75 0.2'
'set grads off'
'set timelab off'
'set mpdraw off'
'set grid off'
'set xlint 1'
'set ylint 1'

'color 0 3500 100 -gxout shaded -kind white->(50,50,50)'
'd height*1000.'
'set lwid 74 5'
'xcbar 4.5 4.7 1.4 5 -fs 5 -ft 74'
'set string 1 bl 75 0'
'set strsiz 0.15'
'draw string 4.5 5.2 [m]'

* draw coastline
'set gxout contour'
'set clevs 0.5'
'set clab off'
'set cthick 10'
'd height>0'

* draw title
'q gxinfo'
line=sublin(result, 3)
x0  = subwrd(line,4)
'q gxinfo'
line=sublin(result, 4)
y0  = subwrd(line,6)
'set string 1 bl 75 0'
'set strsiz 0.25'
'draw string 'x0' 'y0+0.2' TaiwanVVM Topography'

'gxprint taiwanvvm_topo.png x1000 y2000 white -t 1'

