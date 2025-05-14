'reinit'
'set background 1'
'c'

file='/data/C.shaoyu/ats/vvm/taiwanvvm_list.txt'

topocmap='250 3000 250 -gxout shaded -kind white->(100,100,100)'
raincmap='-levs 1 2 3 4 5 7 10 15 20 25 -gxout grfill -kind (255,255,255,0)->grainbow'
raincmap='-levs 2 5 10 15 25 -gxout grfill -kind (255,255,255,0)-(0)->(84,104,245)->(11,191,38)->(242,226,5)->(242,5,5)->(204,7,204)'

date='18JUN2020'
while (1)
  res = read(file)
  line1 = sublin(res,1)
  line2 = sublin(res,2)
  rc1 = subwrd(line1,1)
  if (rc1); break; endif
  case = subwrd(line2,1)
  say case

  'open /data/C.shaoyu/ats/vvm/'case'/gs_ctl_files/surface.ctl'
  'open /data/C.shaoyu/ats/vvm/'case'/gs_ctl_files/topo.ctl'

*  'set lon 119 123'
*  'set lat 21.5 26'
  'set lon 119.7 122.3'
  'set lat 21.8 25.5'

* figure setting 
  'c'
  'set parea 2.58333 8.41667 0.8 7.55'
  'set xlopts 1 10 0.2'
  'set ylopts 1 10 0.2'
  'set grads off'
  'set timelab off'
  'set ylint 1'
  'set xlint 1'
*  'set mpdset hires'
  'set mpdraw off'
  
  'color 'topocmap
  'd height.2(t=1,z=1)*1000.'
  'xcbar 9.2 9.5 0.8 7.55'
  'set gxout contour'
  'set clab off'
  'set clevs 0'
  'set ccolor 1'
  'set cthick 5'
  'd height.2(t=1,z=1)'

  'color 'raincmap
  'd ave(sprec.1,t=2,t=145)*3600*24'
  'xcbar 8.5 8.8 0.8 7.55'

  'set string 1 bl 10 0'
  'set strsiz 0.25'
  'draw string 3 7.7 TaiwanVVM'case' daily [mm`a `nd`a-1`n]'
  '! mkdir -p ./fig/taiwanvvm/daily/'
  'gxprint ./fig/taiwanvvm/daily/ats_'case'.png x1100 y850'
  
  it=1
  while(it<=24)
  'c'
  t0=(it-1)*6+2
  t1=it*6+1
  say 't0='t0', t1='t1
  'set t 't0
  'q time'
  say result
  'set xlopts 1 10 0.2'
  'set ylopts 1 10 0.2'
  'set grads off'
  'set timelab off'
  'set ylint 1'
  'set xlint 1'
*  'set mpdset hires'
  'set mpdraw off'
  
*  'color 0 3000 500 -gxout shaded -kind white->(150,150,150)'
  'color 'topocmap
  'd height.2(t=1,z=1)*1000.'
  'xcbar 9.2 9.5 0.8 7.55'
  'set gxout contour'
  'set clab off'
  'set clevs 0'
  'set ccolor 1'
  'set cthick 5'
  'd height.2(t=1,z=1)'
  
*  'color -levs 1 3 5 7 10 15 20 -gxout grfill -kind (255,255,255,0)->grainbow'
  'color 'raincmap
  'd ave(sprec.1,t='t0',t='t1')*3600'
  'xcbar 8.5 8.8 0.8 7.55'
  
  tstr=math_format('%02.0f', it)
  'set string 1 bl 10 0'
  'set strsiz 0.25'
  'draw string 3 7.7 TaiwanVVM 'case' 'tstr'LT [mm`a `nhr`a-1`n]'
  
  '! mkdir -p ./fig/taiwanvvm/'case
  'gxprint ./fig/taiwanvvm/'case'/ats_'tstr'.png x1100 y850'
  
  it=it+1
  endwhile
  'close 2'
  'close 1'
*read file
endwhile




