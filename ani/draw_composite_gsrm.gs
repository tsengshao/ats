'reinit'
'set background 1'
'c'

model='icon'
mlarge='ICON'
ncase='19'

* model='nicam'
* mlarge='NICAM'
* ncase='16'

'sdfopen ../data/rainfall_composite/rcomp_'model'.nc'
'sdfopen /data/C.shaoyu/hackathon/nicam/2dbc/orog.nc'
'sdfopen /data/C.shaoyu/hackathon/nicam/2dbc/sftlf.nc'

topocmap='250 3000 250 -gxout shaded -kind white->(100,100,100)'
raincmap='-levs 2 5 10 15 25 -gxout grfill -kind (255,255,255,0)-(0)->(84,104,245)->(11,191,38)->(242,226,5)->(242,5,5)->(204,7,204)'

* figure setting 
'c'
'set parea 2.58333 8.41667 0.8 7.55'
'set xlopts 1 10 0.2'
'set ylopts 1 10 0.2'
'set grads off'
'set timelab off'
'set ylint 1'
'set xlint 1'
'set mpdset hires'
*'set mpt type color <style <thickness>>'
'set lwid 20 2'
'set map 1 1 20'

'set lon 119.7 122.3'
'set lat 21.8 25.5'

'color 'topocmap
'd orog.2(t=1,z=1)'
'xcbar 8.5 8.8 0.8 7.55'

'color 'raincmap
'define drain=rain.1*3600*24'
'd maskout(drain,sftlf.3(t=1,z=1)>0.2)'
'xcbar 7.8 8.1 0.8 7.55'


* topo contour
'set gxout contour'
'set cmin 500'
'set cmax 3000'
'set cint 500'
'set ccolor 1'
'set cthick 5'
'set clab off'
'd orog.2(t=1,z=1)'

'set string 1 bl 10 0'
'set strsiz 0.25'
'draw string 3.6 7.7 'mlarge'('ncase')'

'set string 1 br 10 0'
'set strsiz 0.2'
'draw string 8.8 8.1 topo [m]'
'draw string 8.8 7.7 rain [mm`a `nd`a-1`n]'

'! mkdir -p ./fig/composite/'
'gxprint ./fig/composite/composite_'model'.png x1100 y850'

